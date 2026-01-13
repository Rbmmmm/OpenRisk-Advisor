from __future__ import annotations

import argparse
from pathlib import Path

from .config import load_metrics_config, load_sources_config, resolve_configs
from .fetcher import fetch_metric
from .parser import parse_metric_file
from .storage import Storage


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch and parse OpenDigger metrics without typer.")
    parser.add_argument("--sources", required=True, type=Path, help="Path to sources.yaml")
    parser.add_argument("--metrics", required=True, type=Path, help="Path to metrics.yaml")
    parser.add_argument("--retries", type=int, default=2, help="Max retries for network errors")
    args = parser.parse_args()

    sources_cfg = load_sources_config(args.sources)
    metrics_cfg = load_metrics_config(args.metrics)
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
                    max_retries=args.retries,
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
