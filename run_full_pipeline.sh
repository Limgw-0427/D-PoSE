#!/usr/bin/env bash
# Sequential file-based pipeline: hsmr -> dpose -> fusion.
# Run from the directory containing docker-compose.yml (e.g. D-PoSE root).
# Requires: Docker, Docker Compose v2, NVIDIA Container Toolkit.
# Usage: ./run_full_pipeline.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Ensure shared_data dirs exist (로컬 폴더 ./shared_data)
echo "[Pipeline] Ensuring shared_data dirs..."
mkdir -p shared_data/inputs shared_data/logs shared_data/hsmr_out shared_data/dpose_out shared_data/fusion_out

# Sequential execution (no parallel runs to avoid GPU memory conflicts)
echo "[Pipeline] Step 1/3: Running hsmr..."
docker compose --profile pipeline run --rm hsmr

echo "[Pipeline] Step 2/3: Running dpose..."
docker compose --profile pipeline run --rm dpose

echo "[Pipeline] Step 3/3: Running fusion..."
docker compose --profile pipeline run --rm fusion

echo "[Pipeline] Done. Results: ./shared_data/hsmr_out, dpose_out, fusion_out; logs in ./shared_data/logs/"
