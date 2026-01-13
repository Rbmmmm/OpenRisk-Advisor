#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Dict, List

import yaml


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Probe JSON structures for no_time_keys")
    parser.add_argument("--sources", required=True, help="Path to sources.yaml")
    parser.add_argument("--db", default=None, help="Override sqlite db path")
    parser.add_argument("--limit", type=int, default=5, help="Samples per metric")
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


def describe_payload(payload: object) -> str:
    if isinstance(payload, dict):
        keys = list(payload.keys())
        return f"dict keys={keys[:10]}"
    if isinstance(payload, list):
        if not payload:
            return "list empty"
        first = payload[0]
        if isinstance(first, dict):
            return f"list[dict] keys={list(first.keys())[:10]}"
        return f"list[{type(first).__name__}]"
    return type(payload).__name__


def main() -> None:
    args = parse_args()
    db_path = get_sqlite_path(Path(args.sources), args.db)
    conn = connect(db_path)

    query = """
        SELECT m.name as metric_name, r.full_name as repo, rj.json_text
        FROM raw_json rj
        JOIN metrics m ON m.id = rj.metric_id
        JOIN repos r ON r.id = rj.repo_id
        WHERE rj.parse_status = 'no_time_keys'
        ORDER BY m.name, r.full_name
    """

    samples: Dict[str, List[str]] = {}
    for row in conn.execute(query):
        name = row["metric_name"]
        if len(samples.get(name, [])) >= args.limit:
            continue
        try:
            payload = json.loads(row["json_text"])
        except json.JSONDecodeError:
            desc = "invalid_json"
        else:
            desc = describe_payload(payload)
        samples.setdefault(name, []).append(f"{row['repo']}: {desc}")

    for metric, items in samples.items():
        print(f"== {metric} ==")
        for item in items:
            print(f"  - {item}")

    conn.close()


if __name__ == "__main__":
    main()
