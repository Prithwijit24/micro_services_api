FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# System deps for MySQL client, healthchecks, Playwright
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl wget gcc ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
# Install Playwright browsers: Firefox (primary — bypasses bot detection) + Chromium (fallback)
RUN uv run playwright install firefox chromium --with-deps
# Preserve browsers so entrypoint can copy them into tmpfs at startup (no re-download)
RUN mkdir -p /opt/playwright-browsers && cp -r /root/.cache/ms-playwright/* /opt/playwright-browsers/

# Copy application code and startup script
COPY app/ ./app/
COPY scripts/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
