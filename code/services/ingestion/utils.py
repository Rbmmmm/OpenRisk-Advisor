from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


MONTH_RAW_RE = re.compile(r"^(\d{4}-\d{2})-raw$")
MONTH_RE = re.compile(r"^(\d{4}-\d{2})$")
QUARTER_RE = re.compile(r"^(\d{4}Q[1-4])$")
YEAR_RE = re.compile(r"^(\d{4})$")


@dataclass
class PeriodKey:
    period: str
    period_type: str
    is_raw: bool
    source_key: str


def detect_period_key(key: str) -> Optional[PeriodKey]:
    match = MONTH_RAW_RE.match(key)
    if match:
        return PeriodKey(period=match.group(1), period_type="month", is_raw=True, source_key=key)

    if MONTH_RE.match(key):
        return PeriodKey(period=key, period_type="month", is_raw=False, source_key=key)

    if QUARTER_RE.match(key):
        return PeriodKey(period=key, period_type="quarter", is_raw=False, source_key=key)

    if YEAR_RE.match(key):
        return PeriodKey(period=key, period_type="year", is_raw=False, source_key=key)

    return None


def file_sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def json_dumps_canonical(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def json_sha256(payload: Any) -> str:
    canonical = json_dumps_canonical(payload).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()
