from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from .storage import Storage
from .utils import detect_period_key, json_sha256

logger = logging.getLogger(__name__)


def load_json(path: Path) -> Optional[object]:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as exc:
        logger.warning("invalid json %s: %s", path, exc)
        return None


def parse_metric_file(
    storage: Storage,
    repo_id: int,
    metric_id: int,
    path: Path,
) -> dict:
    payload = load_json(path)
    if payload is None:
        return {"status": "invalid_json", "time_keys": 0, "rows": 0}

    json_hash = json_sha256(payload)

    if not isinstance(payload, dict):
        storage.record_raw_json(
            repo_id=repo_id,
            metric_id=metric_id,
            json_text=json.dumps(payload, ensure_ascii=True),
            json_hash=json_hash,
            parse_status="non_dict",
            time_keys_count=0,
        )
        return {"status": "non_dict", "time_keys": 0, "rows": 0}

    rows = []
    object_rows = []
    time_keys = 0
    for key, value in payload.items():
        period_key = detect_period_key(key)
        if period_key is None:
            continue
        time_keys += 1
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            rows.append(
                (
                    repo_id,
                    metric_id,
                    period_key.period,
                    period_key.period_type,
                    float(value),
                    1 if period_key.is_raw else 0,
                    period_key.source_key,
                )
            )
        else:
            object_rows.append(
                (
                    repo_id,
                    metric_id,
                    period_key.period,
                    period_key.period_type,
                    json.dumps(value, ensure_ascii=True),
                    1 if period_key.is_raw else 0,
                    period_key.source_key,
                )
            )

    nested_time_keys = 0
    if time_keys == 0:
        nested_time_keys, nested_object_rows = _parse_nested_time_series(
            repo_id, metric_id, payload
        )
        if nested_time_keys > 0:
            object_rows.extend(nested_object_rows)

    if time_keys > 0:
        parse_status = "time_series"
    elif nested_time_keys > 0:
        parse_status = "time_series_object"
    else:
        parse_status = "no_time_keys"
    storage.record_raw_json(
        repo_id=repo_id,
        metric_id=metric_id,
        json_text=json.dumps(payload, ensure_ascii=True, sort_keys=True),
        json_hash=json_hash,
        parse_status=parse_status,
        time_keys_count=time_keys or nested_time_keys,
    )

    inserted = 0
    if rows:
        inserted = storage.upsert_time_series_rows(rows)
    if object_rows:
        storage.upsert_time_series_object_rows(object_rows)

    return {"status": parse_status, "time_keys": time_keys or nested_time_keys, "rows": inserted}


def _parse_nested_time_series(
    repo_id: int,
    metric_id: int,
    payload: dict,
) -> tuple[int, list]:
    if not isinstance(payload, dict):
        return 0, []

    per_period: dict = {}
    time_keys = 0
    for sub_key, sub_value in payload.items():
        if not isinstance(sub_value, dict):
            continue
        for time_key, value in sub_value.items():
            period_key = detect_period_key(str(time_key))
            if period_key is None:
                continue
            time_keys += 1
            entry = per_period.setdefault(
                (period_key.period, period_key.period_type, period_key.is_raw, period_key.source_key),
                {},
            )
            entry[sub_key] = value

    rows = []
    for (period, period_type, is_raw, source_key), obj in per_period.items():
        rows.append(
            (
                repo_id,
                metric_id,
                period,
                period_type,
                json.dumps(obj, ensure_ascii=True),
                1 if is_raw else 0,
                source_key,
            )
        )
    return time_keys, rows
