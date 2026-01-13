#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Dict, List

import yaml


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Repo risk summary from signal events")
    parser.add_argument("--sources", required=True, help="Path to sources.yaml")
    parser.add_argument("--db", default=None, help="Override sqlite db path")
    parser.add_argument("--output", default="docs/repo_summary.md", help="Markdown output")
    parser.add_argument(
        "--lookback-months",
        type=int,
        default=6,
        help="Only aggregate signal events within the latest N months (per repo)",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=5,
        help="How many top signals to list per repo",
    )
    return parser.parse_args()


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def configured_repo_names(sources_path: Path) -> List[str]:
    data = load_yaml(sources_path)
    repos = data.get("repos") or []
    names: List[str] = []
    for r in repos:
        if not isinstance(r, dict):
            continue
        org = r.get("org")
        repo = r.get("repo")
        enabled = r.get("enabled", True)
        if not enabled:
            continue
        if isinstance(org, str) and isinstance(repo, str) and org and repo:
            names.append(f"{org}/{repo}")
    return names


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


def risk_level(score: float) -> str:
    if score >= 60:
        return "High"
    if score >= 30:
        return "Medium"
    return "Low"


def month_to_int(month: str) -> int:
    year, m = month.split("-", 1)
    return int(year) * 12 + int(m)


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
    start = month_to_int(latest_month) - (lookback_months - 1)
    return int_to_month(start)


