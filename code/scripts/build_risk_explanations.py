#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build RiskReport evidence chains from signal_events + predictions")
    p.add_argument("--sources", required=True, help="Path to sources.yaml")
    p.add_argument("--model", default="configs/model.yaml", help="Path to model.yaml")
    p.add_argument("--signals", default="configs/signals.yaml", help="Path to signals.yaml")
    p.add_argument("--db", default=None, help="Override sqlite db path")
    p.add_argument("--model-type", default="baseline", choices=["baseline", "transformer"])
    p.add_argument("--model-version", default=None, help="Model version (default: latest for model-type)")
    p.add_argument("--as-of-month", default=None, help="YYYY-MM (default: latest in risk_predictions)")
    p.add_argument("--lookback-months", type=int, default=6, help="Look back window for signal evidence")
    p.add_argument("--top-n-signals", type=int, default=5, help="Top signals per repo")
    p.add_argument("--replace", action="store_true", help="Delete existing risk_reports for this snapshot")
    return p.parse_args()


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


def month_to_int(month: str) -> int:
    y, m = month.split("-", 1)
    return int(y) * 12 + int(m)


def int_to_month(value: int) -> str:
    year = value // 12
    m = value % 12
    if m == 0:
        year -= 1
        m = 12
    return f"{year:04d}-{m:02d}"


def lookback_start(latest_month: str, lookback_months: int) -> str:
    if lookback_months <= 1:
        return latest_month
    return int_to_month(month_to_int(latest_month) - (lookback_months - 1))


def configured_repo_ids(conn: sqlite3.Connection, sources_path: Path) -> Dict[int, str]:
    sources = load_yaml(sources_path)
    enabled_names = {
        f"{r.get('org')}/{r.get('repo')}"
        for r in (sources.get("repos") or [])
        if isinstance(r, dict) and r.get("enabled", True)
    }
    rows = conn.execute("SELECT id, full_name FROM repos").fetchall()
    return {int(r["id"]): str(r["full_name"]) for r in rows if str(r["full_name"]) in enabled_names}


def metric_id_map(conn: sqlite3.Connection) -> Dict[str, int]:
    return {str(r["name"]): int(r["id"]) for r in conn.execute("SELECT id, name FROM metrics")}


def latest_model_version(conn: sqlite3.Connection, model_type: str) -> Optional[str]:
    row = conn.execute(
        "SELECT model_version FROM ml_models WHERE model_type=? ORDER BY created_at DESC LIMIT 1",
        (model_type,),
    ).fetchone()
    return str(row["model_version"]) if row and row["model_version"] else None


def latest_as_of_month(conn: sqlite3.Connection, model_type: str, model_version: str) -> Optional[str]:
    row = conn.execute(
        """
        SELECT MAX(as_of_month) AS m
        FROM risk_predictions
        WHERE model_type=? AND model_version=?
        """,
        (model_type, model_version),
    ).fetchone()
    return str(row["m"]) if row and row["m"] else None


