from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Iterable, List, Sequence

import yaml

try:
    from iotdb.Session import Session
    from iotdb.utils.IoTDBConstants import TSDataType
except Exception:  # noqa: BLE001
    Session = None  # type: ignore
    TSDataType = None  # type: ignore


@dataclass
class IoTDBConfig:
    host: str
    port: int
    username: str
    password: str
    enable_rpc_compression: bool
    root: str
    github: str
    gitee: str
    device_prefix: str
    device_format: str
    raw_prefix: str
    feat_prefix: str
    use_aligned: bool
    batch_size: int


def load_config(path: str) -> IoTDBConfig:
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    conn = cfg.get("connection", {})
    db = cfg.get("database", {})
    mapping = cfg.get("mapping", {})
    write = cfg.get("write", {})
    return IoTDBConfig(
        host=conn.get("host", "127.0.0.1"),
        port=int(conn.get("port", 6667)),
        username=conn.get("username", "root"),
        password=conn.get("password", "root"),
        enable_rpc_compression=bool(conn.get("enable_rpc_compression", False)),
        root=db.get("root", "root.openrisk"),
        github=db.get("github", "root.openrisk.github"),
        gitee=db.get("gitee", "root.openrisk.gitee"),
        device_prefix=mapping.get("device_prefix", "root.openrisk"),
        device_format=mapping.get("device_format", "{platform}.{org}_{repo}"),
        raw_prefix=mapping.get("raw_prefix", "raw_"),
        feat_prefix=mapping.get("feat_prefix", "feat_"),
        use_aligned=bool(write.get("use_aligned", True)),
        batch_size=int(write.get("batch_size", 500)),
    )


class IoTDBManager:
    def __init__(self, config: IoTDBConfig) -> None:
        if Session is None or TSDataType is None:
            raise RuntimeError(
                "apache-iotdb package is required. Install with: pip install apache-iotdb"
            )
        self.config = config
        self.session = Session(
            config.host,
            config.port,
            config.username,
            config.password,
        )

    def open(self) -> None:
        self.session.open(self.config.enable_rpc_compression)

    def close(self) -> None:
        self.session.close()

    def ensure_databases(self) -> None:
        for path in [self.config.github, self.config.gitee]:
            try:
                self.session.set_storage_group(path)
            except Exception:
                # Storage group may already exist
                pass

    def device_id(self, platform: str, org: str, repo: str) -> str:
        def sanitize(value: str) -> str:
            return "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in value)

        safe = self.config.device_format.format(
            platform=sanitize(platform),
            org=sanitize(org),
            repo=sanitize(repo),
        )
        return f"{self.config.device_prefix}.{safe}"

    def measurement_name(self, kind: str, metric: str, feature: str | None = None) -> str:
        if kind == "raw":
            return f"{self.config.raw_prefix}{metric}"
        if kind == "feat":
            if feature:
                return f"{self.config.feat_prefix}{metric}_{feature}"
            return f"{self.config.feat_prefix}{metric}"
        return metric

    def insert_aligned(
        self,
        device_id: str,
        timestamp_ms: int,
        measurements: Sequence[str],
        values: Sequence[float],
    ) -> None:
        types = [self._infer_type(v) for v in values]
        self.session.insert_aligned_record(
            device_id,
            timestamp_ms,
            list(measurements),
            types,
            list(values),
        )

    def insert_batch_aligned(
        self,
        device_ids: List[str],
        timestamps: List[int],
        measurements_list: List[List[str]],
        values_list: List[List[float]],
    ) -> None:
        types_list: List[List[TSDataType]] = [
            [self._infer_type(value) for value in values] for values in values_list
        ]
        self.session.insert_aligned_records(
            device_ids,
            timestamps,
            measurements_list,
            types_list,
            values_list,
        )

    def insert_record(
        self,
        device_id: str,
        timestamp_ms: int,
        measurements: Sequence[str],
        values: Sequence[object],
    ) -> None:
        types = [self._infer_type(v) for v in values]
        self.session.insert_record(
            device_id,
            timestamp_ms,
            list(measurements),
            types,
            list(values),
        )

    @staticmethod
    def _infer_type(value: object) -> TSDataType:
        if isinstance(value, str):
            return TSDataType.TEXT
        return TSDataType.FLOAT

    @staticmethod
    def period_to_timestamp(period: str) -> int:
        if len(period) == 7 and "-" in period:
            dt_obj = dt.datetime.strptime(period + "-01", "%Y-%m-%d")
        elif len(period) == 6 and "Q" in period:
            year = int(period[:4])
            q = int(period[5])
            month = (q - 1) * 3 + 1
            dt_obj = dt.datetime(year, month, 1)
        elif len(period) == 4:
            dt_obj = dt.datetime(int(period), 1, 1)
        else:
            raise ValueError(f"Unsupported period format: {period}")
        return int(dt_obj.replace(tzinfo=dt.timezone.utc).timestamp() * 1000)
