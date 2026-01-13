from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import yaml
from pydantic import BaseModel, Field, ValidationError


class MetricConfig(BaseModel):
    name: str
    file: str
    level: str = Field("repo", description="repo or developer")
    description: Optional[str] = None
    granularity: Optional[List[str]] = None
    keep_raw: Optional[bool] = None
    missing_policy: Optional[str] = None


class MetricDefaults(BaseModel):
    granularity: List[str] = Field(default_factory=lambda: ["month", "quarter", "year"])
    keep_raw: bool = True
    missing_policy: str = "keep"


class MetricsConfig(BaseModel):
    version: int
    defaults: Optional[MetricDefaults] = None
    metrics: List[MetricConfig]


class SourceDefaults(BaseModel):
    platform: str = "github"
    base_url: str = "https://oss.open-digger.cn"
    cache_dir: str = "data/cache"
    sqlite_path: str = "data/sqlite/opendigger.db"


class RepoConfig(BaseModel):
    org: str
    repo: str
    platform: Optional[str] = None
    enabled: bool = True

    @property
    def full_name(self) -> str:
        return f"{self.org}/{self.repo}"


class SourcesConfig(BaseModel):
    version: int
    defaults: SourceDefaults
    repos: List[RepoConfig]


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_metrics_config(path: Path) -> MetricsConfig:
    data = load_yaml(path)
    try:
        return MetricsConfig(**data)
    except ValidationError as exc:
        raise ValueError(f"Invalid metrics config: {path}") from exc


def load_sources_config(path: Path) -> SourcesConfig:
    data = load_yaml(path)
    try:
        return SourcesConfig(**data)
    except ValidationError as exc:
        raise ValueError(f"Invalid sources config: {path}") from exc


class ResolvedRepo(BaseModel):
    platform: str
    org: str
    repo: str

    @property
    def full_name(self) -> str:
        return f"{self.org}/{self.repo}"

    @property
    def path_parts(self) -> List[str]:
        return [self.platform, self.org, self.repo]


class ResolvedConfigs(BaseModel):
    base_url: str
    cache_dir: Path
    sqlite_path: Path
    repos: List[ResolvedRepo]
    metrics: List[MetricConfig]


def resolve_configs(
    sources: SourcesConfig, metrics: MetricsConfig
) -> ResolvedConfigs:
    repos: List[ResolvedRepo] = []
    for repo in sources.repos:
        if not repo.enabled:
            continue
        platform = repo.platform or sources.defaults.platform
        repos.append(ResolvedRepo(platform=platform, org=repo.org, repo=repo.repo))

    return ResolvedConfigs(
        base_url=sources.defaults.base_url.rstrip("/"),
        cache_dir=Path(sources.defaults.cache_dir),
        sqlite_path=Path(sources.defaults.sqlite_path),
        repos=repos,
        metrics=metrics.metrics,
    )
