#!/usr/bin/env bash
# Hits /health on the gateway (which in turn checks every internal service)
# and prints a pass/fail summary. Requires the stack to be running.
set -euo pipefail

GATEWAY_URL="${GATEWAY_URL:-http://localhost/health}"

echo "[smoke-test] Checking ${GATEWAY_URL} ..."
response=$(curl -fsS "${GATEWAY_URL}" || true)

if [ -z "${response}" ]; then
  echo "[smoke-test] FAILED: could not reach gateway health endpoint"
  exit 1
fi

echo "${response}" | python3 -m json.tool
echo "[smoke-test] Done."