def ensure_risk_report_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS risk_reports (
            id INTEGER PRIMARY KEY,
            repo_id INTEGER NOT NULL,
            as_of_month TEXT NOT NULL,
            model_type TEXT NOT NULL,
            model_version TEXT NOT NULL,
            report_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(repo_id, as_of_month, model_type, model_version)
        )
        """
    )
    conn.commit()


def parse_signal_defs(signals_cfg: dict) -> Dict[str, dict]:
    out: Dict[str, dict] = {}
    for s in signals_cfg.get("signals", []) or []:
        if not isinstance(s, dict):
            continue
        sid = s.get("id")
        if isinstance(sid, str) and sid:
            out[sid] = s
    return out


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def compute_forecast_uncertainty_ratio(forecast: dict) -> float:
    eps = 1e-6
    ratios: List[float] = []
    metrics = (forecast.get("metrics") or {}) if isinstance(forecast, dict) else {}
    for _, v in metrics.items():
        if not isinstance(v, dict):
            continue
        q10 = v.get("q10") or []
        q50 = v.get("q50") or []
        q90 = v.get("q90") or []
        for a, b, c in zip(q10, q50, q90):
            denom = abs(float(b)) + eps
            ratios.append((float(c) - float(a)) / denom)
    return sum(ratios) / len(ratios) if ratios else 0.0


def percentile_rank(values: List[float], x: float) -> Optional[float]:
    if not values:
        return None
    sorted_vals = sorted(values)
    # inclusive rank
    le = sum(1 for v in sorted_vals if v <= x)
    return le / len(sorted_vals)


def merge_contiguous_ranges(ranges: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
    if not ranges:
        return []
    items = sorted(ranges, key=lambda r: (month_to_int(r[0]), month_to_int(r[1])))
    merged: List[Tuple[str, str]] = []
    cur_s, cur_e = items[0]
    for s, e in items[1:]:
        if month_to_int(s) <= month_to_int(cur_e) + 1:
            if month_to_int(e) > month_to_int(cur_e):
                cur_e = e
        else:
            merged.append((cur_s, cur_e))
            cur_s, cur_e = s, e
    merged.append((cur_s, cur_e))
    return merged


def fetch_series_window(
    conn: sqlite3.Connection,
    repo_id: int,
    metric_id: int,
    start_month: str,
    end_month: str,
) -> List[Tuple[str, float]]:
    rows = conn.execute(
        """
        SELECT period, value
        FROM time_series
        WHERE repo_id=? AND metric_id=? AND period_type='month' AND is_raw=0
          AND period >= ? AND period <= ?
        ORDER BY period
        """,
        (repo_id, metric_id, start_month, end_month),
    ).fetchall()
    return [(str(r["period"]), float(r["value"])) for r in rows if r["value"] is not None]


def fetch_feature_window(
    conn: sqlite3.Connection,
    repo_id: int,
    metric_id: int,
    feature: str,
    start_month: str,
    end_month: str,
) -> List[Tuple[str, float]]:
    rows = conn.execute(
        """
        SELECT period, value
        FROM derived_features
        WHERE repo_id=? AND metric_id=? AND period_type='month' AND feature=?
          AND period >= ? AND period <= ?
        ORDER BY period
        """,
        (repo_id, metric_id, feature, start_month, end_month),
    ).fetchall()
    return [(str(r["period"]), float(r["value"])) for r in rows if r["value"] is not None]


def basic_stats(values: List[float]) -> dict:
    if not values:
        return {"count": 0}
    return {
        "count": len(values),
        "last": float(values[-1]),
        "mean": float(sum(values) / len(values)),
        "min": float(min(values)),
        "max": float(max(values)),
    }


def dimension_meaning(dimension: str) -> str:
    mapping = {
        "activity_throughput": "产出/协作流水线可能放缓，需关注提交与协作事件是否进入持续下行。",
        "contributors_concentration": "贡献者规模或集中度可能恶化，需关注关键人依赖与新人补给。",
        "collaboration_efficiency": "协作效率可能变差（响应/积压/处理时长），需关注 triage 与流程阻塞。",
        "attention_engagement": "外部关注可能衰减（辅助维度），需结合内部指标判断是否为成熟期自然减速。",
        "openrank_reference": "综合参照轴变化，需与治理维度一起解读。",
    }
    return mapping.get(dimension, "该信号提示某治理维度出现异常变化，建议结合证据复核。")


def compute_signal_confidence(
    base_confidence: float,
    avg_raw_ratio_win3: float,
    window_coverage: float,
    forecast_uncertainty_ratio: float,
) -> float:
    # base_confidence: from signal_events (raw/interp-derived) or composite default
    # avg_raw_ratio_win3: [0,1], higher => more reliable
    # window_coverage: [0,1], missing values reduce confidence
    # forecast_uncertainty_ratio: >=0, higher => less reliable
    unc_penalty = 1.0 / (1.0 + forecast_uncertainty_ratio)
    conf = (
        clamp01(base_confidence)
        * (0.4 + 0.6 * clamp01(avg_raw_ratio_win3))
        * (0.4 + 0.6 * clamp01(window_coverage))
        * unc_penalty
    )
    return clamp01(conf)


def compare_windows(values: List[float], window: int) -> dict:
    # Compare current window (last N) vs previous window (prev N) on mean and delta.
    if window <= 0 or len(values) < window:
        return {"window": window, "current": {}, "previous": {}, "delta": {}}
    current = values[-window:]
    prev = values[-2 * window : -window] if len(values) >= 2 * window else []
    cur_mean = sum(current) / len(current) if current else None
    prev_mean = sum(prev) / len(prev) if prev else None
    delta = None
    pct = None
    if cur_mean is not None and prev_mean is not None:
        delta = cur_mean - prev_mean
        if abs(prev_mean) > 1e-12:
            pct = delta / prev_mean
    return {
        "window": window,
        "current": {"mean": cur_mean, "count": len(current)},
        "previous": {"mean": prev_mean, "count": len(prev)},
        "delta": {"abs": delta, "pct": pct},
    }


def build_signal_evidence(
    conn: sqlite3.Connection,
    signal_defs: Dict[str, dict],
    metric_ids: Dict[str, int],
    repo_id: int,
    signal_row: sqlite3.Row,
    related_rows: List[sqlite3.Row],
    forecast_uncertainty_ratio: float,
    avg_raw_ratio_win3: float,
) -> dict:
    sid = str(signal_row["signal_id"])
    end_month = str(signal_row["end_month"])
    start_month = str(signal_row["start_month"])
    sev = float(signal_row["severity"] or 0.0)  # already weighted to [0,100] by signal_engine
    conf = float(signal_row["confidence"] or 0.0)
    strength = max(0.0, min(1.0, sev / 100.0))

    evidence_ref = str(signal_row["evidence_ref"] or "{}")
    try:
        ev = json.loads(evidence_ref)
        if not isinstance(ev, dict):
            ev = {}
    except Exception:  # noqa: BLE001
        ev = {}

    sdef = signal_defs.get(sid) or {}
    signal_name = str(ev.get("signal_name") or sdef.get("name") or sid)
    dimension = str(ev.get("dimension") or sdef.get("dimension") or "unknown")

    # Find sustained start t0 by merging contiguous event windows for this signal_id in lookback.
    ranges = [(str(r["start_month"]), str(r["end_month"])) for r in related_rows]
    merged = merge_contiguous_ranges(ranges)
    sustained_start = start_month
    sustained_months = max(1, month_to_int(end_month) - month_to_int(start_month) + 1)
    for s, e in merged:
        if month_to_int(s) <= month_to_int(end_month) <= month_to_int(e):
            sustained_start = s
            sustained_months = max(1, month_to_int(e) - month_to_int(s) + 1)
            break

    duration = max(1, month_to_int(end_month) - month_to_int(start_month) + 1)

    # Supporting metrics: use primary metric from metric_id column when available.
    supporting = {}
    metric_id = int(signal_row["metric_id"] or 0)
    metric_name = None
    for name, mid in metric_ids.items():
        if mid == metric_id:
            metric_name = name
            break

    if metric_name:
        series = fetch_series_window(conn, repo_id, metric_id, start_month, end_month)
        values = [v for _, v in series]
        supporting["metric"] = metric_name
        supporting["series_stats"] = basic_stats(values)
        supporting["window_compare"] = compare_windows(values, window=len(values))
        # Common derived features used in this repo
        for feat in ["yoy", "mom", "trend_slope_3", "zscore_12", "raw_ratio_win3", "interp_ratio_win3"]:
            window = fetch_feature_window(conn, repo_id, metric_id, feat, start_month, end_month)
            vals = [v for _, v in window]
            if vals:
                supporting[feat] = basic_stats(vals)

        # Abnormality: zscore and percentile rank over last 24 months up to end_month.
        hist_start = int_to_month(month_to_int(end_month) - 23)
        hist = fetch_series_window(conn, repo_id, metric_id, hist_start, end_month)
        hist_vals = [v for _, v in hist]
        p_rank = percentile_rank(hist_vals, values[-1]) if hist_vals and values else None
        zvals = fetch_feature_window(conn, repo_id, metric_id, "zscore_12", hist_start, end_month)
        z_last = zvals[-1][1] if zvals else None
        supporting["is_abnormal"] = {
            "zscore_12_last": z_last,
            "percentile_rank_24m_last": p_rank,
        }

    # Coverage in the signal window (metric series)
    win_len = max(1, month_to_int(end_month) - month_to_int(start_month) + 1)
    coverage = (supporting.get("series_stats", {}) or {}).get("count", 0) / float(win_len)
    signal_conf = compute_signal_confidence(conf, avg_raw_ratio_win3, float(coverage), forecast_uncertainty_ratio)

    # Evidence refs for visualization: keep declarative, not a chart.
    evidence_refs = {
        "window": {"start_month": start_month, "end_month": end_month},
        "series": [],
        "notes": "Plot raw series + rolling trend/YoY/zscore and highlight the trigger window for audit.",
    }
    if metric_name:
        evidence_refs["series"].extend(
            [
                {"name": f"raw_{metric_name}", "source": "time_series"},
                {"name": f"feat_{metric_name}_yoy", "source": "derived_features"},
                {"name": f"feat_{metric_name}_trend_slope_3", "source": "derived_features"},
                {"name": f"feat_{metric_name}_zscore_12", "source": "derived_features"},
            ]
        )

    return {
        "signal_id": sid,
        "signal_name": signal_name,
        "dimension": dimension,
        "when": {"start_month": start_month, "end_month": end_month, "duration_months": duration},
        "time_window": {
            "t0": sustained_start,
            "t_end": end_month,
            "sustained_months": sustained_months,
        },
        "signal_strength": strength,
        "signal_confidence": signal_conf,
        "supporting_metrics": supporting,
        "is_abnormal": supporting.get("is_abnormal") if isinstance(supporting, dict) else None,
        "evidence_refs": evidence_refs,
        "visual_evidence": {
            "window": {"start_month": start_month, "end_month": end_month},
            "recommended_charts": [
                "raw_series_line",
                "rolling_mean_overlay",
                "yoy_line",
                "zscore_line",
                "raw_ratio_bar",
            ],
        },
        "governance_meaning": dimension_meaning(dimension),
        "thresholds": {
            "severity_level": ev.get("signal_severity") or sdef.get("severity"),
            "window": ev.get("signal_window") or sdef.get("window"),
            "consistency": ev.get("signal_consistency") or sdef.get("consistency"),
        },
    }


def build_data_quality(
    conn: sqlite3.Connection,
    metric_ids: Dict[str, int],
    repo_id: int,
    as_of_month: str,
    window_months: int,
    metrics: List[str],
) -> dict:
    start = int_to_month(month_to_int(as_of_month) - (window_months - 1))
    out = {"window": {"start_month": start, "end_month": as_of_month}, "metrics": {}, "avg_raw_ratio_win3": 0.0}
    raw_ratios: List[float] = []
    coverages: List[float] = []
    for m in metrics:
        mid = metric_ids.get(m)
        if not mid:
            continue
        series = fetch_series_window(conn, repo_id, mid, start, as_of_month)
        coverage = len(series) / float(window_months) if window_months else 0.0
        coverages.append(float(coverage))
        rr = fetch_feature_window(conn, repo_id, mid, "raw_ratio_win3", start, as_of_month)
        rr_vals = [v for _, v in rr]
        rr_mean = float(sum(rr_vals) / len(rr_vals)) if rr_vals else 0.0
        if rr_vals:
            raw_ratios.append(rr_mean)
        out["metrics"][m] = {"coverage": coverage, "raw_ratio_win3_mean": rr_mean}
    out["avg_raw_ratio_win3"] = float(sum(raw_ratios) / len(raw_ratios)) if raw_ratios else 0.0
    out["avg_coverage"] = float(sum(coverages) / len(coverages)) if coverages else 0.0
    out["missing_rate"] = float(1.0 - out["avg_coverage"]) if coverages else 1.0
    return out


def main() -> None:
    args = parse_args()
    sources_path = Path(args.sources)
    model_cfg = load_yaml(Path(args.model))
    signals_cfg = load_yaml(Path(args.signals))
    inputs = model_cfg.get("inputs") or {}
    task = model_cfg.get("task") or {}
    window_months = int(task.get("input_window_months", 18))
    metrics = list(inputs.get("metrics") or [])

    db_path = get_sqlite_path(sources_path, args.db)
    conn = connect(db_path)
    try:
        ensure_risk_report_table(conn)
        repo_map = configured_repo_ids(conn, sources_path)
        metric_ids = metric_id_map(conn)
        signal_defs = parse_signal_defs(signals_cfg)

        model_version = args.model_version or latest_model_version(conn, args.model_type)
        if not model_version:
            raise SystemExit("No trained model found in ml_models for this model_type")
        as_of = args.as_of_month or latest_as_of_month(conn, args.model_type, model_version)
        if not as_of:
            raise SystemExit("No risk_predictions found for this model_type/model_version")

        if args.replace:
            conn.execute(
                "DELETE FROM risk_reports WHERE as_of_month=? AND model_type=? AND model_version=?",
                (as_of, args.model_type, model_version),
            )
            conn.commit()

        # Load predictions snapshot
        pred_rows = conn.execute(
            """
            SELECT repo_id, p_calibrated, p_raw, risk_level, needs_review, forecast_json, explain_json
            FROM risk_predictions
            WHERE model_type=? AND model_version=? AND as_of_month=?
            """,
            (args.model_type, model_version, as_of),
        ).fetchall()

        start_lb = lookback_start(as_of, args.lookback_months)
        created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

        out_rows = []
        seen_repo_ids = set()
        for pr in pred_rows:
            repo_id = int(pr["repo_id"])
            if repo_id not in repo_map:
                continue
            seen_repo_ids.add(repo_id)
            repo_name = repo_map[repo_id]

            try:
                forecast = json.loads(pr["forecast_json"]) if pr["forecast_json"] else {}
            except Exception:  # noqa: BLE001
                forecast = {}
            try:
                explain_aux = json.loads(pr["explain_json"]) if pr["explain_json"] else {}
            except Exception:  # noqa: BLE001
                explain_aux = {}
            model_uncertainty = {
                "forecast_uncertainty_ratio": compute_forecast_uncertainty_ratio(forecast),
            }

            # Top-N signal events within lookback (end_month in [start_lb, as_of])
            sig_rows = conn.execute(
                """
                SELECT signal_id, metric_id, start_month, end_month, confidence, severity, evidence_ref
                FROM signal_events
                WHERE repo_id=? AND end_month >= ? AND end_month <= ?
                """,
                (repo_id, start_lb, as_of),
            ).fetchall()
            # Dedup by signal_id keeping best weighted score
            best: Dict[str, sqlite3.Row] = {}
            best_score: Dict[str, float] = {}
            for r in sig_rows:
                sid = str(r["signal_id"])
                sev = float(r["severity"] or 0.0)
                conf = float(r["confidence"] or 0.0)
                score = sev * (0.5 + 0.5 * conf)
                if score > best_score.get(sid, -1.0):
                    best_score[sid] = score
                    best[sid] = r
            selected = [best[sid] for sid, _ in sorted(best_score.items(), key=lambda x: x[1], reverse=True)[: max(1, args.top_n_signals)]]
            data_quality = build_data_quality(conn, metric_ids, repo_id, as_of, window_months, metrics)
            avg_rr = float(data_quality.get("avg_raw_ratio_win3") or 0.0)
            unc_ratio = float(model_uncertainty.get("forecast_uncertainty_ratio") or 0.0)

            main_signals = []
            for r in selected:
                sid = str(r["signal_id"])
                rel = [row for row in sig_rows if str(row["signal_id"]) == sid]
                main_signals.append(
                    build_signal_evidence(
                        conn,
                        signal_defs,
                        metric_ids,
                        repo_id,
                        r,
                        related_rows=rel,
                        forecast_uncertainty_ratio=unc_ratio,
                        avg_raw_ratio_win3=avg_rr,
                    )
                )

            # Multi-dimension consistency summary for top signals (used as additional evidence).
            dims = sorted({str(s.get("dimension")) for s in main_signals if s.get("dimension")})
            evidence_chain = {
                "lookback_months": args.lookback_months,
                "lookback_start": start_lb,
                "lookback_end": as_of,
                "top_signal_dimensions": dims,
                "top_signal_dimensions_count": len(dims),
            }

            report = {
                "repo": repo_name,
                "as_of_month": as_of,
                "risk_score": float(pr["p_calibrated"]),
                "risk_level": str(pr["risk_level"]),
                "needs_review": bool(int(pr["needs_review"])),
                "model": {"type": args.model_type, "version": model_version},
                "main_signals": main_signals,
                "evidence_chain": evidence_chain,
                "data_quality": data_quality,
                "model_uncertainty": model_uncertainty,
                "aux_explain": explain_aux,  # keep auxiliary model attribution if present
            }
            out_rows.append(
                (
                    repo_id,
                    as_of,
                    args.model_type,
                    model_version,
                    json.dumps(report, ensure_ascii=True),
                    created_at,
                )
            )

        # Add placeholders for configured repos without predictions.
        missing_repo_ids = sorted(set(repo_map.keys()) - seen_repo_ids)
        for repo_id in missing_repo_ids:
            repo_name = repo_map[repo_id]
            data_quality = build_data_quality(conn, metric_ids, repo_id, as_of, window_months, metrics)
            evidence_chain = {
                "lookback_months": args.lookback_months,
                "lookback_start": start_lb,
                "lookback_end": as_of,
                "top_signal_dimensions": [],
                "top_signal_dimensions_count": 0,
            }
            report = {
                "repo": repo_name,
                "as_of_month": as_of,
                "risk_score": 0.0,
                "risk_level": "Low",
                "needs_review": True,
                "model": {"type": args.model_type, "version": model_version},
                "main_signals": [],
                "evidence_chain": evidence_chain,
                "data_quality": data_quality,
                "model_uncertainty": {"forecast_uncertainty_ratio": 0.0},
                "aux_explain": {},
                "note": "no_prediction_available",
            }
            out_rows.append(
                (
                    repo_id,
                    as_of,
                    args.model_type,
                    model_version,
                    json.dumps(report, ensure_ascii=True),
                    created_at,
                )
            )

        conn.executemany(
            """
            INSERT INTO risk_reports
              (repo_id, as_of_month, model_type, model_version, report_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(repo_id, as_of_month, model_type, model_version) DO UPDATE SET
              report_json=excluded.report_json,
              created_at=excluded.created_at
            """,
            out_rows,
        )
        conn.commit()
        print(
            f"[build_risk_explanations] as_of={as_of} model={args.model_type}/{model_version} repos={len(out_rows)} lookback={args.lookback_months}m"
        )
    finally:
        conn.close()


if __name__ == "__main__":
    main()
