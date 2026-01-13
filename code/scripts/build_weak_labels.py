#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build weak supervision labels from signal_events")
    p.add_argument("--sources", required=True, help="Path to sources.yaml")
    p.add_argument("--model", default="configs/model.yaml", help="Path to model.yaml")
    p.add_argument("--db", default=None, help="Override sqlite db path")
    p.add_argument("--period-type", default="month", choices=["month"], help="Only month supported")
    p.add_argument("--replace", action="store_true", help="Drop and rebuild label tables")
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


def month_sequence(start_month: str, end_month: str) -> List[str]:
    s = month_to_int(start_month)
    e = month_to_int(end_month)
    if e < s:
        return []
    return [int_to_month(x) for x in range(s, e + 1)]


@dataclass(frozen=True)
class LabelCfg:
    horizon_months: int
    exclude_signal_ids: set[str]
    include_signal_ids: set[str]
    score_cap: float
    soft_scale: float
    binary_threshold: float
    pos_min_confidence: float
    pos_weight: float
    unlabeled_weight: float


def parse_label_cfg(model_cfg: dict) -> LabelCfg:
    task = model_cfg.get("task") or {}
    labels = model_cfg.get("labels") or {}
    agg = labels.get("aggregation") or {}
    score_to_soft = agg.get("score_to_soft") or {}
    pu = labels.get("pu_weighting") or {}
    include = set(labels.get("include_signal_ids") or [])
    exclude = set(labels.get("exclude_signal_ids") or [])
    return LabelCfg(
        horizon_months=int(task.get("horizon_months", 3)),
        exclude_signal_ids=exclude,
        include_signal_ids=include,
        score_cap=float(agg.get("score_cap", 100.0)),
        soft_scale=float(score_to_soft.get("scale", 40.0)),
        binary_threshold=float(agg.get("binary_threshold", 0.5)),
        pos_min_confidence=float(pu.get("pos_min_confidence", 0.34)),
        pos_weight=float(pu.get("pos_weight", 3.0)),
        unlabeled_weight=float(pu.get("unlabeled_weight", 0.5)),
    )


def label_params(model_cfg: dict) -> tuple[int, float]:
    labels = model_cfg.get("labels") or {}
    agg = labels.get("aggregation") or {}
    min_dims = int(agg.get("min_dimensions_for_positive", 2))
    duration_w = float(agg.get("duration_weight", 0.25))
    return min_dims, duration_w


