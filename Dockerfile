FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# System deps for MySQL client, healthchecks, Playwright
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl wget gcc ffmpeg default-libmysqlclient-dev pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
RUN uv pip install python-multipart

# Install Playwright browsers: Firefox (primary — bypasses bot detection) + Chromium (fallback)
RUN uv run playwright install firefox chromium --with-deps

# Copy application code
COPY app/ ./app/

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
