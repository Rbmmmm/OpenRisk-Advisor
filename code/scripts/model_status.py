#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Dict, Optional

import yaml


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Model status summary")
    p.add_argument("--sources", required=True, help="Path to sources.yaml")
    p.add_argument("--model", default="configs/model.yaml", help="Path to model.yaml")
    p.add_argument("--db", default=None, help="Override sqlite db path")
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


def latest_model(conn: sqlite3.Connection, model_type: str) -> Optional[dict]:
    row = conn.execute(
        """
        SELECT model_type, model_version, created_at, train_samples, val_samples, artifact_path, extra_json
        FROM ml_models
        WHERE model_type=?
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (model_type,),
    ).fetchone()
    if not row:
        return None
    out = dict(row)
    try:
        out["extra_json"] = json.loads(out.get("extra_json") or "{}")
    except json.JSONDecodeError:
        out["extra_json"] = {}
    return out


def prediction_stats(conn: sqlite3.Connection, model_type: str, model_version: str) -> dict:
    row = conn.execute(
        """
        SELECT COUNT(*) AS cnt, MAX(as_of_month) AS latest_month
        FROM risk_predictions
        WHERE model_type=? AND model_version=?
        """,
        (model_type, model_version),
    ).fetchone()
    return {
        "count": int(row["cnt"]) if row and row["cnt"] is not None else 0,
        "latest_month": row["latest_month"] if row and row["latest_month"] else None,
    }


def main() -> None:
    args = parse_args()
    sources_path = Path(args.sources)
    model_path = Path(args.model)
    db_path = get_sqlite_path(sources_path, args.db)

    model_cfg = load_yaml(model_path)
    config_summary: Dict[str, object] = {
        "version": model_cfg.get("version"),
        "task": model_cfg.get("task", {}),
        "forecast": model_cfg.get("forecast", {}),
        "inputs": model_cfg.get("inputs", {}),
        "labels": model_cfg.get("labels", {}),
        "calibration": model_cfg.get("calibration", {}),
        "thresholds": model_cfg.get("thresholds", {}),
        "models": model_cfg.get("models", {}),
    }

    conn = connect(db_path)
    out = {
        "db": str(db_path),
        "config": config_summary,
        "models": {},
    }
    try:
        for model_type in ("baseline", "transformer"):
            latest = None
            try:
                latest = latest_model(conn, model_type)
            except sqlite3.OperationalError:
                latest = None
            if latest and latest.get("model_version"):
                try:
                    preds = prediction_stats(conn, model_type, latest["model_version"])
                except sqlite3.OperationalError:
                    preds = {"count": 0, "latest_month": None}
            else:
                preds = {"count": 0, "latest_month": None}
            out["models"][model_type] = {
                "latest": latest,
                "predictions": preds,
            }
    finally:
        conn.close()

    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
