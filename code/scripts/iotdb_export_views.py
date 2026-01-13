#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.iotdb.storage_manager import IoTDBManager, load_config
from services.iotdb.query_manager import (
    aligned_range_sql,
    aligned_snapshot_sql,
    execute_query,
    export_csv,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export IoTDB views for DataEase/SQLBot")
    parser.add_argument("--iotdb", required=True, help="Path to iotdb.yaml")
    parser.add_argument("--root", default="root.openrisk.github", help="Root path")
    parser.add_argument("--start", required=True, help="Start time ISO, e.g. 2024-01-01T00:00:00")
    parser.add_argument("--end", required=True, help="End time ISO, e.g. 2025-01-01T00:00:00")
    parser.add_argument("--snapshot", required=True, help="Snapshot time ISO for wide view")
    parser.add_argument("--measurements", required=True, help="Comma-separated measurements")
    parser.add_argument("--output-dir", default="data/exports", help="Output directory")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    measurements: List[str] = [m.strip() for m in args.measurements.split(",") if m.strip()]
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    cfg = load_config(args.iotdb)
    manager = IoTDBManager(cfg)
    manager.open()
    try:
        # Long view: aligned by device over range
        sql_long = aligned_range_sql(args.root, measurements, args.start, args.end)
        result_long = execute_query(manager, sql_long)
        export_csv(result_long, str(output_dir / "iotdb_long.csv"))

        # Wide view: snapshot per device
        sql_wide = aligned_snapshot_sql(args.root, measurements, args.snapshot)
        result_wide = execute_query(manager, sql_wide)
        export_csv(result_wide, str(output_dir / "iotdb_wide.csv"))
    finally:
        manager.close()


if __name__ == "__main__":
    main()
