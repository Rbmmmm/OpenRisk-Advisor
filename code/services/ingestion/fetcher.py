from __future__ import annotations

import datetime as dt
import logging
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

from .config import MetricConfig, ResolvedRepo
from .utils import file_sha256

logger = logging.getLogger(__name__)


@dataclass
class FetchResult:
    repo: ResolvedRepo
    metric: MetricConfig
    url: str
    path: Path
    status: str
    error: str | None
    fetched_at: str
    file_hash: str | None
    http_status: int | None
    final_url: str | None
    response_size: int | None
    error_type: str | None
    retry_count: int


def build_url(base_url: str, repo: ResolvedRepo, metric: MetricConfig) -> str:
    return f"{base_url}/{repo.platform}/{repo.org}/{repo.repo}/{metric.file}"


def fetch_metric(
    base_url: str,
    repo: ResolvedRepo,
    metric: MetricConfig,
    cache_dir: Path,
    max_retries: int = 2,
) -> FetchResult:
    url = build_url(base_url, repo, metric)
    target_dir = cache_dir / repo.platform / repo.org / repo.repo
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / metric.file

    fetched_at = dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    file_hash = None
    status = "error"
    error = None
    http_status = None
    final_url = None
    response_size = None
    error_type = None
    retry_count = 0

    for attempt in range(max_retries + 1):
        retry_count = attempt
        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                content = response.read()
                http_status = getattr(response, "status", None)
                final_url = response.geturl()
            target_path.write_bytes(content)
            response_size = len(content)
            file_hash = file_sha256(target_path)
            status = "ok"
            error = None
            error_type = None
            break
        except urllib.error.HTTPError as exc:
            http_status = exc.code
            final_url = exc.geturl()
            status = f"http_{exc.code}"
            error = str(exc)
            error_type = "http_error"
            break
        except urllib.error.URLError as exc:
            reason = exc.reason
            if isinstance(reason, socket.timeout):
                error_type = "timeout"
                status = "timeout"
            else:
                error_type = "connection"
                status = "network_error"
            error = str(exc)
            if attempt >= max_retries:
                break
        except Exception as exc:  # noqa: BLE001
            status = "error"
            error = str(exc)
            error_type = "unknown"
            break

    return FetchResult(
        repo=repo,
        metric=metric,
        url=url,
        path=target_path,
        status=status,
        error=error,
        fetched_at=fetched_at,
        file_hash=file_hash,
        http_status=http_status,
        final_url=final_url,
        response_size=response_size,
        error_type=error_type,
        retry_count=retry_count,
    )


def fetch_all(
    base_url: str,
    repos: Iterable[ResolvedRepo],
    metrics: Iterable[MetricConfig],
    cache_dir: Path,
) -> List[FetchResult]:
    results: List[FetchResult] = []
    for repo in repos:
        for metric in metrics:
            logger.info("fetching %s %s", repo.full_name, metric.file)
            result = fetch_metric(base_url, repo, metric, cache_dir)
            results.append(result)
            if result.status != "ok":
                logger.warning("fetch failed %s %s: %s", repo.full_name, metric.file, result.status)
    return results
