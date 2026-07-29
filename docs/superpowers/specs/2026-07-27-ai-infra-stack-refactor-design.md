# AI Infra Stack Refactor Design

**Date:** 2026-07-27
**Status:** Approved
**Goal:** Consolidate 11 duplicated microservices into a single FastAPI app with minimal boilerplate.

---

## Problem Statement

The current codebase has 11 microservices, each with identical 4-file structures (`main.py`, `service.py`, `models.py`, `routers/`). This creates:
- **Massive duplication** — same FastAPI setup, health endpoints, error handling in 11 places
- **Hard to maintain** — fixing a pattern requires editing 11 files
- **Slow builds** — 11 separate Dockerfiles, 11 separate requirements.txt
- **Over-engineering** — inter-service HTTP calls for what could be in-process calls

## Target Architecture

**Single FastAPI app, single Docker container, single requirements file.**

### Project Layout

```
ai-infra-stack/
├── app/
│   ├── main.py              # Single FastAPI app entry point
│   ├── deps.py              # Shared lazy-loaded dependencies
│   ├── models.py            # All Pydantic models (single file)
│   ├── routers/
│   │   ├── __init__.py      # register_all_routers()
│   │   ├── search.py        # ~20 lines
│   │   ├── browse.py        # ~25 lines
│   │   ├── embed.py         # ~20 lines
│   │   ├── youtube.py       # ~35 lines
│   │   ├── clip.py          # ~20 lines
│   │   ├── reranker.py      # ~20 lines
│   │   ├── graph.py         # ~25 lines
│   │   ├── vector.py        # ~25 lines
│   │   ├── cache.py         # ~25 lines
│   │   ├── crawl.py         # ~20 lines
│   │   ├── duckdb.py        # ~25 lines
│   │   ├── storage.py       # ~30 lines
│   │   └── pipeline.py      # ~40 lines
│   └── services/
│       ├── browser.py       # Playwright/Camoufox logic
│       ├── embed.py         # Sentence-transformers
│       ├── youtube.py       # yt-dlp + Whisper
│       ├── search.py        # SearXNG HTTP client
│       ├── reranker.py      # Cross-encoder
│       ├── clip.py          # CLIP model
│       ├── graph.py         # Neo4j client
│       ├── vector.py        # ChromaDB client
│       ├── cache.py         # Redis client
│       ├── crawl.py         # Scrapling + Trafilatura
│       ├── duckdb.py        # DuckDB OLAP
│       ├── storage.py       # MinIO S3 client
│       ├── proxy.py         # Free proxy routing
│       └── pipeline.py      # Search→Crawl→Rerank pipeline
├── Dockerfile               # ONE Dockerfile
├── pyproject.toml           # ONE dependency file (uv)
├── docker-compose.yml       # App + infrastructure only
├── .env.example             # All env vars documented
├── Makefile                 # Simplified targets
├── scripts/
│   └── smoke_test.sh
├── backups/
├── data/                    # Persistent volumes
│   ├── browser/
│   ├── youtube/
│   ├── searxng/
│   ├── redis/
│   ├── chroma/
│   ├── neo4j/
│   ├── duckdb/
│   └── minio/
└── tests/
    └── test_smoke.py
```

## Component Details

### 1. `app/main.py` — Single Entry Point

```python
from fastapi import FastAPI
from app.routers import register_all_routers

app = FastAPI(
    title="AI Infra Stack",
    description="Unified API for search, browse, embed, crawl, and more",
    version="2.0.0",
)

register_all_routers(app)

@app.get("/health")
async def health():
    return {"status": "ok"}
```

### 2. `app/routers/__init__.py` — Router Registration

```python
from fastapi import FastAPI

def register_all_routers(app: FastAPI):
    from app.routers import (
        search, browse, embed, youtube, clip,
        reranker, graph, vector, cache, crawl, duckdb, storage, pipeline,
    )
    for module in [search, browse, embed, youtube, clip,
                   reranker, graph, vector, cache, crawl, duckdb, storage, pipeline]:
        app.include_router(module.router)
```

### 3. `app/routers/<service>.py` — Router Pattern

Each router follows this pattern:

```python
from fastapi import APIRouter, HTTPException
from app.models import <Request>, <Response>
from app.services.<service> import <Service>

router = APIRouter(prefix="/<service>")
svc = <Service>()

@router.post("/", response_model=<Response>)
async def endpoint(req: <Request>):
    try:
        return await svc.method(req)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
```

