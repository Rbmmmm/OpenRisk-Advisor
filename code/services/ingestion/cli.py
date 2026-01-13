from __future__ import annotations

import logging
import time
from pathlib import Path

import typer

from .config import load_metrics_config, load_sources_config, resolve_configs
from .fetcher import fetch_metric
from .parser import parse_metric_file
from .storage import Storage

app = typer.Typer(add_completion=False)


def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


@app.command()
def fetch(
    sources: Path = typer.Option(..., exists=True, help="Path to sources.yaml"),
    metrics: Path = typer.Option(..., exists=True, help="Path to metrics.yaml"),
    retries: int = typer.Option(2, help="Max retries for network errors"),
    log_level: str = typer.Option("INFO", help="Log level"),
) -> None:
    setup_logging(log_level)
    logger = logging.getLogger(__name__)

    sources_cfg = load_sources_config(sources)
    metrics_cfg = load_metrics_config(metrics)
    resolved = resolve_configs(sources_cfg, metrics_cfg)

    storage = Storage(resolved.sqlite_path)

    try:
        total = len(resolved.repos) * len(resolved.metrics)
        logger.info(
            "starting fetch: repos=%d metrics=%d combos=%d cache_dir=%s db=%s",
            len(resolved.repos),
            len(resolved.metrics),
            total,
            resolved.cache_dir,
            resolved.sqlite_path,
        )
        started = time.monotonic()
        done = 0
        for repo in resolved.repos:
            repo_id = storage.upsert_repo(repo)
            for metric in resolved.metrics:
                metric_id = storage.upsert_metric(metric)
                t0 = time.monotonic()
                result = fetch_metric(
                    resolved.base_url,
                    repo,
                    metric,
                    resolved.cache_dir,
                    max_retries=retries,
                )
                done += 1
                storage.record_raw_file(
                    repo_id=repo_id,
                    metric_id=metric_id,
                    path=result.path,
                    url=result.url,
                    fetched_at=result.fetched_at,
                    status=result.status,
                    error=result.error,
                    file_hash=result.file_hash,
                    http_status=result.http_status,
                    final_url=result.final_url,
                    response_size=result.response_size,
                    error_type=result.error_type,
                    retry_count=result.retry_count,
                )

                elapsed_ms = int((time.monotonic() - t0) * 1000)
                if result.status == "ok":
                    logger.info(
                        "fetched ok [%d/%d] %s %s http=%s bytes=%s retry=%d %.3fs",
                        done,
                        total,
                        repo.full_name,
                        metric.file,
                        result.http_status,
                        result.response_size,
                        result.retry_count,
                        elapsed_ms / 1000,
                    )
                else:
                    logger.warning(
                        "fetch failed [%d/%d] %s %s status=%s http=%s err_type=%s retry=%d %.3fs",
                        done,
                        total,
                        repo.full_name,
                        metric.file,
                        result.status,
                        result.http_status,
                        result.error_type,
                        result.retry_count,
                        elapsed_ms / 1000,
                    )
        total_s = time.monotonic() - started
        logger.info("fetch finished: combos=%d elapsed=%.1fs", total, total_s)
    finally:
        storage.close()


@app.command()
def parse(
    sources: Path = typer.Option(..., exists=True, help="Path to sources.yaml"),
    metrics: Path = typer.Option(..., exists=True, help="Path to metrics.yaml"),
    log_level: str = typer.Option("INFO", help="Log level"),
) -> None:
    setup_logging(log_level)

    sources_cfg = load_sources_config(sources)
    metrics_cfg = load_metrics_config(metrics)
    resolved = resolve_configs(sources_cfg, metrics_cfg)

    storage = Storage(resolved.sqlite_path)

    try:
        for repo in resolved.repos:
            repo_id = storage.upsert_repo(repo)
            for metric in resolved.metrics:
                metric_id = storage.upsert_metric(metric)
                path = resolved.cache_dir / repo.platform / repo.org / repo.repo / metric.file
                if not path.exists():
                    logging.getLogger(__name__).warning(
                        "missing cache file %s", path
                    )
                    continue
                result = parse_metric_file(storage, repo_id, metric_id, path)
                logging.getLogger(__name__).info(
                    "parsed %s %s: %s", repo.full_name, metric.file, result
                )
    finally:
        storage.close()


@app.command()
def all(
    sources: Path = typer.Option(..., exists=True, help="Path to sources.yaml"),
    metrics: Path = typer.Option(..., exists=True, help="Path to metrics.yaml"),
    retries: int = typer.Option(2, help="Max retries for network errors"),
    log_level: str = typer.Option("INFO", help="Log level"),
) -> None:
    """Fetch and parse in a single run."""
    setup_logging(log_level)

    sources_cfg = load_sources_config(sources)
    metrics_cfg = load_metrics_config(metrics)
    resolved = resolve_configs(sources_cfg, metrics_cfg)

    storage = Storage(resolved.sqlite_path)

    try:
        for repo in resolved.repos:
            repo_id = storage.upsert_repo(repo)
            for metric in resolved.metrics:
                metric_id = storage.upsert_metric(metric)
                result = fetch_metric(
                    resolved.base_url,
                    repo,
                    metric,
                    resolved.cache_dir,
                    max_retries=retries,
                )
                storage.record_raw_file(
                    repo_id=repo_id,
                    metric_id=metric_id,
                    path=result.path,
                    url=result.url,
                    fetched_at=result.fetched_at,
                    status=result.status,
                    error=result.error,
                    file_hash=result.file_hash,
                    http_status=result.http_status,
                    final_url=result.final_url,
                    response_size=result.response_size,
                    error_type=result.error_type,
                    retry_count=result.retry_count,
                )
                if result.status != "ok":
                    continue
                parse_metric_file(storage, repo_id, metric_id, result.path)
    finally:
        storage.close()


if __name__ == "__main__":
    app()
