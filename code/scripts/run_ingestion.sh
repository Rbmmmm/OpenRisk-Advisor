#!/usr/bin/env bash
set -euo pipefail

python -m services.ingestion.cli all \
  --sources configs/sources.yaml \
  --metrics configs/metrics.yaml