### 4. `app/services/<service>.py` — Business Logic

Each service is a thin class wrapping the actual library call:

- **search.py**: ~15 lines, wraps httpx call to SearXNG
- **browse.py**: ~80 lines, multi-layer browser fallback (Firefox/Chromium/StealthyFetcher)
- **embed.py**: ~20 lines, wraps sentence-transformers
- **youtube.py**: ~150 lines, wraps yt-dlp + Whisper STT
- **clip.py**: ~20 lines, wraps sentence-transformers
- **reranker.py**: ~20 lines, wraps cross-encoder
- **graph.py**: ~30 lines, wraps neo4j driver
- **vector.py**: ~30 lines, wraps chromadb
- **cache.py**: ~25 lines, wraps redis
- **crawl.py**: ~50 lines, Scrapling + Trafilatura + Playwright fallback
- **duckdb.py**: ~30 lines, wraps duckdb
- **storage.py**: ~40 lines, wraps MinIO S3
- **proxy.py**: ~50 lines, free proxy routing
- **pipeline.py**: ~100 lines, Search→Crawl→Rerank pipeline

**Total: ~680 lines across all services.**

### 5. `app/deps.py` — Lazy-Loaded Shared Dependencies

Heavy resources (ML models, HTTP clients) are loaded on first use, not at startup:

```python
# HTTP Client (shared across search, crawl, gateway)
# Redis Client (shared across cache)
# Embed Model (lazy-loaded sentence-transformers)
# CLIP Model (lazy-loaded sentence-transformers)
# Reranker Model (lazy-loaded cross-encoder)
```

**Key:** If you only use search + browse, you never load ML models. Fast startup.

### 6. `app/models.py` — All Pydantic Models

Single file with section comments, ~200 lines total. Organized by service:

- Search (3 models)
- Browse (2 models)
- Embed (2 models)
- YouTube (6 models)
- CLIP (2 models)
- Reranker (2 models)
- Graph (3 models)
- Vector (3 models)
- Cache (4 models)
- Crawl (2 models)

### 7. `Dockerfile` — Single Container

```dockerfile
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN uv tool install playwright && uv run playwright install firefox --with-deps

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY app/ ./app/

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 8. `pyproject.toml` — Dependencies

```toml
[project]
name = "ai-infra-stack"
version = "2.0.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    "pydantic>=2.0",
    "httpx>=0.27",
    "redis[hiredis]>=5.0",
    "sentence-transformers>=3.0",
    "yt-dlp>=2024.0",
    "neo4j>=5.0",
    "chromadb>=0.5.0",
    "playwright>=1.45",
]
```

### 9. `docker-compose.yml` — Infrastructure Only

**Before:** 20 containers (11 app + 7 infra + 2 monitoring)
**After:** 10 containers (1 app + 7 infra + 2 monitoring)

```yaml
services:
  app:
    build: .
    container_name: ai-stack-app
    restart: unless-stopped
    networks:
      - internal
    env_file: .env
    expose:
      - "8000"
    volumes:
      - ./models:/root/.cache/huggingface
      - ./data/browser:/data/browser
      - ./data/youtube:/opt/data/youtube
    healthcheck:
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 30s
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
    depends_on:
      redis:
        condition: service_healthy
      neo4j:
        condition: service_healthy
      chromadb:
        condition: service_healthy

  # Infrastructure services remain unchanged:
  postgres:
    image: postgres:17-alpine
    # ... (same as current)

  redis:
    image: redis:7.4-alpine
    # ... (same as current)

  neo4j:
    image: neo4j:5.26-community
    # ... (same as current)

  chromadb:
    image: chromadb/chroma:0.5.23
    # ... (same as current)

  searxng:
    image: searxng/searxng:latest
    # ... (same as current)

  firecrawl:
    image: mcp/firecrawl:latest
    # ... (same as current)

  caddy:
    image: caddy:2.9-alpine
    # ... (same as current, but points to app:8000)

  uptime-kuma:
    image: louislam/uptime-kuma:1
    # ... (same as current)

  dozzle:
    image: amir20/dozzle:latest
    # ... (same as current)
