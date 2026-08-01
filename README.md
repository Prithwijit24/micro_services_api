<div align="center">

# 🧠 AI Infrastructure Stack

### *Production-ready, self-hosted AI infrastructure — one API to rule them all*

[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker&logoColor=white)](https://docker.com)
[![CI](https://img.shields.io/badge/CI-GitHub_Actions-2088FF?style=flat-square&logo=githubactions&logoColor=white)](.github/workflows/ci.yml)

```
🌐 Internet → 🔒 Caddy (TLS) → ⚡ FastAPI → 🛠️ 7 Docker + 1 Host
```

</div>

---

## 📋 Table of Contents

- [Quick Start](#-quick-start)
- [Architecture](#-architecture)
- [API Endpoints](#-api-endpoints)
- [Security](#-security)
- [CI Pipeline](#-ci-pipeline)
- [Configuration](#-configuration)
- [Troubleshooting](#-troubleshooting)

---

## 🚀 Quick Start

```bash
# 1. Clone
git clone <repo-url> && cd micro_services_api

# 2. Configure
cp .env.example .env
# Edit .env — set JWT_SECRET and ADMIN_PASS

# 3. Launch
docker compose up -d

# 4. Verify
curl https://aistackapi.duckdns.org/health
```

👉 **Full walkthrough:** See [QUICKSTART.md](QUICKSTART.md) for a notebook-style guide with every command and expected output.

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────┐
│                     🌐 INTERNET                           │
└─────────────────────────┬────────────────────────────────┘
                          │
               ┌──────────▼──────────┐
               │   🔒 CADDY (TLS)    │  Port 80/443
               │   Auto HTTPS        │
               └──────────┬──────────┘
                          │
               ┌──────────▼──────────┐
               │  ⚡ FASTAPI APP      │  Port 8000 (internal)
               │  30+ endpoints      │
               │  Auth + Rate Limit  │
               └──────────┬──────────┘
                          │
     ┌────────┬───────────┼───────────┬────────┐
     │        │           │           │        │
┌────▼───┐ ┌──▼────┐ ┌────▼────┐ ┌───▼───┐ ┌──▼─────┐
│🔍SearXNG│ │🧬Chroma│ │📊Neo4j │ │🗄️Redis│ │📁MinIO │
│ Search │ │Vector │ │ Graph  │ │ Cache │ │  S3   │
└────────┘ └───────┘ └────────┘ └───────┘ └───────┘
```

### 🐳 Services (7 Docker + 1 Host)

| # | Service | Image | Purpose |
|---|---------|-------|---------|
| 1 | **App** | Custom (Python 3.12) | FastAPI — all capabilities |
| 2 | **Redis** | `redis:7.4-alpine` | Cache + rate limiting |
| 3 | **Neo4j** | `neo4j:5.26-community` | Graph database |
| 4 | **ChromaDB** | `chromadb/chroma:0.5.23` | Vector database |
| 5 | **SearXNG** | `searxng/searxng:latest` | Meta search engine |
| 6 | **MinIO** | `minio/minio:latest` | S3-compatible storage |
| 7 | **Dozzle** | `amir20/dozzle:latest` | Log viewer |
| — | **Caddy** | Host (system) | TLS reverse proxy — runs on host, not Docker |

### 🔐 Dashboards

| Service | URL | Credentials |
|---------|-----|-------------|
| **Neo4j Browser** | `http://<IP>:7474` | `neo4j` / `changeme` |
| **SearXNG** | `http://<IP>:8080` | No login |
| **MinIO Console** | `http://<IP>:9001` | `minioadmin` / `minioadmin` |
| **Dozzle (Logs)** | `http://<IP>:8081` | No auth |
| **ChromaDB** | `http://<IP>:8000` | No auth |

> ⚠️ Dashboards are internal-only (not exposed through Caddy). Access via SSH tunnel: `ssh -L 7474:localhost:7474 ubuntu@<VM_IP>`

### 🧠 ML Models

Each model is loaded lazily on first request and cached on disk. Set `API_KEY` and `BASE` once (see [QUICKSTART.md](QUICKSTART.md)), then copy-paste any example below.

#### Text embeddings — [`BAAI/bge-small-en-v1.5`](https://huggingface.co/BAAI/bge-small-en-v1.5) · ~130 MB · 384-d
Maps text to a 384-d dense vector. Cosine similarity between two vectors ≈ semantic similarity.

```bash
curl -X POST $BASE/embed \
  -H "Content-Type: application/json" -H "X-API-Key: $API_KEY" \
  -d '{"texts":["python is a programming language","cookies are baked goods"]}'
```

Returns `{ "model": "BAAI/bge-small-en-v1.5", "dimensions": 384, "embeddings": [[…], […]] }`.

#### Vision + language — [`openai/clip-vit-base-patch32`](https://huggingface.co/openai/clip-vit-base-patch32) · ~600 MB · 512-d
Three endpoints share the same 512-d text/image embedding space so text and images can be compared directly.

```bash
# Text → vector
curl -X POST $BASE/clip/text_embedding \
  -H "Content-Type: application/json" -H "X-API-Key: $API_KEY" \
  -d '{"texts":["a cat on a couch","a dog in a field"]}'

# Image → vector (URLs OR base64 strings)
curl -X POST $BASE/clip/image_embedding \
  -H "Content-Type: application/json" -H "X-API-Key: $API_KEY" \
  -d '{"image_urls":["https://upload.wikimedia.org/wikipedia/commons/3/3a/Cat03.jpg"]}'

# Text-vs-images similarity in one shot
curl -X POST $BASE/clip/similarity \
  -H "Content-Type: application/json" -H "X-API-Key: $API_KEY" \
  -d '{"text":"a sunset over the ocean","image_urls":["https://…","https://…"]}'
```

Returns `{ "text": "...", "scores": [0.31, 0.27] }` for similarity (parallel to your `image_urls`).

#### Relevance scoring — [`BAAI/bge-reranker-v2-m3`](https://huggingface.co/BAAI/bge-reranker-v2-m3) · ~1.1 GB
Cross-encoder that scores how relevant a document is to a query (semantic match, not keyword overlap).

```bash
curl -X POST $BASE/rerank \
  -H "Content-Type: application/json" -H "X-API-Key: $API_KEY" \
  -d '{"query":"python programming","documents":["Python is a programming language","Cookies are baked goods","Django is a Python framework"]}'
```

Returns `{ "model": "BAAI/bge-reranker-v2-m3", "query": "…", "results": [{ "index": 0, "document": "…", "score": 0.94 }, …] }`.

#### Speech-to-text — [`faster-whisper`](https://github.com/SYSTRAN/faster-whisper) · `base` · ~150 MB
Auto-falls-back from YouTube subtitles → Whisper when subtitles are missing or forced via `force_whisper:true`.

```bash
# JSON segments (default)
curl -X POST $BASE/youtube/transcript \
  -H "Content-Type: application/json" -H "X-API-Key: $API_KEY" \
  -d '{"url":"https://www.youtube.com/watch?v=dQw4w9WgXcQ"}'

# Pretty markdown for LLM ingestion
curl -X POST "$BASE/youtube/transcript?output_format=markdown" \
  -H "Content-Type: application/json" -H "X-API-Key: $API_KEY" \
  -d '{"url":"https://www.youtube.com/watch?v=dQw4w9WgXcQ"}'
```

Returns `{ "id": "…", "language": "en", "segments": [{ "start": 0, "text": "…" }, …], "source": "youtube_subtitles" | "whisper", "whisper_model": "…" }`.

> ⚡ **Cold start:** models download into `./models/` on first use (~2 GB total). The BGE embedder and CLIP share the same on-disk cache, so subsequent requests are instant after the first call to either.

---

## 📡 API Endpoints

> **Base URL:** `https://aistackapi.duckdns.org`  
> **Swagger:** `https://aistackapi.duckdns.org/docs`

### Public (no auth)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | API info |
| `GET` | `/health/live` | Liveness probe (always 200, no dependency checks) |
| `GET` | `/health` | Readiness checks for all 6 services (503 if any down) |
| `GET` | `/docs` | Interactive Swagger UI |
| `GET` | `/redoc` | Alternative ReDoc UI |
| `GET` | `/openapi.json` | Raw OpenAPI 3 spec |
| `POST` | `/auth/token` | Login — exchange admin credentials for JWT |

### Protected (requires `X-API-Key` or `Authorization: Bearer`)

#### Search & Content

| Method | Path | Description | Fallback chain |
|--------|------|-------------|----------------|
| `POST` | `/search` | Web search | DDGS → SearXNG → Tavily → SerpAPI |
| `POST` | `/news` | News search (with optional article crawling) | DDGS |
| `POST` | `/images` | Image search with optional CLIP reranking | DDGS → Unsplash → Pexels |
| `POST` | `/videos` | Video search | DDGS |
| `POST` | `/crawl` | URL → clean markdown | Scrapling → Trafilatura |
| `POST` | `/browse` | Render a page (full HTML / screenshot / form interaction) | httpx → Playwright |
| `POST` | `/pipeline` | Search → Crawl → Rerank — all in one call | — |
| `POST` | `/pipeline/stream` | Same pipeline, emitted as SSE events | — |

#### ML Models

| Method | Path | Description | Model |
|--------|------|-------------|-------|
| `POST` | `/embed` | Text → dense vectors (384-d) | BAAI/bge-small-en-v1.5 |
| `POST` | `/rerank` | Score documents by relevance to a query | BAAI/bge-reranker-v2-m3 |
| `POST` | `/clip/text_embedding` | CLIP text embedding (512-d) | openai/clip-vit-base-patch32 |
| `POST` | `/clip/image_embedding` | CLIP image embedding (URL or base64 input) | openai/clip-vit-base-patch32 |
| `POST` | `/clip/similarity` | Text-vs-images similarity scores | openai/clip-vit-base-patch32 |
| `POST` | `/youtube/transcript` | Transcript (JSON or markdown) + optional Whisper fallback | youtube_subtitles → faster-whisper |

#### Databases

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/duckdb/query` | Run SQL (DuckDB) |
| `POST` | `/duckdb/insert` | Insert rows into a DuckDB table |
| `GET` | `/duckdb/tables` | List tables and row counts |
| `POST` | `/vector/upsert` | Store vectors in ChromaDB |
| `POST` | `/vector/search` | Search vectors (cosine similarity) |
| `POST` | `/vector/delete` | Delete vectors by ID |
| `POST` | `/graph/query` | Run parameterized Cypher (Neo4j) |
| `POST` | `/graph/add_node` | Add or merge a node |
| `POST` | `/graph/add_edge` | Add an edge between two existing nodes |

#### Storage, Cache & YouTube

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/cache/set` | Store JSON value in Redis (optional TTL) |
| `GET` | `/cache/get/{key}` | Read from Redis |
| `DELETE` | `/cache/delete/{key}` | Delete from Redis |
| `POST` | `/storage/upload` | Upload file to MinIO |
| `POST` | `/storage/list` | List files in a bucket |
| `GET` | `/storage/download/{bucket}/{key}` | Download file from MinIO |
| `POST` | `/storage/delete` | Delete one or many keys |
| `POST` | `/youtube/info` | Video metadata |
| `POST` | `/youtube/thumbnail` | Alias for `/youtube/info` |
| `POST` | `/youtube/download/audio` | Start audio download (returns `job_id`) |
| `POST` | `/youtube/download/video` | Start video download (returns `job_id`) |
| `GET` | `/youtube/jobs/{job_id}` | Poll async download status |

#### Auth Management (JWT-only)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/auth/apikey` | Mint a new API key (custom rate limit / expiry) |
| `DELETE` | `/auth/apikey?key=…` | Revoke an API key |
| `GET` | `/auth/apikeys` | List active API keys (prefix only) |
| `GET` | `/auth/rate-status` | Inspect current rate-limit consumption |

---

## 🔐 Security

| Layer | Protection |
|-------|-----------|
| **TLS** | Caddy auto-HTTPS with Let's Encrypt |
| **Auth** | JWT + API keys (required for all protected endpoints) |
| **Rate limit** | Anonymous: 20 req/min · Authenticated: 300 req/min |
| **Strict mode** | `AUTH_STRICT=true` — anonymous requests get 401 |
| **Headers** | HSTS, nosniff, XSS protection, CSP, Server stripped |
| **Docker** | `read_only: true`, `no-new-privileges`, `cap_drop: ALL` |
| **Secrets** | All credentials in `.env` (gitignored); CI uses GitHub Secrets |

---

## 🤖 CI Pipeline

GitHub Actions runs every **6 hours** via cron:

```yaml
# .github/workflows/ci.yml
on:
  schedule:
    - cron: '0 */6 * * *'
  workflow_dispatch:
```

- Runs `tests/comprehensive.sh` against the live API
- Uses GitHub Secrets for credentials (never exposed)
- Creates an issue automatically on failure

**Required GitHub Secrets:** `API_KEY`, `ADMIN_PASS`

---

## 🔧 Configuration

```bash
cp .env.example .env
# Edit these required values:
#   JWT_SECRET=<openssl rand -hex 32>
#   ADMIN_PASS=<your-strong-password>
```

| Variable | Default | Description |
|----------|---------|-------------|
| `AUTH_STRICT` | `true` | Reject anonymous requests |
| `HEALTH_TIMEOUT` | `3.0` | Per-service readiness timeout in seconds |
| `AUTH_ENABLED` | `true` | Enable authentication |
| `CORS_ORIGINS` | (empty) | Allowed CORS origins |

---

## 🛠️ Common Commands

| Command | Description |
|---------|-------------|
| `make up` | 🚀 Start everything |
| `make down` | ⏹️ Stop everything |
| `make logs` | 📋 Tail all logs |
| `make build` | 🔨 Rebuild app image |
| `make backup` | 💾 Backup Neo4j/ChromaDB/Redis |
| `make restore FILE=./backups/xxx.tar.gz` | ♻️ Restore from backup |
| `make smoke-test` | ✅ Health check all services |
| `make clean` | 🧹 Remove containers + images |
| `docker compose up -d --build app` | Rebuild + restart just the app |
| `bash tests/comprehensive.sh` | Run 40+ API tests |

> 💡 `make` is a shortcut for common `docker compose` operations. See the `Makefile` for all targets.

---

## 🐛 Troubleshooting

| Issue | Fix |
|-------|-----|
| App won't start | `docker logs ai-stack-app` |
| `Permission denied` on data dirs | `sudo chmod -R 777 data/` |
| Embed returns error | Check `./models/` permissions |
| Search returns empty | Check DDGS/SearXNG provider connectivity and logs |
| Crawl returns empty | Check the target URL and browser availability |
| `/health` is degraded | Use `/health/live` for liveness; inspect the readiness service statuses |
| Playwright browsers crash | Known Docker limitation — browse uses fast HTTP fallback |

---

## 💻 Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| RAM | 4 GB | 8 GB |
| CPU | 2 cores | 4 cores |
| Disk | 30 GB | 100 GB |
| Swap | 4 GB | 8 GB |
| Docker | 24.0+ | 27.0+ |

---

## 📄 License

MIT
