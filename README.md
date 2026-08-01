<div align="center">

# 🧠 AI Infrastructure Stack

### *Production-ready, self-hosted AI infrastructure — one API to rule them all*

[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker&logoColor=white)](https://docker.com)
[![CI](https://img.shields.io/badge/CI-GitHub_Actions-2088FF?style=flat-square&logo=githubactions&logoColor=white)](.github/workflows/ci.yml)

```
🌐 Internet → 🔒 Caddy (TLS) → ⚡ FastAPI → 🐳 8 Docker Services
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

### 🧠 ML Models (loaded on first use)

| Model | Size | Endpoint |
|-------|------|----------|
| BAAI/bge-small-en-v1.5 | ~130MB | `/embed` |
| openai/clip-vit-base-patch32 | ~600MB | `/clip` |
| BAAI/bge-reranker-v2-m3 | ~1.1GB | `/rerank` |
| faster-whisper base | ~150MB | `/youtube/transcript` |

---

## 📡 API Endpoints

> **Base URL:** `https://aistackapi.duckdns.org`  
> **Swagger:** `https://aistackapi.duckdns.org/docs`

### Public (no auth)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | API info |
| `GET` | `/health/live` | Liveness probe (no dependency checks) |
| `GET` | `/health` | Readiness checks for all 6 services |
| `GET` | `/docs` | Interactive Swagger UI |
| `POST` | `/auth/token` | Login — get JWT token |

### Protected (requires `X-API-Key` or `Authorization: Bearer`)

| Method | Path | Description | Fallback |
|--------|------|-------------|----------|
| `POST` | `/search` | Web search | DDGS → SearXNG → Tavily → SerpAPI |
| `POST` | `/crawl` | URL → markdown | Safe HTTP → Playwright fallback |
| `POST` | `/browse` | Render a page | httpx (fast) |
| `POST` | `/embed` | Text → vectors | — |
| `POST` | `/rerank` | Score documents by relevance | — |
| `POST` | `/cache/set` | Store in Redis | — |
| `GET` | `/cache/get/{key}` | Read from Redis | — |
| `DELETE` | `/cache/delete/{key}` | Delete from Redis | — |
| `POST` | `/graph/query` | Run Cypher (Neo4j) | — |
| `POST` | `/graph/add_node` | Add node | — |
| `POST` | `/graph/add_edge` | Add edge | — |
| `POST` | `/vector/upsert` | Store vectors (ChromaDB) | — |
| `POST` | `/vector/search` | Search vectors | — |
| `POST` | `/vector/delete` | Delete vectors | — |
| `POST` | `/duckdb/query` | Run SQL (DuckDB) | — |
| `GET` | `/duckdb/tables` | List tables | — |
| `POST` | `/youtube/info` | Video metadata | — |
| `POST` | `/youtube/transcript` | Get transcript | Subtitles → Whisper |
| `POST` | `/youtube/download/audio` | Download audio | — |
| `POST` | `/clip/text_embedding` | CLIP text embedding | — |
| `POST` | `/storage/upload` | Upload file (MinIO) | — |
| `POST` | `/storage/list` | List files | — |
| `GET` | `/storage/download/{bucket}/{key}` | Download file | — |
| `POST` | `/pipeline` | Search → Crawl → Rerank | All-in-one |
| `POST` | `/pipeline/stream` | Pipeline (SSE streaming) | — |

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

### 🧠 ML Models (loaded on first use)

| Model | Size | Endpoint |
|-------|------|----------|
| BAAI/bge-small-en-v1.5 | ~130MB | `/embed` |
| openai/clip-vit-base-patch32 | ~600MB | `/clip` |
| BAAI/bge-reranker-v2-m3 | ~1.1GB | `/rerank` |
| faster-whisper base | ~150MB | `/youtube/transcript` |

Models are cached in `./models/` and shared across container restarts. The first request to each endpoint downloads the model (~2GB total); subsequent requests are instant.

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
