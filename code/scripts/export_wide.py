#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import sqlite3
from pathlib import Path
from typing import Dict, List, Tuple

import yaml


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export wide table from SQLite")
    parser.add_argument("--sources", required=True, help="Path to sources.yaml")
    parser.add_argument("--metrics", required=True, help="Path to metrics.yaml")
    parser.add_argument("--period-type", default="month", choices=["month", "quarter", "year"])
    parser.add_argument("--db", default=None, help="Override sqlite db path")
    parser.add_argument(
        "--output",
        default="data/exports/wide_repo_month.csv",
        help="Output CSV path",
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


def read_metric_map(conn: sqlite3.Connection, metrics_cfg: dict) -> Dict[int, str]:
    metric_files = {m["file"] for m in (metrics_cfg.get("metrics") or [])}
    metric_map: Dict[int, str] = {}
    query = "SELECT id, name, file FROM metrics"
    for row in conn.execute(query):
        if row["file"] in metric_files:
            metric_map[row["id"]] = row["name"]
    return metric_map


def read_repo_map(conn: sqlite3.Connection, sources_cfg: dict) -> Dict[int, str]:
    repos_cfg = sources_cfg.get("repos") or []
    allowed = {f"{r['org']}/{r['repo']}" for r in repos_cfg}
    repo_map: Dict[int, str] = {}
    query = "SELECT id, full_name FROM repos"
    for row in conn.execute(query):
        if row["full_name"] in allowed:
            repo_map[row["id"]] = row["full_name"]
    return repo_map


def export_wide(
    conn: sqlite3.Connection,
    repo_map: Dict[int, str],
    metric_map: Dict[int, str],
    period_type: str,
    output_path: Path,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    metric_ids = sorted(metric_map.keys())
    metric_names = [metric_map[m] for m in metric_ids]

    query = """
        SELECT repo_id, metric_id, period, value
        FROM time_series
        WHERE is_raw = 0 AND period_type = ?
    """

    rows_by_key: Dict[Tuple[int, str], Dict[str, float]] = {}
    for row in conn.execute(query, (period_type,)):
        repo_id = row["repo_id"]
        metric_id = row["metric_id"]
        if repo_id not in repo_map or metric_id not in metric_map:
            continue
        key = (repo_id, row["period"])
        rows_by_key.setdefault(key, {})[metric_map[metric_id]] = row["value"]

    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["repo", "period"] + metric_names)
        for (repo_id, period), values in sorted(rows_by_key.items(), key=lambda x: (x[0][0], x[0][1])):
            row = [repo_map[repo_id], period]
            for name in metric_names:
                row.append(values.get(name, ""))
            writer.writerow(row)


def main() -> None:
    args = parse_args()
    sources_path = Path(args.sources)
    metrics_path = Path(args.metrics)

    sources_cfg = load_yaml(sources_path)
    metrics_cfg = load_yaml(metrics_path)

    db_path = get_sqlite_path(sources_path, args.db)
    conn = connect(db_path)

    try:
        repo_map = read_repo_map(conn, sources_cfg)
        metric_map = read_metric_map(conn, metrics_cfg)
        export_wide(conn, repo_map, metric_map, args.period_type, Path(args.output))
    finally:
        conn.close()


if __name__ == "__main__":
    main()
