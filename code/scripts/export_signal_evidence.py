#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Dict, List

import yaml


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export signal evidence report")
    parser.add_argument("--sources", required=True, help="Path to sources.yaml")
    parser.add_argument("--db", default=None, help="Override sqlite db path")
    parser.add_argument("--output", default="docs/signal_report.md", help="Markdown output")
    parser.add_argument("--json-output", default="docs/signal_report.json", help="JSON output")
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


def load_metric_files(conn: sqlite3.Connection) -> Dict[int, str]:
    return {row["id"]: row["file"] for row in conn.execute("SELECT id, file FROM metrics")}


def main() -> None:
    args = parse_args()
    db_path = get_sqlite_path(Path(args.sources), args.db)
    conn = connect(db_path)

    try:
        configured = set(configured_repo_names(Path(args.sources)))
        metric_files = load_metric_files(conn)
        repo_map = {
            row["id"]: row["full_name"]
            for row in conn.execute("SELECT id, full_name FROM repos")
            if not configured or row["full_name"] in configured
        }
        events = conn.execute(
            """
            SELECT id, repo_id, signal_id, metric_id, start_month, end_month, confidence, severity, evidence_ref
            FROM signal_events
            ORDER BY repo_id, signal_id, start_month
            """
        ).fetchall()

        report_items = []
        for row in events:
            repo_name = repo_map.get(row["repo_id"])
            if not repo_name:
                continue
            evidence = json.loads(row["evidence_ref"])
            start_month = row["start_month"]
            end_month = row["end_month"]
            duration = None
            if isinstance(start_month, str) and isinstance(end_month, str) and len(start_month) == 7 and len(end_month) == 7:
                sy, sm = start_month.split("-", 1)
                ey, em = end_month.split("-", 1)
                duration = (int(ey) * 12 + int(em)) - (int(sy) * 12 + int(sm)) + 1
            severity = float(row["severity"] or 0.0)
            report_items.append(
                {
                    "repo": repo_name,
                    "signal_id": row["signal_id"],
                    "metric": evidence.get("metric"),
                    "metric_file": metric_files.get(row["metric_id"], ""),
                    "dimension": evidence.get("dimension"),
                    "signal_name": evidence.get("signal_name"),
                    "signal_severity": evidence.get("signal_severity"),
                    "signal_weight": evidence.get("signal_weight"),
                    "signal_window": evidence.get("signal_window"),
                    "signal_consistency": evidence.get("signal_consistency"),
                    "signal_confidence_cfg": evidence.get("signal_confidence"),
                    "signal_evidence_fields": evidence.get("signal_evidence_fields"),
                    "signal_strength": max(0.0, min(1.0, severity / 100.0)),
                    "signal_confidence": float(row["confidence"] or 0.0),
                    "when": {"start_month": start_month, "end_month": end_month, "duration_months": duration},
                    "time_window": {"t0": start_month, "t_end": end_month, "sustained_months": duration},
                    "months": evidence.get("months", []),
                    "features": evidence.get("features", {}),
                    "raw_ratio": evidence.get("raw_ratio"),
                    "interp_ratio": evidence.get("interp_ratio"),
                    "confidence_tier": evidence.get("confidence_tier"),
                    "severity": severity,
                    "confidence": float(row["confidence"] or 0.0),
                    "summary_template": evidence.get("summary_template"),
                    "triggered_signals": evidence.get("triggered_signals"),
                }
            )

        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with output_path.open("w", encoding="utf-8") as f:
            f.write("# Signal Evidence Report\n\n")
            for item in report_items:
                f.write(f"## {item['repo']} / {item['signal_id']}\n\n")
                if item["metric"]:
                    f.write(f"- metric: `{item['metric']}` ({item['metric_file']})\n")
                if item["signal_name"]:
                    f.write(f"- signal_name: {item['signal_name']}\n")
                if item["signal_severity"]:
                    f.write(f"- severity_level: {item['signal_severity']}\n")
                if item["signal_weight"] is not None:
                    f.write(f"- weight: {item['signal_weight']}\n")
                if item["signal_window"]:
                    f.write(f"- window: {item['signal_window']}\n")
                if item["signal_consistency"]:
                    f.write(f"- consistency: {item['signal_consistency']}\n")
                if item["signal_confidence_cfg"]:
                    f.write(f"- confidence_cfg: {item['signal_confidence_cfg']}\n")
                if item["signal_evidence_fields"]:
                    f.write(f"- evidence_fields: {item['signal_evidence_fields']}\n")
                f.write(f"- severity_score: {item['severity']:.2f}\n")
                f.write(f"- confidence: {item['confidence']:.2f}\n")
                if item["raw_ratio"] is not None:
                    f.write(f"- raw_ratio: {item['raw_ratio']:.2%}\n")
                if item["interp_ratio"] is not None:
                    f.write(f"- interp_ratio: {item['interp_ratio']:.2%}\n")
                if item["confidence_tier"]:
                    f.write(f"- confidence_tier: {item['confidence_tier']}\n")
                f.write(f"- months: {', '.join(item['months'])}\n")
                if item["summary_template"]:
                    f.write(f"- summary: {item['summary_template']}\n")
                if item["triggered_signals"]:
                    f.write("- triggered_signals:\n")
                    for sid, months in item["triggered_signals"].items():
                        f.write(f"  - {sid}: {', '.join(months)}\n")
                if item["features"]:
                    f.write("- features:\n")
                    for key, values in item["features"].items():
                        cleaned = ["NA" if v is None else f"{v:.4f}" for v in values]
                        f.write(f"  - {key}: {', '.join(cleaned)}\n")
                f.write("\n")

        json_path = Path(args.json_output)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        with json_path.open("w", encoding="utf-8") as f:
            json.dump(report_items, f, ensure_ascii=True, indent=2)

    finally:
        conn.close()


if __name__ == "__main__":
    main()