def ensure_tables(conn: sqlite3.Connection, replace: bool) -> None:
    if replace:
        conn.execute("DROP TABLE IF EXISTS weak_labels")
        conn.execute("DROP TABLE IF EXISTS weak_label_meta")
        conn.commit()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS weak_labels (
            id INTEGER PRIMARY KEY,
            repo_id INTEGER NOT NULL,
            as_of_month TEXT NOT NULL,
            horizon_months INTEGER NOT NULL,
            risk_score REAL NOT NULL,
            risk_soft REAL NOT NULL,
            risk_binary INTEGER NOT NULL,
            sample_weight REAL NOT NULL,
            events_count INTEGER NOT NULL,
            mean_event_confidence REAL NOT NULL,
            evidence_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(repo_id, as_of_month, horizon_months)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS weak_label_meta (
            id INTEGER PRIMARY KEY,
            key TEXT NOT NULL UNIQUE,
            value TEXT NOT NULL
        )
        """
    )
    conn.commit()


def configured_repo_ids(conn: sqlite3.Connection, sources_path: Path) -> Dict[int, str]:
    sources = load_yaml(sources_path)
    enabled_names = {
        f"{r.get('org')}/{r.get('repo')}"
        for r in (sources.get("repos") or [])
        if isinstance(r, dict) and r.get("enabled", True)
    }
    rows = conn.execute("SELECT id, full_name FROM repos").fetchall()
    return {int(r["id"]): str(r["full_name"]) for r in rows if str(r["full_name"]) in enabled_names}


def repo_month_bounds(conn: sqlite3.Connection, repo_ids: Iterable[int]) -> Dict[int, Tuple[str, str]]:
    bounds: Dict[int, Tuple[str, str]] = {}
    for rid in repo_ids:
        row = conn.execute(
            """
            SELECT MIN(period) AS min_m, MAX(period) AS max_m
            FROM time_series
            WHERE repo_id = ? AND period_type = 'month' AND is_raw = 0
            """,
            (rid,),
        ).fetchone()
        if not row or not row["min_m"] or not row["max_m"]:
            continue
        bounds[rid] = (str(row["min_m"]), str(row["max_m"]))
    return bounds


def fetch_signal_events(conn: sqlite3.Connection, repo_id: int) -> List[sqlite3.Row]:
    return conn.execute(
        """
        SELECT signal_id, start_month, end_month, confidence, severity, evidence_ref
        FROM signal_events
        WHERE repo_id = ?
        ORDER BY end_month
        """,
        (repo_id,),
    ).fetchall()


def soft_from_score(score: float, scale: float) -> float:
    # soft = 1 - exp(-score/scale), clipped to [0, 1]
    if scale <= 0:
        return 0.0
    v = 1.0 - math.exp(-max(0.0, score) / scale)
    return max(0.0, min(1.0, v))


def main() -> None:
    args = parse_args()
    sources_path = Path(args.sources)
    model_path = Path(args.model)
    model_cfg = load_yaml(model_path)
    label_cfg = parse_label_cfg(model_cfg)
    min_dims_for_pos, duration_weight = label_params(model_cfg)

    db_path = get_sqlite_path(sources_path, args.db)
    conn = connect(db_path)
    try:
        ensure_tables(conn, args.replace)

        repo_map = configured_repo_ids(conn, sources_path)
        bounds = repo_month_bounds(conn, repo_map.keys())

        created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        conn.execute(
            """
            INSERT INTO weak_label_meta (key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value
            """,
            ("model_yaml", str(model_path)),
        )
        conn.execute(
            """
            INSERT INTO weak_label_meta (key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value
            """,
            ("created_at", created_at),
        )
        conn.commit()

        total_rows = 0
        for repo_id, repo_name in sorted(repo_map.items(), key=lambda x: x[1]):
            if repo_id not in bounds:
                continue
            min_m, max_m = bounds[repo_id]
            months = month_sequence(min_m, max_m)
            if not months:
                continue

            events = fetch_signal_events(conn, repo_id)

            # index events by end_month for fast lookups
            events_by_end: Dict[str, List[sqlite3.Row]] = {}
            for e in events:
                sid = str(e["signal_id"])
                if label_cfg.include_signal_ids and sid not in label_cfg.include_signal_ids:
                    continue
                if sid in label_cfg.exclude_signal_ids:
                    continue
                events_by_end.setdefault(str(e["end_month"]), []).append(e)

            month_ints = [month_to_int(m) for m in months]
            month_set = set(months)

            rows_to_insert = []
            for t_month in months:
                t_int = month_to_int(t_month)
                fut_start = t_int + 1
                fut_end = t_int + label_cfg.horizon_months
                future_months = [int_to_month(x) for x in range(fut_start, fut_end + 1)]
                future_months = [m for m in future_months if m in month_set]

                score = 0.0
                conf_vals: List[float] = []
                event_summaries: List[dict] = []
                events_count = 0
                dim_set: set[str] = set()
                for m in future_months:
                    for e in events_by_end.get(m, []):
                        sev = float(e["severity"] or 0.0)
                        conf = float(e["confidence"] or 0.0)
                        start_m = str(e["start_month"])
                        end_m = str(e["end_month"])
                        duration = max(1, month_to_int(end_m) - month_to_int(start_m) + 1)
                        score += (sev * (0.5 + 0.5 * conf)) * (1.0 + duration_weight * (duration - 1))
                        conf_vals.append(conf)
                        events_count += 1
                        try:
                            ev = json.loads(e["evidence_ref"]) if e["evidence_ref"] else {}
                            dim = ev.get("dimension")
                            if isinstance(dim, str) and dim:
                                dim_set.add(dim)
                        except Exception:  # noqa: BLE001
                            pass
                        event_summaries.append(
                            {
                                "signal_id": str(e["signal_id"]),
                                "start_month": start_m,
                                "end_month": end_m,
                                "duration_months": duration,
                                "severity": sev,
                                "confidence": conf,
                            }
                        )

                score = min(label_cfg.score_cap, score)
                risk_soft = soft_from_score(score, label_cfg.soft_scale)
                risk_binary = 1 if risk_soft >= label_cfg.binary_threshold else 0
                mean_conf = sum(conf_vals) / len(conf_vals) if conf_vals else 0.0
                dim_count = len(dim_set)

                # PU weighting: only treat as "high-confidence positive" when binary positive + confidence ok.
                if risk_binary == 1 and mean_conf >= label_cfg.pos_min_confidence and dim_count >= min_dims_for_pos:
                    w = label_cfg.pos_weight
                else:
                    w = label_cfg.unlabeled_weight

                evidence = {
                    "repo": repo_name,
                    "as_of_month": t_month,
                    "horizon_months": label_cfg.horizon_months,
                    "risk_score": score,
                    "risk_soft": risk_soft,
                    "risk_binary": risk_binary,
                    "events_count": events_count,
                    "mean_event_confidence": mean_conf,
                    "dimensions_triggered": sorted(dim_set),
                    "events": event_summaries[:200],  # cap to keep rows small
                }
                rows_to_insert.append(
                    (
                        repo_id,
                        t_month,
                        label_cfg.horizon_months,
                        float(score),
                        float(risk_soft),
                        int(risk_binary),
                        float(w),
                        int(events_count),
                        float(mean_conf),
                        json.dumps(evidence, ensure_ascii=True),
                        created_at,
                    )
                )

            conn.executemany(
                """
                INSERT INTO weak_labels
                    (repo_id, as_of_month, horizon_months, risk_score, risk_soft, risk_binary,
                     sample_weight, events_count, mean_event_confidence, evidence_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(repo_id, as_of_month, horizon_months) DO UPDATE SET
                    risk_score=excluded.risk_score,
                    risk_soft=excluded.risk_soft,
                    risk_binary=excluded.risk_binary,
                    sample_weight=excluded.sample_weight,
                    events_count=excluded.events_count,
                    mean_event_confidence=excluded.mean_event_confidence,
                    evidence_json=excluded.evidence_json,
                    created_at=excluded.created_at
                """,
                rows_to_insert,
            )
            conn.commit()
            total_rows += len(rows_to_insert)

        print(f"[build_weak_labels] db={db_path} rows={total_rows} horizon={label_cfg.horizon_months}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