def main() -> None:
    args = parse_args()
    sources_path = Path(args.sources)
    db_path = get_sqlite_path(sources_path, args.db)
    conn = connect(db_path)

    try:
        configured = set(configured_repo_names(sources_path))
        repo_map = {
            row["id"]: row["full_name"]
            for row in conn.execute("SELECT id, full_name FROM repos")
            if row["full_name"] in configured
        }
        rows = conn.execute(
            """
            SELECT repo_id, signal_id, severity, confidence, start_month, end_month
            FROM signal_events
            ORDER BY repo_id
            """
        ).fetchall()

        by_repo: Dict[int, List[sqlite3.Row]] = {}
        for row in rows:
            by_repo.setdefault(row["repo_id"], []).append(row)

        # Latest fetch status snapshot per repo (dedup by latest raw_files id per repo×metric).
        fetch_stats: Dict[int, Dict[str, int]] = {rid: {"ok": 0, "http_404": 0, "network_fail": 0, "other_fail": 0, "total": 0} for rid in repo_map}
        for row in conn.execute(
            """
            SELECT rf.repo_id, rf.status
            FROM raw_files rf
            JOIN (
              SELECT repo_id, metric_id, MAX(id) AS max_id
              FROM raw_files
              GROUP BY repo_id, metric_id
            ) x ON x.repo_id = rf.repo_id AND x.metric_id = rf.metric_id AND x.max_id = rf.id
            """
        ):
            repo_id = int(row["repo_id"])
            if repo_id not in fetch_stats:
                continue
            status = str(row["status"])
            fs = fetch_stats[repo_id]
            fs["total"] += 1
            if status == "ok":
                fs["ok"] += 1
            elif status.startswith("http_404"):
                fs["http_404"] += 1
            elif status in ("network_error", "timeout"):
                fs["network_fail"] += 1
            else:
                fs["other_fail"] += 1

        # Latest month can differ a lot across metrics. For governance signals, anchor the
        # lookback window on core metrics (activity/contributors/issues/PR), otherwise a
        # non-core metric (e.g. stars) can push as_of_month too far and hide valid signals.
        metric_id_by_name = {
            row["name"]: int(row["id"])
            for row in conn.execute("SELECT id, name FROM metrics")
        }
        core_metric_names = [
            "activity",
            "contributors",
            "issues_new",
            "issues_closed",
            "change_requests",
            "change_requests_accepted",
            "issue_age",
            "bus_factor",
        ]
        core_metric_ids = [metric_id_by_name[n] for n in core_metric_names if n in metric_id_by_name]

        latest_month_overall_by_repo: Dict[int, str] = {}
        for row in conn.execute(
            """
            SELECT repo_id, MAX(period) AS latest_month
            FROM time_series
            WHERE period_type='month' AND is_raw=0
            GROUP BY repo_id
            """
        ):
            rid = int(row["repo_id"])
            if rid in repo_map and row["latest_month"]:
                latest_month_overall_by_repo[rid] = str(row["latest_month"])

        latest_month_core_by_repo: Dict[int, str] = {}
        if core_metric_ids:
            placeholders = ",".join("?" for _ in core_metric_ids)
            query = f"""
            SELECT repo_id, MAX(period) AS latest_month
            FROM time_series
            WHERE period_type='month' AND is_raw=0 AND metric_id IN ({placeholders})
            GROUP BY repo_id
            """
            for row in conn.execute(query, core_metric_ids):
                rid = int(row["repo_id"])
                if rid in repo_map and row["latest_month"]:
                    latest_month_core_by_repo[rid] = str(row["latest_month"])

        # Core months count per repo (used for diagnosing why some repos have no signals).
        core_months_by_repo: Dict[int, int] = {rid: 0 for rid in repo_map}
        if core_metric_ids:
            placeholders = ",".join("?" for _ in core_metric_ids)
            q = f"""
            SELECT repo_id, COUNT(DISTINCT period) AS c
            FROM time_series
            WHERE period_type='month' AND is_raw=0 AND metric_id IN ({placeholders})
            GROUP BY repo_id
            """
            for row in conn.execute(q, core_metric_ids):
                rid = int(row["repo_id"])
                if rid in repo_map:
                    core_months_by_repo[rid] = int(row["c"] or 0)

        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with output_path.open("w", encoding="utf-8") as f:
            f.write("# Repo Risk Summary\n\n")
            # Always emit all repos from sources (even those with 0 signals),
            # so the report coverage matches the configured repo set.
            for repo_id in sorted(repo_map.keys(), key=lambda rid: repo_map[rid]):
                events = by_repo.get(repo_id, [])
                latest_month_overall = latest_month_overall_by_repo.get(repo_id)
                latest_month_core = latest_month_core_by_repo.get(repo_id)
                latest_month = latest_month_core or latest_month_overall
                if not latest_month and events:
                    latest_month = max(str(e["end_month"]) for e in events if e["end_month"])
                latest_month = latest_month or "1970-01"
                start_month = lookback_start(latest_month, args.lookback_months)

                per_signal_best: Dict[str, float] = {}
                per_signal_count: Dict[str, int] = {}
                total_events_in_window = 0

                for e in events:
                    end_m = str(e["end_month"])
                    if end_m < start_month or end_m > latest_month:
                        continue
                    total_events_in_window += 1
                    sid = str(e["signal_id"])
                    per_signal_count[sid] = per_signal_count.get(sid, 0) + 1
                    severity = float(e["severity"] or 0.0)
                    confidence = float(e["confidence"] or 0.0)
                    weighted = severity * (0.5 + 0.5 * confidence)
                    if weighted > per_signal_best.get(sid, 0.0):
                        per_signal_best[sid] = weighted

                total_score = min(100.0, sum(per_signal_best.values()))
                top_signals = [
                    sid for sid, _ in sorted(per_signal_best.items(), key=lambda x: x[1], reverse=True)
                ][: max(0, args.top_n)]

                f.write(f"## {repo_map.get(repo_id, repo_id)}\n\n")
                f.write(f"- risk_level: {risk_level(total_score)}\n")
                f.write(f"- risk_score: {total_score:.3f}\n")
                f.write(f"- as_of_month: {latest_month}\n")
                f.write(f"- as_of_month_core: {latest_month_core or 'N/A'}\n")
                f.write(f"- as_of_month_overall: {latest_month_overall or 'N/A'}\n")
                f.write(f"- lookback_months: {args.lookback_months}\n")
                f.write(f"- signals_triggered: {len(per_signal_best)}\n")
                f.write(f"- events_in_window: {total_events_in_window}\n")
                f.write(f"- core_months_total: {core_months_by_repo.get(repo_id, 0)}\n")
                fs = fetch_stats.get(repo_id) or {"ok": 0, "http_404": 0, "network_fail": 0, "other_fail": 0, "total": 0}
                total_fetch = fs["total"] or 1
                f.write(f"- fetch_ok: {fs['ok']} / {fs['total']} ({fs['ok']/total_fetch:.2%})\n")
                f.write(f"- fetch_404: {fs['http_404']} ({fs['http_404']/total_fetch:.2%})\n")
                f.write(f"- fetch_network_fail: {fs['network_fail']} ({fs['network_fail']/total_fetch:.2%})\n")
                if top_signals:
                    f.write("- top_signals: " + ", ".join(top_signals) + "\n")
                    f.write("- top_signals_event_counts:\n")
                    for sid in top_signals:
                        f.write(f"  - {sid}: {per_signal_count.get(sid, 0)}\n")
                    f.write("\n")
                else:
                    f.write("- top_signals: (none)\n\n")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
