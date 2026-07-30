#!/bin/bash
set -e

# On first boot, copy pre-installed Playwright browsers to persistent volume
PLAYWRIGHT_BROWSERS="/root/.cache/ms-playwright"
PLAYWRIGHT_PREINSTALLED="/opt/playwright-browsers"

if ! ls "$PLAYWRIGHT_BROWSERS"/chromium-* >/dev/null 2>&1 || \
   ! ls "$PLAYWRIGHT_BROWSERS"/firefox-* >/dev/null 2>&1; then
    echo ">>> First boot: copying Playwright browsers to persistent volume..."
    mkdir -p "$PLAYWRIGHT_BROWSERS"
    cp -r "$PLAYWRIGHT_PREINSTALLED"/* "$PLAYWRIGHT_BROWSERS"/
    echo ">>> Playwright browsers ready (persisted)."
fi

exec uv run --no-sync uvicorn app.main:app --host 0.0.0.0 --port 8000
