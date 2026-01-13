#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.iotdb.storage_manager import IoTDBManager, load_config


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync SQLite data into IoTDB")
    parser.add_argument("--sources", required=True, help="Path to sources.yaml")
    parser.add_argument("--iotdb", required=True, help="Path to iotdb.yaml")
    parser.add_argument("--period-type", default="month", choices=["month", "quarter", "year"])
    parser.add_argument("--include-feat", action="store_true", help="Write derived features")
    parser.add_argument("--include-raw", action="store_true", help="Write raw metrics")
    parser.add_argument("--include-meta", action="store_true", help="Write repo meta as TEXT")
    parser.add_argument("--recent-months", type=int, default=None, help="Only sync last N months")
    parser.add_argument("--log-path", default="data/iotdb_sync_log.jsonl", help="Sync log path")
    return parser.parse_args()


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def get_sqlite_path(sources_path: Path) -> Path:
    sources = load_yaml(sources_path)
    defaults = sources.get("defaults") or {}
    return Path(defaults.get("sqlite_path", "data/sqlite/opendigger.db"))


def connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def repo_lookup(conn: sqlite3.Connection) -> Dict[int, Tuple[str, str, str]]:
    rows = conn.execute("SELECT id, platform, org, repo FROM repos").fetchall()
    return {row["id"]: (row["platform"], row["org"], row["repo"]) for row in rows}


def metric_lookup(conn: sqlite3.Connection) -> Dict[int, str]:
    rows = conn.execute("SELECT id, name FROM metrics").fetchall()
    return {row["id"]: row["name"] for row in rows}


def fetch_raw_series(conn: sqlite3.Connection, period_type: str) -> List[sqlite3.Row]:
    query = """
        SELECT repo_id, metric_id, period, value
        FROM time_series
        WHERE is_raw = 0 AND period_type = ?
    """
    return conn.execute(query, (period_type,)).fetchall()


def fetch_feat_series(conn: sqlite3.Connection, period_type: str) -> List[sqlite3.Row]:
    query = """
        SELECT repo_id, metric_id, period, feature, value
        FROM derived_features
        WHERE period_type = ?
    """
    return conn.execute(query, (period_type,)).fetchall()


def period_to_key(period: str) -> Tuple[int, int]:
    if len(period) == 7:
        y, m = period.split("-")
        return int(y), int(m)
    return 0, 0


def filter_recent_months(rows: List[sqlite3.Row], recent_months: int) -> List[sqlite3.Row]:
    periods = sorted({row["period"] for row in rows if len(row["period"]) == 7})
    if not periods:
        return rows
    last_year, last_month = period_to_key(periods[-1])
    cutoff = (last_year * 12 + last_month) - (recent_months - 1)

    filtered = []
    for row in rows:
        if len(row["period"]) != 7:
            filtered.append(row)
            continue
        y, m = period_to_key(row["period"])
        if (y * 12 + m) >= cutoff:
            filtered.append(row)
    return filtered


def load_repo_meta(sources_path: Path) -> Dict[str, Dict[str, str]]:
    sources = load_yaml(sources_path)
    meta = {}
    for repo in sources.get("repos", []):
        info = repo.get("meta") or {}
        if not info:
            continue
        full_name = f"{repo.get('org')}/{repo.get('repo')}"
        meta[full_name] = {k: str(v) for k, v in info.items()}
    return meta


def main() -> None:
    args = parse_args()
    db_path = get_sqlite_path(Path(args.sources))
    conn = connect(db_path)

    try:
        repos = repo_lookup(conn)
        metrics = metric_lookup(conn)
        raw_rows = fetch_raw_series(conn, args.period_type) if args.include_raw else []
        feat_rows = fetch_feat_series(conn, args.period_type) if args.include_feat else []

        if args.recent_months and args.period_type == "month":
            raw_rows = filter_recent_months(raw_rows, args.recent_months)
            feat_rows = filter_recent_months(feat_rows, args.recent_months)

        cfg = load_config(args.iotdb)
        manager = IoTDBManager(cfg)
        manager.open()
        manager.ensure_databases()

        total_points = 0
        try:
            batch_device_ids: List[str] = []
            batch_timestamps: List[int] = []
            batch_measurements: List[List[str]] = []
            batch_values: List[List[float]] = []

            grouped: Dict[Tuple[int, str], Dict[str, float]] = defaultdict(dict)
            for row in raw_rows:
                repo_id = row["repo_id"]
                metric = metrics.get(row["metric_id"], "unknown")
                period = row["period"]
                meas = manager.measurement_name("raw", metric)
                grouped[(repo_id, period)][meas] = float(row["value"])

            for row in feat_rows:
                repo_id = row["repo_id"]
                metric = metrics.get(row["metric_id"], "unknown")
                period = row["period"]
                feature = row["feature"]
                meas = manager.measurement_name("feat", metric, feature)
                grouped[(repo_id, period)][meas] = float(row["value"])

            for (repo_id, period), measurements in grouped.items():
                platform, org, repo = repos[repo_id]
                device_id = manager.device_id(platform, org, repo)
                timestamp_ms = manager.period_to_timestamp(period)
                batch_device_ids.append(device_id)
                batch_timestamps.append(timestamp_ms)
                batch_measurements.append(list(measurements.keys()))
                batch_values.append(list(measurements.values()))
                total_points += len(measurements)

                if len(batch_device_ids) >= cfg.batch_size:
                    manager.insert_batch_aligned(
                        batch_device_ids,
                        batch_timestamps,
                        batch_measurements,
                        batch_values,
                    )
                    batch_device_ids.clear()
                    batch_timestamps.clear()
                    batch_measurements.clear()
                    batch_values.clear()

            if batch_device_ids:
                manager.insert_batch_aligned(
                    batch_device_ids,
                    batch_timestamps,
                    batch_measurements,
                    batch_values,
                )

            if args.include_meta:
                meta = load_repo_meta(Path(args.sources))
                for repo_id, (platform, org, repo) in repos.items():
                    full_name = f"{org}/{repo}"
                    info = meta.get(full_name)
                    if not info:
                        continue
                    device_id = manager.device_id(platform, org, repo)
                    timestamp_ms = 0
                    measurements = [f"meta_{k}" for k in info.keys()]
                    values = list(info.values())
                    manager.insert_record(device_id, timestamp_ms, measurements, values)

        finally:
            manager.close()
    finally:
        conn.close()

    log_path = Path(args.log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "period_type": args.period_type,
        "include_raw": args.include_raw,
        "include_feat": args.include_feat,
        "include_meta": args.include_meta,
        "recent_months": args.recent_months,
        "total_points": total_points,
    }
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=True) + "\n")


if __name__ == "__main__":
    main()
