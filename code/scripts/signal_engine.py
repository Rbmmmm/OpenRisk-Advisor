#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import sqlite3
import subprocess
import sys
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Signal engine for OpenRisk-Advisor")
    parser.add_argument("--sources", required=True, help="Path to sources.yaml")
    parser.add_argument("--metrics", required=True, help="Path to metrics.yaml")
    parser.add_argument("--signals", required=True, help="Path to signals.yaml")
    parser.add_argument("--db", default=None, help="Override sqlite db path")
    parser.add_argument(
        "--no-export-reports",
        action="store_true",
        help="Do not generate docs/signal_report.* and docs/repo_summary.md after evaluation",
    )
    return parser.parse_args()


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def get_sqlite_path(sources_path: Path, override: str | None) -> Path:
    if override:
        return Path(override)
    sources = load_yaml(sources_path)
    defaults = sources.get("defaults") or {}
    return Path(defaults.get("sqlite_path", "data/sqlite/opendigger.db"))


def connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_signal_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS signal_events (
            id INTEGER PRIMARY KEY,
            repo_id INTEGER NOT NULL,
            signal_id TEXT NOT NULL,
            metric_id INTEGER NOT NULL,
            start_month TEXT NOT NULL,
            end_month TEXT NOT NULL,
            confidence REAL NOT NULL,
            severity REAL NOT NULL,
            evidence_ref TEXT NOT NULL,
            FOREIGN KEY (repo_id) REFERENCES repos(id),
            FOREIGN KEY (metric_id) REFERENCES metrics(id)
        )
        """
    )
    conn.commit()


@dataclass
class SignalDef:
    signal_id: str
    name: str
    dimension: str
    severity: str
    weight: float
    enabled: bool
    window: str
    allow_partial_window: bool
    requires: dict
    conditions: dict
    consistency: dict
    confidence: dict
    min_coverage: dict
    explain: dict
    require_quarter_alignment: bool
    require_year_alignment: bool


@dataclass
class SignalContext:
    windows: Dict[str, int]
    severity_scores: Dict[str, float]
    default_weight: float
    metric_ids: Dict[str, int]
    metrics_cfg: dict


def parse_signals(config: dict) -> List[SignalDef]:
    signals = []
    for item in config.get("signals", []):
        signals.append(
            SignalDef(
                signal_id=item["id"],
                name=item.get("name", item["id"]),
                dimension=item.get("dimension", "unknown"),
                severity=item.get("severity", "info"),
                weight=float(item.get("weight", 1.0)),
                enabled=bool(item.get("enabled", True)),
                window=item.get("window", "win3"),
                allow_partial_window=bool(item.get("allow_partial_window", False)),
                requires=item.get("requires", {}),
                conditions=item.get("conditions", {}),
                consistency=item.get("consistency", {"type": "k_of_n", "k": 2, "n": 3}),
                confidence=item.get("confidence", {}),
                min_coverage=item.get("min_coverage", {}),
                explain=item.get("explain", {}),
                require_quarter_alignment=bool(item.get("require_quarter_alignment", False)),
                require_year_alignment=bool(item.get("require_year_alignment", False)),
            )
        )
    return signals


def metric_id_map(conn: sqlite3.Connection) -> Dict[str, int]:
    return {row["name"]: row["id"] for row in conn.execute("SELECT id, name FROM metrics")}


def repo_map(conn: sqlite3.Connection) -> Dict[int, str]:
    return {row["id"]: row["full_name"] for row in conn.execute("SELECT id, full_name FROM repos")}


def feature_values(
    conn: sqlite3.Connection, repo_id: int, metric_id: int, feature: str
) -> Dict[str, float]:
    query = """
        SELECT period, value
        FROM derived_features
        WHERE repo_id = ? AND metric_id = ? AND period_type = 'month' AND feature = ?
    """
    return {
        row["period"]: row["value"]
        for row in conn.execute(query, (repo_id, metric_id, feature))
    }


def parse_feature_name(feature: str, metric_names: List[str]) -> Tuple[Optional[str], str]:
    if "." in feature:
        metric, suffix = feature.split(".", 1)
        # Support object-metric access patterns used in signals.yaml:
        # - issue_response_time.p95        -> metric=issue_response_time, feature=p95_value
        # - issue_response_time.avg        -> metric=issue_response_time, feature=avg_value
        # - issue_response_time.p95_yoy    -> metric=issue_response_time, feature=p95_yoy
        if suffix in ("avg", "p95"):
            return metric, f"{suffix}_value"
        return metric, suffix
    for name in sorted(metric_names, key=len, reverse=True):
        if feature == name:
            return name, "value"
        if feature.startswith(f"{name}_"):
            return name, feature[len(name) + 1 :]
    return None, feature


def normalize_metric_name(raw_name: str) -> str:
    if "." in raw_name:
        return raw_name.split(".", 1)[0]
    return raw_name


def metric_ref_to_feature(metric_ref: str) -> Tuple[str, str]:
    if "." in metric_ref:
        base, sub = metric_ref.split(".", 1)
        return base, f"{sub}_value"
    return metric_ref, "value"


def extract_feature_clauses(conditions: dict) -> List[dict]:
    clauses: List[dict] = []

    def walk(item: object) -> None:
        if isinstance(item, list):
            for entry in item:
                walk(entry)
            return
        if isinstance(item, dict):
            if "feature" in item:
                clauses.append(item)
                return
            if "all" in item:
                walk(item["all"])
            if "any" in item:
                walk(item["any"])
            return

    walk(conditions)
    return clauses


def eval_condition_block(block: object, period: str, metric_names: List[str], get_feature) -> bool:
    if isinstance(block, list):
        return all(eval_condition_block(b, period, metric_names, get_feature) for b in block)
    if isinstance(block, dict):
        if "all" in block:
            return all(eval_condition_block(b, period, metric_names, get_feature) for b in block["all"])
        if "any" in block:
            return any(eval_condition_block(b, period, metric_names, get_feature) for b in block["any"])
        if "feature" in block:
            metric_name, feature = parse_feature_name(block["feature"], metric_names)
            if not metric_name:
                return False
            left = get_feature(metric_name, feature, period)
            if left is None:
                return False
            if "feature_ref" in block:
                ref_metric, ref_feature = parse_feature_name(block["feature_ref"], metric_names)
                if not ref_metric:
                    return False
                right = get_feature(ref_metric, ref_feature, period)
                if right is None:
                    return False
                return op_compare(left, block["op"], right)
            return op_compare(left, block["op"], float(block.get("value", 0)))
    return False


def op_compare(left: float, op: str, right: float) -> bool:
    if op == "<":
        return left < right
    if op == "<=":
        return left <= right
    if op == ">":
        return left > right
    if op == ">=":
        return left >= right
    if op == "==":
        return left == right
    return False


def window_months(windows: Dict[str, int], name: str) -> int:
    return int(windows.get(name, 3))


def build_k_of_n_flags(flags: List[bool], k: int, n: int) -> List[bool]:
    if not flags:
        return []
    result = []
    for idx in range(len(flags)):
        start = max(0, idx - n + 1)
        count = sum(1 for v in flags[start : idx + 1] if v)
        result.append(count >= k)
    return result


def build_event_end_indices(flags: List[bool], k: int, n: int) -> List[int]:
    if not flags:
        return []
    valid_flags = build_k_of_n_flags(flags, k, n)
    return [idx for idx, ok in enumerate(valid_flags) if ok]


def mean(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def confidence_tier(raw_ratio: float, interp_ratio: float, tiers: dict) -> str:
    for name, cfg in tiers.items():
        min_raw = float(cfg.get("min_raw_ratio", 0.0))
        max_interp = float(cfg.get("max_interp_ratio", 1.0))
        if raw_ratio >= min_raw and interp_ratio <= max_interp:
            return name
    return "low"


def month_to_quarter(month: str) -> Optional[str]:
    if len(month) != 7 or "-" not in month:
        return None
    year, m = month.split("-", 1)
    if not year.isdigit() or not m.isdigit():
        return None
    month_int = int(m)
    if month_int < 1 or month_int > 12:
        return None
    quarter = (month_int - 1) // 3 + 1
    return f"{year}Q{quarter}"


def load_quarter_trend(conn: sqlite3.Connection) -> Dict[Tuple[int, str], float]:
    query = """
        SELECT metric_id, period, value
        FROM derived_features
        WHERE period_type = 'quarter' AND feature = 'trend_dir'
    """
    return {(row["metric_id"], row["period"]): row["value"] for row in conn.execute(query)}


def quarter_alignment_ok(trend_value: Optional[float], op: str) -> bool:
    if trend_value is None:
        return False
    if op in ("<", "<="):
        return trend_value < 0
    if op in (">", ">="):
        return trend_value > 0
    return False


def month_to_year(month: str) -> Optional[str]:
    if len(month) != 7 or "-" not in month:
        return None
    year, m = month.split("-", 1)
    if not year.isdigit() or not m.isdigit():
        return None
    return year


def month_sequence(start: str, end: str) -> List[str]:
    if len(start) != 7 or len(end) != 7:
        return []
    sy, sm = start.split("-", 1)
    ey, em = end.split("-", 1)
    if not (sy.isdigit() and sm.isdigit() and ey.isdigit() and em.isdigit()):
        return []
    y, m = int(sy), int(sm)
    end_y, end_m = int(ey), int(em)
    seq = []
    while (y, m) <= (end_y, end_m):
        seq.append(f"{y:04d}-{m:02d}")
        m += 1
        if m > 12:
            m = 1
            y += 1
    return seq


def load_year_trend(conn: sqlite3.Connection) -> Dict[Tuple[int, str], float]:
    query = """
        SELECT metric_id, period, value
        FROM derived_features
        WHERE period_type = 'year' AND feature = 'trend_dir'
    """
    return {(row["metric_id"], row["period"]): row["value"] for row in conn.execute(query)}


def year_alignment_ok(trend_value: Optional[float], op: str) -> bool:
    if trend_value is None:
        return False
    if op in ("<", "<="):
        return trend_value < 0
    if op in (">", ">="):
        return trend_value > 0
    return False


def main() -> None:
    args = parse_args()
    sources_path = Path(args.sources)
    signals_path = Path(args.signals)
    metrics_path = Path(args.metrics)

    db_path = get_sqlite_path(sources_path, args.db)
    conn = connect(db_path)

    try:
        t0 = time.monotonic()
        print(f"[signal_engine] db={db_path}")
        ensure_signal_table(conn)
        signals_cfg = load_yaml(signals_path)
        metrics_cfg = load_yaml(metrics_path)
        signals = parse_signals(signals_cfg)
        enabled_signals = [s for s in signals if s.enabled]
        print(f"[signal_engine] loaded signals={len(signals)} enabled={len(enabled_signals)}")

        windows_cfg = signals_cfg.get("windows", {})
        windows = {name: int(cfg.get("months", 3)) for name, cfg in windows_cfg.items()}
        scoring_cfg = signals_cfg.get("scoring", {})
        severity_scores = {
            k: float(v.get("score", 0)) for k, v in scoring_cfg.get("severity_levels", {}).items()
        }
        default_weight = float(scoring_cfg.get("default_weight", 1.0))

        metric_ids = metric_id_map(conn)
        repo_names = repo_map(conn)
        quarter_trend = load_quarter_trend(conn)
        year_trend = load_year_trend(conn)
        confidence_cfg = signals_cfg.get("schema", {}).get("confidence_policy", {})
        confidence_tiers = confidence_cfg.get("confidence_tiers", {})
        efficiency_cfg = metrics_cfg.get("efficiency", {})
        efficiency_primary = efficiency_cfg.get("primary_metric")
        efficiency_fallback = efficiency_cfg.get("fallback_metric")
        context = SignalContext(
            windows=windows,
            severity_scores=severity_scores,
            default_weight=default_weight,
            metric_ids=metric_ids,
            metrics_cfg=metrics_cfg,
        )

        conn.execute("DELETE FROM signal_events")
        conn.commit()

        # Preload required features
        metric_names = list(metric_ids.keys())
        needed_features: Dict[Tuple[str, str], None] = {}
        for signal in signals:
            for clause in extract_feature_clauses(signal.conditions):
                metric_name, feature = parse_feature_name(clause["feature"], metric_names)
                if metric_name:
                    needed_features[(metric_name, feature)] = None
                    # Always keep base value series for coverage checks and evidence.
                    needed_features[(metric_name, "value")] = None
                if "feature_ref" in clause:
                    metric_name, feature = parse_feature_name(clause["feature_ref"], metric_names)
                    if metric_name:
                        needed_features[(metric_name, feature)] = None
                        needed_features[(metric_name, "value")] = None
            conf = signal.confidence or {}
            for key in ("raw_ratio_feature", "interp_ratio_feature"):
                if key in conf:
                    metric_name, feature = parse_feature_name(conf[key], metric_names)
                    if metric_name:
                        needed_features[(metric_name, feature)] = None

        feature_cache: Dict[Tuple[int, int, str], Dict[str, float]] = {}
        for repo_id in repo_names.keys():
            for (metric_name, feature) in needed_features.keys():
                metric_id = metric_ids.get(metric_name)
                if metric_id is None:
                    continue
                feature_cache[(repo_id, metric_id, feature)] = feature_values(
                    conn, repo_id, metric_id, feature
                )

        # Helper to get feature value
        def get_feature(repo_id: int, metric_name: str, feature: str, period: str) -> Optional[float]:
            metric_id = metric_ids.get(metric_name)
            if metric_id is None:
                return None
            return feature_cache.get((repo_id, metric_id, feature), {}).get(period)

        def has_feature(repo_id: int, metric_name: str, feature: str) -> bool:
            metric_id = metric_ids.get(metric_name)
            if metric_id is None:
                return False
            return bool(feature_cache.get((repo_id, metric_id, feature)))

        triggered_months: Dict[Tuple[int, str], List[str]] = defaultdict(list)

        for signal in signals:
            if not signal.enabled:
                continue
            if "composite" in signal.conditions:
                continue

            window_len = window_months(context.windows, signal.window)
            k = int(signal.consistency.get("k", 2))
            n = int(signal.consistency.get("n", window_len))

            for repo_id, repo_name in repo_names.items():
                requires = signal.requires or {}
                # Keep original refs: signals.yaml may use object-metric refs like
                # issue_response_time.avg / issue_response_time.p95, which map to
                # derived feature names avg_value / p95_value.
                any_metrics = list(requires.get("any_of_metrics", []) or [])
                all_metrics = list(requires.get("all_of_metrics", []) or [])
                if any_metrics:
                    if not any(
                        has_feature(repo_id, *parse_feature_name(m, metric_names)) for m in any_metrics
                    ):
                        continue
                if all_metrics:
                    if not all(
                        has_feature(repo_id, *parse_feature_name(m, metric_names)) for m in all_metrics
                    ):
                        continue
                required_signals_any = requires.get("triggered_signals_any", [])
                required_signals_all = requires.get("triggered_signals_all", [])
                if required_signals_any:
                    if not any(triggered_months.get((repo_id, sid)) for sid in required_signals_any):
                        continue
                if required_signals_all:
                    if not all(triggered_months.get((repo_id, sid)) for sid in required_signals_all):
                        continue
                required_features = requires.get("derived_features", [])
                if required_features:
                    if not all(
                        has_feature(repo_id, *parse_feature_name(f, metric_names))
                        for f in required_features
                    ):
                        continue

                # Determine the primary feature periods from conditions (flattened)
                condition_features = []
                for clause in extract_feature_clauses(signal.conditions):
                    metric_name, feature = parse_feature_name(clause["feature"], metric_names)
                    if metric_name:
                        condition_features.append((metric_name, feature))
                if not condition_features:
                    continue

                base_metric_name, base_feature = condition_features[0]
                fallback_used = False
                if efficiency_primary and efficiency_fallback:
                    if base_metric_name == efficiency_primary and not has_feature(
                        repo_id, efficiency_primary, base_feature
                    ):
                        base_metric_name = efficiency_fallback
                        fallback_used = True
                base_series = feature_cache.get(
                    (repo_id, metric_ids.get(base_metric_name, -1), base_feature), {}
                )
                periods = sorted(base_series.keys())
                if not periods:
                    continue

                align_op = None
                if signal.require_quarter_alignment:
                    if signal.conditions.get("all"):
                        align_op = signal.conditions["all"][0].get("op")
                    elif signal.conditions.get("any"):
                        align_op = signal.conditions["any"][0].get("op")
                align_year_op = None
                if signal.require_year_alignment:
                    if signal.conditions.get("all"):
                        align_year_op = signal.conditions["all"][0].get("op")
                    elif signal.conditions.get("any"):
                        align_year_op = signal.conditions["any"][0].get("op")

                flags = []
                for period in periods:
                    # Coverage check
                    cov_series = float(signal.min_coverage.get("series", 0.0) or 0.0)
                    cov_derived = float(signal.min_coverage.get("derived", 0.0) or 0.0)
                    if cov_series or cov_derived:
                        start_idx = max(0, periods.index(period) - window_len + 1)
                        window_periods = periods[start_idx : periods.index(period) + 1]
                        series_ok = True
                        derived_ok = True
                        if cov_series > 0:
                            count = 0
                            for p in window_periods:
                                val = get_feature(repo_id, base_metric_name, "value", p)
                                if val is not None:
                                    count += 1
                            series_ok = (count / len(window_periods)) >= cov_series
                        if cov_derived > 0:
                            count = 0
                            for p in window_periods:
                                for metric_name, feature in condition_features:
                                    if get_feature(repo_id, metric_name, feature, p) is not None:
                                        count += 1
                                        break
                            derived_ok = (count / len(window_periods)) >= cov_derived
                        if not (series_ok and derived_ok):
                            flags.append(False)
                            continue

                    # Evaluate conditions (supports nested all/any)
                    ok = eval_condition_block(
                        signal.conditions,
                        period,
                        metric_names,
                        lambda m, f, per: get_feature(repo_id, m, f, per),
                    )
                    if ok and signal.require_quarter_alignment and align_op:
                        metric_id = metric_ids.get(base_metric_name, -1)
                        quarter = month_to_quarter(period)
                        trend_val = quarter_trend.get((metric_id, quarter)) if quarter else None
                        ok = quarter_alignment_ok(trend_val, align_op)
                    if ok and signal.require_year_alignment and align_year_op:
                        metric_id = metric_ids.get(base_metric_name, -1)
                        year = month_to_year(period)
                        trend_val = year_trend.get((metric_id, year)) if year else None
                        ok = year_alignment_ok(trend_val, align_year_op)
                    flags.append(ok)

                end_indices = build_event_end_indices(flags, k, n)
                if not end_indices:
                    continue

                metric_name = base_metric_name
                metric_id = metric_ids.get(metric_name, -1)
                if metric_id == -1:
                    continue

                for end_idx in end_indices:
                    start_idx = max(0, end_idx - n + 1)
                    months = periods[start_idx : end_idx + 1]
                    if signal.allow_partial_window:
                        if len(months) < max(1, k):
                            continue
                    else:
                        if len(months) < n:
                            continue

                    feature_values_map = {}
                    for metric_name, feature in condition_features:
                        key = metric_name if feature == "value" else f"{metric_name}_{feature}"
                        feature_values_map[key] = [
                            get_feature(repo_id, metric_name, feature, m) for m in months
                        ]

                    conf = signal.confidence or {}
                    raw_ratio = None
                    interp_ratio = None
                    if "raw_ratio_feature" in conf:
                        mname, fname = parse_feature_name(conf["raw_ratio_feature"], metric_names)
                        if mname:
                            raw_vals = [get_feature(repo_id, mname, fname, m) for m in months]
                            raw_vals = [v for v in raw_vals if v is not None]
                            raw_ratio = mean(raw_vals) if raw_vals else 0.0
                            feature_values_map[conf["raw_ratio_feature"]] = [
                                get_feature(repo_id, mname, fname, m) for m in months
                            ]
                    if "interp_ratio_feature" in conf:
                        mname, fname = parse_feature_name(conf["interp_ratio_feature"], metric_names)
                        if mname:
                            int_vals = [get_feature(repo_id, mname, fname, m) for m in months]
                            int_vals = [v for v in int_vals if v is not None]
                            interp_ratio = mean(int_vals) if int_vals else 0.0
                            feature_values_map[conf["interp_ratio_feature"]] = [
                                get_feature(repo_id, mname, fname, m) for m in months
                            ]
                    if raw_ratio is None and interp_ratio is None:
                        raw_ratio = 0.0
                        interp_ratio = 1.0

                    tier = confidence_tier(raw_ratio or 0.0, interp_ratio or 1.0, confidence_tiers)

                    severity_score = context.severity_scores.get(signal.severity, 0.0)
                    weight = signal.weight or context.default_weight
                    severity_score = min(100.0, severity_score * weight)

                    evidence = {
                        "signal_id": signal.signal_id,
                        "signal_name": signal.name,
                        "signal_severity": signal.severity,
                        "signal_weight": weight,
                        "signal_window": signal.window,
                        "signal_consistency": signal.consistency,
                        "signal_confidence": signal.confidence,
                        "signal_evidence_fields": signal.explain.get("evidence_fields"),
                        "repo": repo_name,
                        "metric": metric_name,
                        "dimension": signal.dimension,
                        "months": months,
                        "features": feature_values_map,
                        "raw_ratio": raw_ratio,
                        "interp_ratio": interp_ratio,
                        "confidence_tier": tier,
                        "summary_template": signal.explain.get("summary_template"),
                        "fallback_used": fallback_used,
                    }

                    conn.execute(
                        """
                        INSERT INTO signal_events
                            (repo_id, signal_id, metric_id, start_month, end_month, confidence, severity, evidence_ref)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            repo_id,
                            signal.signal_id,
                            metric_id,
                            months[0],
                            months[-1],
                            float(raw_ratio or 0),
                            float(severity_score),
                            json.dumps(evidence, ensure_ascii=True),
                        ),
                    )
                    triggered_months[(repo_id, signal.signal_id)].extend(months)

        # Composite signals
        for signal in signals:
            if not signal.enabled:
                continue
            composite = signal.conditions.get("composite")
            if not composite:
                continue

            window_len = window_months(context.windows, signal.window)
            k = int(signal.consistency.get("k", 1))
            n = int(signal.consistency.get("n", window_len))
            if signal.consistency.get("type") == "once_in_window":
                k, n = 1, 1

            for repo_id, repo_name in repo_names.items():
                requires = signal.requires or {}
                required_signals_any = requires.get("triggered_signals_any", [])
                required_signals_all = requires.get("triggered_signals_all", [])
                if required_signals_any:
                    if not any(triggered_months.get((repo_id, sid)) for sid in required_signals_any):
                        continue
                if required_signals_all:
                    if not all(triggered_months.get((repo_id, sid)) for sid in required_signals_all):
                        continue

                ref_signals = composite.get("signals", [])
                if not ref_signals:
                    continue

                months_set = set()
                for sid in ref_signals:
                    months_set.update(triggered_months.get((repo_id, sid), []))
                raw_periods = sorted(months_set)
                periods = month_sequence(raw_periods[0], raw_periods[-1]) if raw_periods else []
                if not periods:
                    continue

                flags = []
                for period in periods:
                    active = 0
                    for sid in ref_signals:
                        if period in triggered_months.get((repo_id, sid), []):
                            active += 1
                    ok = False
                    if composite.get("type") == "m_of_n_signals":
                        ok = active >= int(composite.get("m", 1))
                    elif composite.get("type") == "all_signals":
                        ok = active == len(ref_signals)
                    flags.append(ok)

                end_indices = build_event_end_indices(flags, k, n)
                if not end_indices:
                    continue

                severity_score = context.severity_scores.get(signal.severity, 0.0)
                weight = signal.weight or context.default_weight
                metric_id = next(iter(metric_ids.values())) if metric_ids else 0

                for end_idx in end_indices:
                    start_idx = max(0, end_idx - n + 1)
                    months = periods[start_idx : end_idx + 1]
                    if len(months) < n:
                        continue
                    triggered = {sid: [m for m in months if m in triggered_months.get((repo_id, sid), [])] for sid in ref_signals}
                    severity_score_adj = min(100.0, severity_score * weight)
                    evidence = {
                        "signal_id": signal.signal_id,
                        "signal_name": signal.name,
                        "signal_severity": signal.severity,
                        "signal_weight": weight,
                        "signal_window": signal.window,
                        "signal_consistency": signal.consistency,
                        "repo": repo_name,
                        "dimension": signal.dimension,
                        "months": months,
                        "triggered_signals": triggered,
                        "summary_template": signal.explain.get("summary_template"),
                    }

                    conn.execute(
                        """
                        INSERT INTO signal_events
                            (repo_id, signal_id, metric_id, start_month, end_month, confidence, severity, evidence_ref)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            repo_id,
                            signal.signal_id,
                            metric_id,
                            months[0],
                            months[-1],
                            0.5,
                            float(severity_score_adj),
                            json.dumps(evidence, ensure_ascii=True),
                        ),
                    )

        conn.commit()
        cur = conn.execute("SELECT COUNT(*) AS c FROM signal_events")
        events_count = int(cur.fetchone()["c"])
        elapsed = time.monotonic() - t0
        print(f"[signal_engine] wrote signal_events={events_count} elapsed={elapsed:.2f}s")
    finally:
        conn.close()

    if args.no_export_reports:
        print("[signal_engine] reports: skipped (--no-export-reports)")
        return

    # Generate human-readable outputs so a single command refreshes docs.
    # (These scripts read from the same SQLite DB and write under docs/.)
    cmd_base = [sys.executable]
    db_override = ["--db", str(db_path)] if args.db else []
    export_cmd = cmd_base + [
        "scripts/export_signal_evidence.py",
        "--sources",
        str(sources_path),
        *db_override,
    ]
    summary_cmd = cmd_base + [
        "scripts/repo_risk_summary.py",
        "--sources",
        str(sources_path),
        *db_override,
    ]
    print("[signal_engine] exporting reports...")
    subprocess.run(export_cmd, check=True)
    subprocess.run(summary_cmd, check=True)
    print("[signal_engine] reports updated: docs/signal_report.md, docs/signal_report.json, docs/repo_summary.md")


if __name__ == "__main__":
    main()
