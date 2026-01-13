from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List

from .storage_manager import IoTDBConfig, IoTDBManager


@dataclass
class QueryResult:
    columns: List[str]
    rows: List[List[object]]


def execute_query(manager: IoTDBManager, sql: str) -> QueryResult:
    dataset = manager.session.execute_query_statement(sql)
    columns = list(dataset.get_column_names())
    rows: List[List[object]] = []
    while dataset.has_next():
        record = dataset.next()
        fields = record.get_fields()
        row = [record.get_timestamp()] + [f.get_object_value() for f in fields]
        rows.append(row)
    manager.session.close_operation_handle(dataset.operation_handle)
    return QueryResult(columns=columns, rows=rows)


def export_csv(result: QueryResult, path: str) -> None:
    import csv

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(result.columns)
        writer.writerows(result.rows)


def aligned_snapshot_sql(root: str, measurements: Iterable[str], time_iso: str) -> str:
    meas = ", ".join(measurements)
    return (
        f"SELECT {meas} FROM {root}.** WHERE time = {time_iso} ALIGN BY DEVICE"
    )


def aligned_range_sql(root: str, measurements: Iterable[str], start_iso: str, end_iso: str) -> str:
    meas = ", ".join(measurements)
    return (
        f"SELECT {meas} FROM {root}.** WHERE time >= {start_iso} AND time < {end_iso} "
        "ALIGN BY DEVICE"
    )


def group_by_sql(device: str, measurements: Iterable[str], start_iso: str, end_iso: str, interval: str) -> str:
    meas = ", ".join([f"AVG({m})" for m in measurements])
    return (
        f"SELECT {meas} FROM {device} "
        f"GROUP BY ([{start_iso}, {end_iso}), {interval})"
    )


def fill_sql(device: str, measurements: Iterable[str], start_iso: str, end_iso: str, fill_type: str) -> str:
    meas = ", ".join(measurements)
    return (
        f"SELECT {meas} FROM {device} WHERE time >= {start_iso} AND time < {end_iso} "
        f"FILL({fill_type})"
    )
