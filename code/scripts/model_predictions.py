#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Optional

import yaml


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Model prediction snapshot")
    p.add_argument("--sources", required=True, help="Path to sources.yaml")
    p.add_argument("--model-type", default="baseline", choices=["baseline", "transformer"])
    p.add_argument("--db", default=None, help="Override sqlite db path")
    return p.parse_args()


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def get_sqlite_path(sources_path: Path, override: Optional[str]) -> Path:
    if override:
        return Path(override)
    sources = load_yaml(sources_path)
    defaults = sources.get("defaults") or {}
    return Path(defaults.get("sqlite_path", "data/sqlite/opendigger.db"))


def connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def latest_model_version(conn: sqlite3.Connection, model_type: str) -> Optional[str]:
    try:
        row = conn.execute(
            "SELECT model_version FROM ml_models WHERE model_type=? ORDER BY created_at DESC LIMIT 1",
            (model_type,),
        ).fetchone()
        if row and row[0]:
            return str(row[0])
    except sqlite3.OperationalError:
        return None
    return None


def latest_prediction_version(conn: sqlite3.Connection, model_type: str) -> Optional[str]:
    row = conn.execute(
        "SELECT model_version FROM risk_predictions WHERE model_type=? ORDER BY created_at DESC LIMIT 1",
        (model_type,),
    ).fetchone()
    if row and row[0]:
        return str(row[0])
    return None


def main() -> None:
    args = parse_args()
    sources_path = Path(args.sources)
    db_path = get_sqlite_path(sources_path, args.db)
    conn = connect(db_path)
    try:
        model_version = latest_model_version(conn, args.model_type)
        if model_version is None:
            model_version = latest_prediction_version(conn, args.model_type)
        if model_version is None:
            print(json.dumps({"ok": False, "error": "no_model"}))
            return

        row = conn.execute(
            "SELECT MAX(as_of_month) FROM risk_predictions WHERE model_type=? AND model_version=?",
            (args.model_type, model_version),
        ).fetchone()
        as_of_month = row[0] if row and row[0] else None

        items = []
        if as_of_month:
            rows = conn.execute(
                """
                SELECT r.full_name AS repo, rp.as_of_month, rp.p_calibrated, rp.p_raw,
                       rp.risk_level, rp.needs_review
                FROM risk_predictions rp
                JOIN repos r ON r.id = rp.repo_id
                WHERE rp.model_type=? AND rp.model_version=? AND rp.as_of_month=?
                ORDER BY rp.p_calibrated DESC
                """,
                (args.model_type, model_version, as_of_month),
            ).fetchall()
            for r in rows:
                items.append(
                    {
                        "repo": r["repo"],
                        "as_of_month": r["as_of_month"],
                        "p_calibrated": r["p_calibrated"],
                        "p_raw": r["p_raw"],
                        "risk_level": r["risk_level"],
                        "needs_review": bool(r["needs_review"]),
                    }
                )

        print(
            json.dumps(
                {
                    "ok": True,
                    "model_type": args.model_type,
                    "model_version": model_version,
                    "as_of_month": as_of_month,
                    "items": items,
                },
                ensure_ascii=False,
            )
        )
    finally:
        conn.close()


if __name__ == "__main__":
    main()