```

### 10. `.env.example` — Documented Environment Variables

```bash
# ═══════════════════════════════════════════════════════════════
# AI Infra Stack — Environment Variables
# Copy this file to .env and fill in the values you need.
# Only infrastructure vars are required. Service vars are optional.
# ═══════════════════════════════════════════════════════════════

# ── Infrastructure (required) ─────────────────────────────────
REDIS_URL=redis://redis:6379/0
POSTGRES_USER=aistack
POSTGRES_PASSWORD=changeme
POSTGRES_DB=aistack
NEO4J_USER=neo4j
NEO4J_PASSWORD=changeme
NEO4J_PAGECACHE=512M
NEO4J_HEAP_MAX=1G
SEARXNG_BASE_URL=http://localhost:8080/

# ── Search (optional) ────────────────────────────────────────
SEARXNG_URL=http://searxng:8080

# ── Browse (optional) ────────────────────────────────────────
CAMOUFOX_WS_ENDPOINT=  # Leave empty for local Playwright

# ── Embed (optional) ─────────────────────────────────────────
EMBED_MODEL=BAAI/bge-small-en-v1.5
HF_HOME=/root/.cache/huggingface

# ── CLIP (optional) ──────────────────────────────────────────
CLIP_MODEL=clip-ViT-B-32

# ── Reranker (optional) ──────────────────────────────────────
RERANK_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2

# ── YouTube (optional) ───────────────────────────────────────
YOUTUBE_DOWNLOAD_DIR=/opt/data/youtube
YOUTUBE_MAX_CONCURRENT_DOWNLOADS=2

# ── Crawl (optional) ─────────────────────────────────────────
FIRECRAWL_API_KEY=  # Only if using external Firecrawl
```

### 11. `Makefile` — Simplified

```makefile
SHELL := /bin/bash
COMPOSE := docker compose

.PHONY: help up down logs build restart ps clean backup restore smoke-test

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

up: ## Build and start everything
	@test -f .env || cp .env.example .env
	$(COMPOSE) up -d --build

down: ## Stop everything
	$(COMPOSE) down

logs: ## Tail logs
	$(COMPOSE) logs -f --tail=200

build: ## Rebuild the app image
	$(COMPOSE) build app

restart: ## Restart all services
	$(COMPOSE) restart

ps: ## Show container status
	$(COMPOSE) ps

clean: ## Remove containers + dangling images
	$(COMPOSE) down --remove-orphans
	docker image prune -f

backup: ## Backup databases
	@bash scripts/backup.sh

restore: ## Restore from backup: make restore FILE=./backups/xxx.tar.gz
	@test -n "$(FILE)" || (echo "Usage: make restore FILE=./backups/<file>.tar.gz"; exit 1)
	@bash scripts/restore.sh $(FILE)

smoke-test: ## Hit /health on app through gateway
	@bash scripts/smoke_test.sh
```

## Migration Plan

### What gets deleted:
- 11 `services/*/main.py` files
- 11 `services/*/service.py` files
- 11 `services/*/models.py` files
- 11 `services/*/routers/` directories
- 11 `services/*/Dockerfile` files
- 11 `services/*/requirements.txt` files
- 11 `services/*/` directories (entire `services/` folder)

### What gets created:
- `app/` directory with all new code
- `pyproject.toml` (replaces 11 requirements.txt)
- `.env.example` (new)
- Updated `docker-compose.yml` (single app service)
- Updated `Makefile` (simplified)

### What stays unchanged:
- `caddy/` directory
- `scripts/` directory
- `tests/` directory
- `data/` directory structure
- `backups/` directory
- `models/` directory (HuggingFace cache)
- Infrastructure services in docker-compose.yml (redis, neo4j, chromadb, searxng, dozzle)

## How to Add a New Service

1. Add models to `app/models.py`
2. Create `app/services/<new>.py` with business logic
3. Create `app/routers/<new>.py` with router
4. Import in `app/routers/__init__.py`
5. Add env vars to `.env.example` if needed
6. Add dependencies to `pyproject.toml` if needed

**Total: ~100 lines of code. No new Dockerfile, no new requirements.txt, no docker-compose changes.**

## Verification

After implementation:
1. `docker compose up -d --build` — builds single app container
2. `curl http://localhost:8000/health` — returns `{"status": "ok"}`
3. `make smoke-test` — hits all endpoints through gateway
4. Verify each service endpoint works individually
