#!/usr/bin/env bash
# Fresh database and uploads for every run, then the API on :8000.
set -euo pipefail
cd "$(dirname "$0")/../../backend"

export VI_DATABASE_URL="sqlite:///./data/e2e/vendor_intake.db"
export VI_STORAGE_DIR="./data/e2e/uploads"
# Short but non-zero, so UI tests exercise the "processing" state and polling.
export VI_EXTRACTION_DELAY_SECONDS="${VI_EXTRACTION_DELAY_SECONDS:-0.5}"
# Uploads of the extraction eval set's documents get Claude's recorded output (no API key);
# every other upload uses the deterministic backend, as before.
export VI_EXTRACTION_BACKEND="${VI_EXTRACTION_BACKEND:-replay}"

rm -rf data/e2e
uv run python -m vendor_intake.seed
exec uv run uvicorn vendor_intake.main:create_app --factory --port 8000
