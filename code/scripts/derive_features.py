#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import sqlite3
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

import yaml


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Derive features from OpenDigger time series")
    parser.add_argument("--sources", required=True, help="Path to sources.yaml")
    parser.add_argument("--db", default=None, help="Override sqlite db path")
    parser.add_argument("--period-type", default="month", choices=["month", "quarter", "year"])
    parser.add_argument("--window", type=int, default=3, help="Rolling window size (legacy)")
    parser.add_argument("--windows", default=None, help="Comma-separated windows, e.g. 3,6,12")
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


def ensure_feature_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS derived_features (
            id INTEGER PRIMARY KEY,
            repo_id INTEGER NOT NULL,
            metric_id INTEGER NOT NULL,
            period TEXT NOT NULL,
            period_type TEXT NOT NULL,
            feature TEXT NOT NULL,
            value REAL NOT NULL,
            FOREIGN KEY (repo_id) REFERENCES repos(id),
            FOREIGN KEY (metric_id) REFERENCES metrics(id),
            UNIQUE (repo_id, metric_id, period, period_type, feature)
        )
        """
    )
    conn.commit()


def fetch_series(conn: sqlite3.Connection, period_type: str) -> Dict[Tuple[int, int], Dict[str, float]]:
    query = """
        SELECT repo_id, metric_id, period, value
        FROM time_series
        WHERE is_raw = 0 AND period_type = ?
    """
    series: Dict[Tuple[int, int], Dict[str, float]] = defaultdict(dict)
    for row in conn.execute(query, (period_type,)):
        series[(row["repo_id"], row["metric_id"])][row["period"]] = row["value"]
    return series


def fetch_object_series(
    conn: sqlite3.Connection, period_type: str
) -> Dict[Tuple[int, int, str], Dict[str, float]]:
    query = """
        SELECT repo_id, metric_id, period, json_value
        FROM time_series_object
        WHERE is_raw = 0 AND period_type = ?
    """
    series: Dict[Tuple[int, int, str], Dict[str, float]] = defaultdict(dict)
    for row in conn.execute(query, (period_type,)):
        try:
            payload = json.loads(row["json_value"])
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        if "avg" in payload and isinstance(payload["avg"], (int, float)):
            series[(row["repo_id"], row["metric_id"], "avg")][row["period"]] = float(
                payload["avg"]
            )
        if "quantile_4" in payload and isinstance(payload["quantile_4"], (int, float)):
            series[(row["repo_id"], row["metric_id"], "p95")][row["period"]] = float(
                payload["quantile_4"]
            )
    return series


def rolling_mean(values: List[float]) -> float:
    return sum(values) / len(values) if values else math.nan


def rolling_slope(values: List[float]) -> float:
    if len(values) < 2:
        return math.nan
    return (values[-1] - values[0]) / (len(values) - 1)


def rolling_std(values: List[float]) -> float:
    if not values:
        return math.nan
    mean = sum(values) / len(values)
    var = sum((v - mean) ** 2 for v in values) / len(values)
    return math.sqrt(var)


def zscore(values: List[float], current: float) -> float:
    if len(values) < 2:
        return math.nan
    mean = sum(values) / len(values)
    std = rolling_std(values)
    if std == 0:
        return math.nan
    return (current - mean) / std


def derive_features_for_series(
    periods: List[str], values: Dict[str, float], windows: List[int]
) -> Dict[str, Dict[str, float]]:
    features: Dict[str, Dict[str, float]] = defaultdict(dict)
    for idx, period in enumerate(periods):
        val = values[period]
        features[period]["value"] = val
        prev_period = periods[idx - 1] if idx >= 1 else None
        yoy_period = periods[idx - 12] if idx >= 12 else None

        if prev_period is not None and values.get(prev_period) not in (None, 0):
            features[period]["mom"] = (val - values[prev_period]) / values[prev_period]
        if yoy_period is not None and values.get(yoy_period) not in (None, 0):
            features[period]["yoy"] = (val - values[yoy_period]) / values[yoy_period]

        for window in windows:
            window_periods = periods[max(0, idx - window + 1) : idx + 1]
            window_vals = [values[p] for p in window_periods]
            features[period][f"roll_mean_{window}"] = rolling_mean(window_vals)
            slope = rolling_slope(window_vals)
            features[period][f"trend_slope_{window}"] = slope
            features[period][f"roll_std_{window}"] = rolling_std(window_vals)
            features[period][f"zscore_{window}"] = zscore(window_vals, val)
            if window == 3:
                if not math.isnan(slope):
                    if slope > 0:
                        trend_dir = 1.0
                    elif slope < 0:
                        trend_dir = -1.0
                    else:
                        trend_dir = 0.0
                    features[period]["trend_dir"] = trend_dir
    return features


def write_features(
    conn: sqlite3.Connection,
    key: Tuple[int, int],
    period_type: str,
    feature_map: Dict[str, Dict[str, float]],
    feature_prefix: str | None = None,
) -> int:
    rows = []
    repo_id, metric_id = key
    for period, feats in feature_map.items():
        for name, value in feats.items():
            if value is None or math.isnan(value):
                continue
            feature_name = f"{feature_prefix}{name}" if feature_prefix else name
            rows.append((repo_id, metric_id, period, period_type, feature_name, float(value)))
    conn.executemany(
        """
        INSERT INTO derived_features
            (repo_id, metric_id, period, period_type, feature, value)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(repo_id, metric_id, period, period_type, feature) DO UPDATE SET
            value=excluded.value
        """,
        rows,
    )
    conn.commit()
    return len(rows)


def add_raw_interp_ratio(
    conn: sqlite3.Connection,
    period_type: str,
    windows: List[int],
) -> None:
    query = """
        SELECT repo_id, metric_id, period, is_raw
        FROM time_series
        WHERE period_type = ?
    """
    series: Dict[Tuple[int, int], Dict[str, int]] = defaultdict(dict)
    for row in conn.execute(query, (period_type,)):
        series[(row["repo_id"], row["metric_id"])][row["period"]] = row["is_raw"]

    object_keys: set[Tuple[int, int]] = set()
    obj_query = """
        SELECT repo_id, metric_id, period, is_raw
        FROM time_series_object
        WHERE period_type = ?
    """
    for row in conn.execute(obj_query, (period_type,)):
        object_keys.add((row["repo_id"], row["metric_id"]))
        series[(row["repo_id"], row["metric_id"])].setdefault(row["period"], row["is_raw"])

    for (repo_id, metric_id), period_map in series.items():
        periods = sorted(period_map.keys())
        for idx, period in enumerate(periods):
            for window in windows:
                window_periods = periods[max(0, idx - window + 1) : idx + 1]
                raw_cnt = sum(period_map[p] for p in window_periods)
                total = len(window_periods)
                if total == 0:
                    continue
                raw_ratio = raw_cnt / total
                interp_ratio = 1 - raw_ratio
                feature_rows = [
                    (f"raw_ratio_win{window}", raw_ratio),
                    (f"interp_ratio_win{window}", interp_ratio),
                ]

                # Object metrics (stored in time_series_object) produce derived features like
                # avg_* / p95_* (see fetch_object_series + write_features(feature_prefix=...)).
                # Emit matching raw/interp ratio features so signals.yaml can reference:
                #   issue_response_time.p95_raw_ratio_win3, etc.
                if (repo_id, metric_id) in object_keys:
                    feature_rows.extend(
                        [
                            (f"avg_raw_ratio_win{window}", raw_ratio),
                            (f"avg_interp_ratio_win{window}", interp_ratio),
                            (f"p95_raw_ratio_win{window}", raw_ratio),
                            (f"p95_interp_ratio_win{window}", interp_ratio),
                        ]
                    )

                conn.executemany(
                    """
                    INSERT INTO derived_features
                        (repo_id, metric_id, period, period_type, feature, value)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(repo_id, metric_id, period, period_type, feature) DO UPDATE SET
                        value=excluded.value
                    """,
                    [
                        (repo_id, metric_id, period, period_type, feat, float(val))
                        for feat, val in feature_rows
                    ],
                )
    conn.commit()


def main() -> None:
    args = parse_args()
    db_path = get_sqlite_path(Path(args.sources), args.db)
    conn = connect(db_path)

    try:
        ensure_feature_table(conn)
        windows = [args.window]
        if args.windows:
            windows = [int(w.strip()) for w in args.windows.split(",") if w.strip()]
        series = fetch_series(conn, args.period_type)
        total_rows = 0
        for key, values in series.items():
            periods = sorted(values.keys())
            feature_map = derive_features_for_series(periods, values, windows)
            total_rows += write_features(conn, key, args.period_type, feature_map)

        object_series = fetch_object_series(conn, args.period_type)
        for key, values in object_series.items():
            repo_id, metric_id, subfield = key
            periods = sorted(values.keys())
            feature_map = derive_features_for_series(periods, values, windows)
            total_rows += write_features(
                conn,
                (repo_id, metric_id),
                args.period_type,
                feature_map,
                feature_prefix=f"{subfield}_",
            )

        add_raw_interp_ratio(conn, args.period_type, windows)
        print(f"Derived feature rows: {total_rows}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
