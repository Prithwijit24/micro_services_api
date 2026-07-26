#!/usr/bin/env bash
# Runs the local FastAPI smoke test suite (no Docker required).
# Installs a minimal set of lightweight test dependencies if missing.
set -euo pipefail

cd "$(dirname "$0")/.."

REQUIRED_PKGS="fastapi uvicorn httpx pydantic pydantic-settings redis neo4j yt-dlp chromadb numpy"

echo "[test] Checking test dependencies..."
python3 -c "import fastapi, httpx, pydantic, redis, neo4j, yt_dlp, chromadb, numpy" 2>/dev/null || {
  echo "[test] Installing: ${REQUIRED_PKGS}"
  pip install --break-system-packages -q ${REQUIRED_PKGS}
}

echo "[test] Running smoke tests..."
python3 tests/test_smoke.py
