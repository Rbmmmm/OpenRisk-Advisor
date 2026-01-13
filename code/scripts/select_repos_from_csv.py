#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import random
from pathlib import Path

import yaml


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "Select N repos from repo_list.csv deterministically and write into configs/sources.yaml.\n"
            "Rule: keep first K pinned repos from existing sources.yaml, then append unique repos from CSV."
        )
    )
    p.add_argument("--csv", default="repo_list.csv", help="Path to repo_list.csv")
    p.add_argument(
        "--sources",
        default="configs/sources.yaml",
        help="Path to sources.yaml to read and update",
    )
    p.add_argument(
        "--out",
        default=None,
        help="Output path (default: overwrite --sources)",
    )
    p.add_argument("--limit", type=int, default=50, help="Total number of repos")
    p.add_argument(
        "--platform",
        default="github",
        help="Only include rows with this platform value",
    )
    p.add_argument(
        "--mode",
        choices=["order", "random"],
        default="order",
        help="Selection mode for repos coming from CSV (order=CSV order, random=sample with seed)",
    )
    p.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for --mode random (for reproducibility)",
    )
    p.add_argument(
        "--pinned-count",
        type=int,
        default=4,
        help="Keep first K repos in sources.yaml as pinned",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    csv_path = Path(args.csv)
    sources_path = Path(args.sources)
    out_path = Path(args.out) if args.out else sources_path

    if args.limit <= 0:
        raise SystemExit("--limit must be > 0")
    if not csv_path.exists():
        raise SystemExit(f"CSV not found: {csv_path}")
    if not sources_path.exists():
        raise SystemExit(f"sources.yaml not found: {sources_path}")

    sources = yaml.safe_load(sources_path.read_text(encoding="utf-8"))
    repos = list(sources.get("repos", []))

    pinned_count = max(0, min(args.pinned_count, len(repos)))
    pinned = repos[:pinned_count]

    selected: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    def add_repo(org: str, repo: str) -> None:
        key = (org, repo)
        if key in seen:
            return
        seen.add(key)
        selected.append({"org": org, "repo": repo})

    for r in pinned:
        if not isinstance(r, dict) or "org" not in r or "repo" not in r:
            continue
        add_repo(str(r["org"]), str(r["repo"]))

    if args.mode == "order":
        with csv_path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("platform") != args.platform:
                    continue
                repo_name = (row.get("repo_name") or "").strip()
                if "/" not in repo_name:
                    continue
                org, repo = repo_name.split("/", 1)
                org = org.strip()
                repo = repo.strip()
                if not org or not repo:
                    continue
                add_repo(org, repo)
                if len(selected) >= args.limit:
                    break
    else:
        # Random sample, reproducible via seed.
        rnd = random.Random(args.seed)
        candidates: list[tuple[str, str]] = []
        with csv_path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("platform") != args.platform:
                    continue
                repo_name = (row.get("repo_name") or "").strip()
                if "/" not in repo_name:
                    continue
                org, repo = repo_name.split("/", 1)
                org = org.strip()
                repo = repo.strip()
                if not org or not repo:
                    continue
                key = (org, repo)
                if key in seen:
                    continue
                candidates.append(key)

        need = args.limit - len(selected)
        if need <= 0:
            candidates = []
        if need > len(candidates):
            raise SystemExit(
                f"Not enough candidates after filtering: need {need}, got {len(candidates)}"
            )
        picked = rnd.sample(candidates, k=need)
        for org, repo in picked:
            add_repo(org, repo)

    if len(selected) < args.limit:
        raise SystemExit(
            f"Not enough repos after filtering: got {len(selected)}, want {args.limit}"
        )

    sources["repos"] = selected[: args.limit]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        yaml.safe_dump(sources, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )

    print(f"Wrote {args.limit} repos to {out_path}")


if __name__ == "__main__":
    main()
