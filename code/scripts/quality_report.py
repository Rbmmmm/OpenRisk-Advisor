#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import sqlite3
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.ingestion.utils import detect_period_key  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="OpenDigger data quality report")
    parser.add_argument("--sources", required=True, help="Path to sources.yaml")
    parser.add_argument("--metrics", required=True, help="Path to metrics.yaml")
    parser.add_argument(
        "--db",
        default=None,
        help="Override sqlite db path (default from sources.yaml)",
    )
    parser.add_argument(
        "--output",
        default="docs/data_quality_report.md",
        help="Markdown report output path",
    )
    parser.add_argument(
        "--json-output",
        default="docs/data_quality_report.json",
        help="JSON report output path",
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


def fetch_latest_fetch_status(conn: sqlite3.Connection) -> Dict[str, int]:
    query = """
        SELECT status, COUNT(*) as cnt
        FROM (
            SELECT rf.repo_id, rf.metric_id, rf.status,
                   MAX(rf.fetched_at) AS fetched_at
            FROM raw_files rf
            GROUP BY rf.repo_id, rf.metric_id
        ) latest
        GROUP BY status
    """
    results = {}
    for row in conn.execute(query):
        results[row["status"]] = row["cnt"]
    return results


def coverage_stats(conn: sqlite3.Connection) -> Tuple[int, int, int]:
    repo_count = conn.execute("SELECT COUNT(*) FROM repos").fetchone()[0]
    metric_count = conn.execute("SELECT COUNT(*) FROM metrics").fetchone()[0]
    combos = repo_count * metric_count
    return repo_count, metric_count, combos


def repo_metric_parse_flags(conn: sqlite3.Connection) -> Dict[Tuple[int, int], str]:
    query = """
        SELECT repo_id, metric_id,
               SUM(CASE WHEN is_raw = 0 THEN 1 ELSE 0 END) AS normal_cnt,
               SUM(CASE WHEN is_raw = 1 THEN 1 ELSE 0 END) AS raw_cnt
        FROM time_series
        GROUP BY repo_id, metric_id
    """
    object_query = """
        SELECT repo_id, metric_id,
               SUM(CASE WHEN is_raw = 0 THEN 1 ELSE 0 END) AS normal_cnt,
               SUM(CASE WHEN is_raw = 1 THEN 1 ELSE 0 END) AS raw_cnt
        FROM time_series_object
        GROUP BY repo_id, metric_id
    """
    flags: Dict[Tuple[int, int], str] = {}
    for row in conn.execute(query):
        key = (row["repo_id"], row["metric_id"])
        if row["normal_cnt"] > 0:
            flags[key] = "parsed_ok"
        elif row["raw_cnt"] > 0:
            flags[key] = "raw_only"
    for row in conn.execute(object_query):
        key = (row["repo_id"], row["metric_id"])
        if row["normal_cnt"] > 0:
            flags[key] = "parsed_ok"
        elif row["raw_cnt"] > 0 and key not in flags:
            flags[key] = "raw_only"
    return flags


def build_parse_summary(conn: sqlite3.Connection) -> Dict[str, int]:
    repo_ids = [r[0] for r in conn.execute("SELECT id FROM repos").fetchall()]
    metric_ids = [m[0] for m in conn.execute("SELECT id FROM metrics").fetchall()]
    flags = repo_metric_parse_flags(conn)
    counts = {"parsed_ok": 0, "raw_only": 0, "parse_error": 0}
    for repo_id in repo_ids:
        for metric_id in metric_ids:
            status = flags.get((repo_id, metric_id), "parse_error")
            counts[status] += 1
    return counts


def time_span_stats(conn: sqlite3.Connection) -> List[dict]:
    query = """
        SELECT m.name as metric_name,
               ts.period_type,
               MIN(ts.period) as min_period,
               MAX(ts.period) as max_period,
               COUNT(DISTINCT ts.period) as period_count
        FROM time_series ts
        JOIN metrics m ON m.id = ts.metric_id
        WHERE ts.is_raw = 0
        GROUP BY m.name, ts.period_type
        ORDER BY m.name, ts.period_type
    """
    return [dict(row) for row in conn.execute(query)]


def period_count_distribution(conn: sqlite3.Connection) -> List[dict]:
    query = """
        SELECT m.name as metric_name,
               ts.metric_id,
               ts.repo_id,
               COUNT(DISTINCT ts.period) as period_count
        FROM time_series ts
        JOIN metrics m ON m.id = ts.metric_id
        WHERE ts.is_raw = 0
        GROUP BY ts.metric_id, ts.repo_id
    """
    by_metric: Dict[int, List[int]] = {}
    names: Dict[int, str] = {}
    for row in conn.execute(query):
        metric_id = row["metric_id"]
        by_metric.setdefault(metric_id, []).append(row["period_count"])
        names[metric_id] = row["metric_name"]

    dist = []
    for metric_id, counts in by_metric.items():
        counts.sort()
        dist.append(
            {
                "metric_name": names[metric_id],
                "min": counts[0],
                "max": counts[-1],
                "median": counts[len(counts) // 2],
                "repo_count": len(counts),
            }
        )
    return dist


def missing_rate_by_metric(conn: sqlite3.Connection) -> List[dict]:
    repo_count = conn.execute("SELECT COUNT(*) FROM repos").fetchone()[0]
    metric_rows = conn.execute("SELECT id, name FROM metrics").fetchall()

    results = []
    for metric in metric_rows:
        metric_id = metric["id"]
        name = metric["name"]
        period_counts = conn.execute(
            """
            SELECT repo_id, COUNT(DISTINCT period) as cnt
            FROM time_series
            WHERE metric_id = ? AND is_raw = 0
            GROUP BY repo_id
            """,
            (metric_id,),
        ).fetchall()
        counts = [row["cnt"] for row in period_counts]
        max_cnt = max(counts) if counts else 0
        missing_full = repo_count - len(counts)
        missing_partial = 0
        for cnt in counts:
            if max_cnt > 0 and cnt < max_cnt:
                missing_partial += 1
        results.append(
            {
                "metric_name": name,
                "repo_total": repo_count,
                "missing_full": missing_full,
                "missing_partial": missing_partial,
                "missing_full_ratio": (missing_full / repo_count) if repo_count else 0,
                "missing_partial_ratio": (missing_partial / repo_count) if repo_count else 0,
                "max_periods": max_cnt,
            }
        )
    return results


def percentile(values: List[float], q: float) -> float:
    if not values:
        return math.nan
    values = sorted(values)
    k = (len(values) - 1) * q
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return values[int(k)]
    d0 = values[int(f)] * (c - k)
    d1 = values[int(c)] * (k - f)
    return d0 + d1


def raw_value_anomalies(conn: sqlite3.Connection) -> Dict[str, Dict[str, int]]:
    query = """
        SELECT m.name as metric_name, rj.json_text
        FROM raw_json rj
        JOIN metrics m ON m.id = rj.metric_id
    """
    stats: Dict[str, Dict[str, int]] = {}
    for row in conn.execute(query):
        name = row["metric_name"]
        stats.setdefault(name, {"nulls": 0, "non_numeric": 0})
        try:
            payload = json.loads(row["json_text"])
        except json.JSONDecodeError:
            stats[name]["non_numeric"] += 1
            continue
        if not isinstance(payload, dict):
            continue
        for key, value in payload.items():
            if detect_period_key(str(key)) is None:
                continue
            if value is None:
                stats[name]["nulls"] += 1
                continue
            if isinstance(value, bool):
                stats[name]["non_numeric"] += 1
                continue
            if not isinstance(value, (int, float)):
                stats[name]["non_numeric"] += 1
    return stats


def anomaly_overview(conn: sqlite3.Connection) -> List[dict]:
    query = """
        SELECT m.name as metric_name, ts.value
        FROM time_series ts
        JOIN metrics m ON m.id = ts.metric_id
        WHERE ts.is_raw = 0
    """
    values_by_metric: Dict[str, List[float]] = {}
    negatives: Dict[str, int] = {}

    for row in conn.execute(query):
        name = row["metric_name"]
        value = row["value"]
        values_by_metric.setdefault(name, []).append(value)
        if value < 0:
            negatives[name] = negatives.get(name, 0) + 1

    raw_anomalies = raw_value_anomalies(conn)
    results = []
    for name, values in values_by_metric.items():
        p01 = percentile(values, 0.01)
        p50 = percentile(values, 0.50)
        p99 = percentile(values, 0.99)
        raw_stats = raw_anomalies.get(name, {"nulls": 0, "non_numeric": 0})
        results.append(
            {
                "metric_name": name,
                "count": len(values),
                "negatives": negatives.get(name, 0),
                "nulls": raw_stats["nulls"],
                "non_numeric": raw_stats["non_numeric"],
                "p01": p01,
                "p50": p50,
                "p99": p99,
            }
        )
    return results


def fetch_health_by_repo(conn: sqlite3.Connection) -> List[dict]:
    query = """
        SELECT r.full_name as repo,
               SUM(CASE WHEN rf.http_status = 200 THEN 1 ELSE 0 END) AS ok_cnt,
               SUM(CASE WHEN rf.http_status = 404 THEN 1 ELSE 0 END) AS not_found_cnt,
               SUM(CASE WHEN rf.error_type IN ('timeout','connection') THEN 1 ELSE 0 END) AS network_fail_cnt,
               COUNT(*) as total_cnt,
               MAX(rf.fetched_at) as last_fetched_at
        FROM (
            SELECT repo_id, metric_id, MAX(fetched_at) as fetched_at
            FROM raw_files
            GROUP BY repo_id, metric_id
        ) latest
        JOIN raw_files rf
          ON rf.repo_id = latest.repo_id
         AND rf.metric_id = latest.metric_id
         AND rf.fetched_at = latest.fetched_at
        JOIN repos r ON r.id = rf.repo_id
        GROUP BY r.full_name
        ORDER BY r.full_name
    """
    results = []
    for row in conn.execute(query):
        total = row["total_cnt"] or 0
        ok = row["ok_cnt"] or 0
        nf = row["not_found_cnt"] or 0
        net = row["network_fail_cnt"] or 0
        results.append(
            {
                "repo": row["repo"],
                "ok_cnt": ok,
                "not_found_cnt": nf,
                "network_fail_cnt": net,
                "total_cnt": total,
                "ok_rate": (ok / total) if total else 0,
                "not_found_rate": (nf / total) if total else 0,
                "network_fail_rate": (net / total) if total else 0,
                "last_fetched_at": row["last_fetched_at"],
            }
        )
    return results


def most_missing_metrics(conn: sqlite3.Connection, limit: int = 10) -> List[dict]:
    query = """
        SELECT m.name as metric_name, COUNT(*) as not_found_cnt
        FROM (
            SELECT repo_id, metric_id, MAX(fetched_at) as fetched_at
            FROM raw_files
            GROUP BY repo_id, metric_id
        ) latest
        JOIN raw_files rf
          ON rf.repo_id = latest.repo_id
         AND rf.metric_id = latest.metric_id
         AND rf.fetched_at = latest.fetched_at
        JOIN metrics m ON m.id = rf.metric_id
        WHERE rf.http_status = 404
        GROUP BY m.name
        ORDER BY not_found_cnt DESC
        LIMIT ?
    """
    return [dict(row) for row in conn.execute(query, (limit,))]


def format_table(headers: List[str], rows: Iterable[Iterable[object]]) -> str:
    header_row = "| " + " | ".join(headers) + " |"
    sep_row = "| " + " | ".join(["---"] * len(headers)) + " |"
    lines = [header_row, sep_row]
    for row in rows:
        lines.append("| " + " | ".join(str(x) for x in row) + " |")
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    sources_path = Path(args.sources)
    metrics_path = Path(args.metrics)
    db_path = get_sqlite_path(sources_path, args.db)

    conn = connect(db_path)

    repo_count, metric_count, combos = coverage_stats(conn)
    fetch_status = fetch_latest_fetch_status(conn)
    parse_summary = build_parse_summary(conn)
    time_spans = time_span_stats(conn)
    period_dist = period_count_distribution(conn)
    missing_rates = missing_rate_by_metric(conn)
    anomalies = anomaly_overview(conn)
    fetch_health = fetch_health_by_repo(conn)
    missing_metrics = most_missing_metrics(conn)

    timestamp = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    terminal_lines = []
    terminal_lines.append("=== OpenDigger Data Quality Summary ===")
    terminal_lines.append(f"Generated at: {timestamp}")
    terminal_lines.append(f"Repos: {repo_count}  Metrics: {metric_count}  Combos: {combos}")
    terminal_lines.append(f"Fetch status: {fetch_status}")
    terminal_lines.append(f"Parse summary: {parse_summary}")
    terminal_lines.append(f"DB: {db_path}")
    print("\n".join(terminal_lines))

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    json_output_path = Path(args.json_output)
    json_output_path.parent.mkdir(parents=True, exist_ok=True)

    json_payload = {
        "generated_at": timestamp,
        "sources": str(sources_path),
        "metrics": str(metrics_path),
        "db": str(db_path),
        "coverage": {
            "repo_count": repo_count,
            "metric_count": metric_count,
            "combos": combos,
        },
        "fetch_status": fetch_status,
        "parse_summary": parse_summary,
        "fetch_health": fetch_health,
        "missing_metrics": missing_metrics,
    }

    with json_output_path.open("w", encoding="utf-8") as f:
        json.dump(json_payload, f, ensure_ascii=False, indent=2)

    with output_path.open("w", encoding="utf-8") as f:
        f.write("# OpenDigger 数据质量报告\n\n")
        f.write(f"生成时间：{timestamp}\n\n")
        f.write(f"数据源配置：`{sources_path}`\n\n")
        f.write(f"指标配置：`{metrics_path}`\n\n")
        f.write(f"SQLite：`{db_path}`\n\n")

        f.write("## 覆盖情况\n\n")
        f.write(
            format_table(
                ["repo 数", "metric 数", "repo×metric 组合数"],
                [[repo_count, metric_count, combos]],
            )
        )
        f.write("\n\n")

        f.write("## 抓取情况（按状态分组）\n\n")
        status_rows = [[status, count] for status, count in sorted(fetch_status.items())]
        f.write(format_table(["状态", "数量"], status_rows))
        f.write("\n\n")

        f.write("## 解析情况\n\n")
        f.write(
            format_table(
                ["parsed_ok", "raw_only", "parse_error"],
                [[
                    parse_summary["parsed_ok"],
                    parse_summary["raw_only"],
                    parse_summary["parse_error"],
                ]],
            )
        )
        f.write("\n\n")

        f.write("## 每个仓库抓取健康度\n\n")
        f.write(
            format_table(
                ["repo", "ok", "404", "network_fail", "ok_rate", "404_rate", "network_fail_rate"],
                [
                    [
                        row["repo"],
                        row["ok_cnt"],
                        row["not_found_cnt"],
                        row["network_fail_cnt"],
                        f"{row['ok_rate']:.2%}",
                        f"{row['not_found_rate']:.2%}",
                        f"{row['network_fail_rate']:.2%}",
                    ]
                    for row in fetch_health
                ],
            )
        )
        f.write("\n\n")

        f.write("## 上游不存在最多的指标（404 Top）\n\n")
        f.write(
            format_table(
                ["metric", "404_count"],
                [[row["metric_name"], row["not_found_cnt"]] for row in missing_metrics],
            )
        )
        f.write("\n\n")

        f.write("## 时间跨度（按 metric 与 period_type）\n\n")
        f.write(
            format_table(
                ["metric", "period_type", "min", "max", "period_count"],
                [
                    [
                        row["metric_name"],
                        row["period_type"],
                        row["min_period"],
                        row["max_period"],
                        row["period_count"],
                    ]
                    for row in time_spans
                ],
            )
        )
        f.write("\n\n")

        f.write("## period 数分布（按 metric）\n\n")
        f.write(
            format_table(
                ["metric", "repo_count", "min", "median", "max"],
                [
                    [
                        row["metric_name"],
                        row["repo_count"],
                        row["min"],
                        row["median"],
                        row["max"],
                    ]
                    for row in period_dist
                ],
            )
        )
        f.write("\n\n")

        f.write("## 缺失率（按 metric）\n\n")
        f.write(
            format_table(
                [
                    "metric",
                    "repo_total",
                    "missing_full",
                    "missing_partial",
                    "missing_full_ratio",
                    "missing_partial_ratio",
                    "max_periods",
                ],
                [
                    [
                        row["metric_name"],
                        row["repo_total"],
                        row["missing_full"],
                        row["missing_partial"],
                        f"{row['missing_full_ratio']:.2%}",
                        f"{row['missing_partial_ratio']:.2%}",
                        row["max_periods"],
                    ]
                    for row in missing_rates
                ],
            )
        )
        f.write("\n\n")

        f.write("## 异常值概览（按 metric）\n\n")
        f.write(
            format_table(
                ["metric", "count", "negatives", "nulls", "non_numeric", "p01", "p50", "p99"],
                [
                    [
                        row["metric_name"],
                        row["count"],
                        row["negatives"],
                        row["nulls"],
                        row["non_numeric"],
                        f"{row['p01']:.4f}" if not math.isnan(row["p01"]) else "NaN",
                        f"{row['p50']:.4f}" if not math.isnan(row["p50"]) else "NaN",
                        f"{row['p99']:.4f}" if not math.isnan(row["p99"]) else "NaN",
                    ]
                    for row in anomalies
                ],
            )
        )
        f.write("\n")

    conn.close()


if __name__ == "__main__":
    main()
