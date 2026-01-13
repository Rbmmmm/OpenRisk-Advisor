from __future__ import annotations

import datetime as dt
import sqlite3
from pathlib import Path
from typing import Iterable, Optional

from .config import MetricConfig, ResolvedRepo


class Storage:
    def __init__(self, sqlite_path: Path) -> None:
        self.sqlite_path = sqlite_path
        self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.sqlite_path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def close(self) -> None:
        self.conn.close()

    def _init_schema(self) -> None:
        cursor = self.conn.cursor()
        cursor.executescript(
            """
            CREATE TABLE IF NOT EXISTS repos (
                id INTEGER PRIMARY KEY,
                platform TEXT NOT NULL,
                org TEXT NOT NULL,
                repo TEXT NOT NULL,
                full_name TEXT NOT NULL UNIQUE
            );

            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                file TEXT NOT NULL,
                level TEXT NOT NULL,
                description TEXT,
                UNIQUE(file)
            );

            CREATE TABLE IF NOT EXISTS raw_files (
                id INTEGER PRIMARY KEY,
                repo_id INTEGER NOT NULL,
                metric_id INTEGER NOT NULL,
                path TEXT NOT NULL,
                url TEXT NOT NULL,
                fetched_at TEXT NOT NULL,
                status TEXT NOT NULL,
                error TEXT,
                file_hash TEXT,
                http_status INTEGER,
                final_url TEXT,
                response_size INTEGER,
                error_type TEXT,
                retry_count INTEGER,
                FOREIGN KEY (repo_id) REFERENCES repos(id),
                FOREIGN KEY (metric_id) REFERENCES metrics(id)
            );

            CREATE TABLE IF NOT EXISTS raw_json (
                id INTEGER PRIMARY KEY,
                repo_id INTEGER NOT NULL,
                metric_id INTEGER NOT NULL,
                json_text TEXT NOT NULL,
                json_hash TEXT NOT NULL,
                parsed_at TEXT NOT NULL,
                parse_status TEXT NOT NULL,
                time_keys_count INTEGER NOT NULL,
                FOREIGN KEY (repo_id) REFERENCES repos(id),
                FOREIGN KEY (metric_id) REFERENCES metrics(id)
            );

            CREATE TABLE IF NOT EXISTS time_series (
                id INTEGER PRIMARY KEY,
                repo_id INTEGER NOT NULL,
                metric_id INTEGER NOT NULL,
                period TEXT NOT NULL,
                period_type TEXT NOT NULL,
                value REAL NOT NULL,
                is_raw INTEGER NOT NULL,
                source_key TEXT NOT NULL,
                FOREIGN KEY (repo_id) REFERENCES repos(id),
                FOREIGN KEY (metric_id) REFERENCES metrics(id),
                UNIQUE (repo_id, metric_id, period, period_type, is_raw)
            );

            CREATE TABLE IF NOT EXISTS time_series_object (
                id INTEGER PRIMARY KEY,
                repo_id INTEGER NOT NULL,
                metric_id INTEGER NOT NULL,
                period TEXT NOT NULL,
                period_type TEXT NOT NULL,
                json_value TEXT NOT NULL,
                is_raw INTEGER NOT NULL,
                source_key TEXT NOT NULL,
                FOREIGN KEY (repo_id) REFERENCES repos(id),
                FOREIGN KEY (metric_id) REFERENCES metrics(id),
                UNIQUE (repo_id, metric_id, period, period_type, is_raw)
            );
            """
        )
        self.conn.commit()
        self._ensure_raw_files_columns()

    def _ensure_raw_files_columns(self) -> None:
        cursor = self.conn.cursor()
        cursor.execute("PRAGMA table_info(raw_files)")
        existing = {row[1] for row in cursor.fetchall()}
        columns = {
            "http_status": "INTEGER",
            "final_url": "TEXT",
            "response_size": "INTEGER",
            "error_type": "TEXT",
            "retry_count": "INTEGER",
        }
        for name, col_type in columns.items():
            if name not in existing:
                cursor.execute(f"ALTER TABLE raw_files ADD COLUMN {name} {col_type}")
        self.conn.commit()

    def upsert_repo(self, repo: ResolvedRepo) -> int:
        cursor = self.conn.cursor()
        full_name = repo.full_name
        cursor.execute(
            """
            INSERT INTO repos (platform, org, repo, full_name)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(full_name) DO UPDATE SET
                platform=excluded.platform,
                org=excluded.org,
                repo=excluded.repo
            """,
            (repo.platform, repo.org, repo.repo, full_name),
        )
        self.conn.commit()
        cursor.execute("SELECT id FROM repos WHERE full_name = ?", (full_name,))
        return int(cursor.fetchone()["id"])

    def upsert_metric(self, metric: MetricConfig) -> int:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO metrics (name, file, level, description)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(file) DO UPDATE SET
                name=excluded.name,
                level=excluded.level,
                description=excluded.description
            """,
            (metric.name, metric.file, metric.level, metric.description),
        )
        self.conn.commit()
        cursor.execute("SELECT id FROM metrics WHERE file = ?", (metric.file,))
        return int(cursor.fetchone()["id"])

    def record_raw_file(
        self,
        repo_id: int,
        metric_id: int,
        path: Path,
        url: str,
        fetched_at: str,
        status: str,
        error: Optional[str],
        file_hash: Optional[str],
        http_status: Optional[int],
        final_url: Optional[str],
        response_size: Optional[int],
        error_type: Optional[str],
        retry_count: int,
    ) -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO raw_files
                (
                    repo_id, metric_id, path, url, fetched_at, status, error, file_hash,
                    http_status, final_url, response_size, error_type, retry_count
                )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                repo_id,
                metric_id,
                str(path),
                url,
                fetched_at,
                status,
                error,
                file_hash,
                http_status,
                final_url,
                response_size,
                error_type,
                retry_count,
            ),
        )
        self.conn.commit()

    def record_raw_json(
        self,
        repo_id: int,
        metric_id: int,
        json_text: str,
        json_hash: str,
        parse_status: str,
        time_keys_count: int,
    ) -> None:
        cursor = self.conn.cursor()
        parsed_at = dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
        cursor.execute(
            """
            INSERT INTO raw_json
                (repo_id, metric_id, json_text, json_hash, parsed_at, parse_status, time_keys_count)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                repo_id,
                metric_id,
                json_text,
                json_hash,
                parsed_at,
                parse_status,
                time_keys_count,
            ),
        )
        self.conn.commit()

    def upsert_time_series_rows(self, rows: Iterable[tuple]) -> int:
        cursor = self.conn.cursor()
        cursor.executemany(
            """
            INSERT INTO time_series
                (repo_id, metric_id, period, period_type, value, is_raw, source_key)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(repo_id, metric_id, period, period_type, is_raw) DO UPDATE SET
                value=excluded.value,
                source_key=excluded.source_key
            """,
            rows,
        )
        self.conn.commit()
        return cursor.rowcount

    def upsert_time_series_object_rows(self, rows: Iterable[tuple]) -> int:
        cursor = self.conn.cursor()
        cursor.executemany(
            """
            INSERT INTO time_series_object
                (repo_id, metric_id, period, period_type, json_value, is_raw, source_key)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(repo_id, metric_id, period, period_type, is_raw) DO UPDATE SET
                json_value=excluded.json_value,
                source_key=excluded.source_key
            """,
            rows,
        )
        self.conn.commit()
        return cursor.rowcount
