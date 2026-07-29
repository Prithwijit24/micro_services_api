<div align="center">

# 🧠 AI Infrastructure Stack

### *Production-ready, self-hosted AI infrastructure — one API to rule them all*

[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker&logoColor=white)](https://docker.com)
[![License](https://img.shields.io/badge/License-MIT-blue?style=flat-square)](LICENSE)

```
🌐 Internet → 🔒 Caddy (TLS) → ⚡ FastAPI App → 🐳 11 Docker Services
```

</div>

---

## 📋 Table of Contents

<details>
<summary><strong>🏗️ Architecture & Services</strong></summary>

- [Architecture Overview](#-architecture-overview)
- [Service Map](#-service-map)
- [Repository Layout](#-repository-layout)
</details>

<details>
<summary><strong>🚀 Quick Start</strong></summary>

- [Local Development](#-local-development)
- [Oracle Cloud VM Deployment](#-oracle-cloud-vm-deployment)
- [Get Your Public URL](#-get-your-public-url)
</details>

<details>
<summary><strong>📡 API Reference</strong></summary>

- [All Endpoints](#-api-endpoints)
- [Code Snippets](#-code-snippets)
- [Jupyter Notebook](#-jupyter-notebook)
</details>

<details>
<summary><strong>🛠️ Operations</strong></summary>

- [Common Commands](#-common-commands)
- [Logins & Dashboards](#-logins--dashboards)
- [Backup & Restore](#-backup--restore)
- [Troubleshooting](#-troubleshooting)
</details>

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        🌐 INTERNET                                  │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │   🔒 CADDY (TLS)    │  Port 80/443
                    │   Reverse Proxy     │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │  ⚡ FASTAPI APP      │  Port 8000 (internal)
                    │  Single Container   │
                    │  15 routers         │
                    │  30+ endpoints      │
                    └──────────┬──────────┘
                               │
        ┌──────────┬───────────┼───────────┬──────────┐
        │          │           │           │          │
   ┌────▼────┐ ┌───▼───┐ ┌────▼────┐ ┌────▼────┐ ┌───▼───┐
   │ 🔍 SearXNG│ │ 🕷️ Scrapling│ │ 🤖 Obscura │ │ 📊 Neo4j │ │ 💾 MySQL │
   │ Search   │ │ Crawl │ │ Browser │ │  Graph  │ │   DB  │
   └─────────┘ └───────┘ └─────────┘ └─────────┘ └───────┘
        │          │           │           │          │
   ┌────▼────┐ ┌───▼───┐ ┌────▼────┐ ┌────▼────┐ ┌───▼───┐
   │ 🧬 ChromaDB│ │ 🔎 Qdrant │ │ 🧠 Embed  │ │ 🎯 CLIP │ │ 🔄 Rerank│
   │ Vectors │ │Vectors│ │ BGE     │ │  VLM   │ │ BGE   │
   └─────────┘ └───────┘ └─────────┘ └─────────┘ └───────┘
        │          │           │           │          │
   ┌────▼────┐ ┌───▼───┐ ┌────▼────┐ ┌────▼────┐ ┌───▼───┐
   │ 🗄️ Redis │ │ 🎬 YouTube│ │ 📁 MinIO │ │ 📈 DuckDB│ │ 🎤 Whisper│
   │ Cache   │ │ yt-dlp │ │ S3 Store│ │ OLAP   │ │  STT  │
   └─────────┘ └───────┘ └─────────┘ └─────────┘ └───────┘
```

### 🐳 Docker Services (12 containers)

| # | Service | Image | Port | Purpose | Status |
|---|---------|-------|------|---------|--------|
| 1 | **App** | Custom build | 8000 | FastAPI application (all capabilities) | ✅ |
| 2 | **Caddy** | `caddy:2.9-alpine` | 80/443 | Reverse proxy + auto HTTPS | ✅ |
| 3 | **Redis** | `redis:7.4-alpine` | 6379 | Cache + message broker | ✅ |
| 4 | **Neo4j** | `neo4j:5.26-community` | 7474/7687 | Graph database | ✅ |
| 5 | **ChromaDB** | `chromadb/chroma:0.5.23` | 8000 | Vector database | ✅ |
| 6 | **SearXNG** | `searxng/searxng:latest` | 8080 | Meta search engine | ✅ |
| 7 | **Qdrant** | `qdrant/qdrant:v1.12.4` | 6333/6334 | Vector database (alternative) | ✅ |
| 8 | **MinIO** | `minio/minio:latest` | 9000/9001 | S3-compatible file storage | ✅ |
| 9 | **MySQL** | `mysql:8.4` | 3306 | Relational database | ✅ |
| 10 | **Obscura** | `h4ckf0r0day/obscura:latest` | 9222 | Headless Chromium (CDP) | ✅ |
| 11 | **Uptime Kuma** | `louislam/uptime-kuma:1` | 3001 | Monitoring dashboard | ✅ |
| 12 | **Dozzle** | `amir20/dozzle:latest` | 8081 | Log viewer | ✅ |

---

## 📁 Repository Layout

```
ai-infra-stack/
├── 🐳 docker-compose.yml          # Full stack definition (12 services)
├── 🔧 Makefile                    # up/down/backup/restore targets
├── 🔐 .env.example                # Copy to .env and fill in secrets
├── 📄 Dockerfile                  # Python 3.12 + Playwright + uv
│
├── 📂 app/
│   ├── main.py                    # FastAPI entry point
│   ├── models.py                  # All Pydantic request/response models
│   ├── deps.py                    # Dependency injection
│   ├── routers/                   # 15 API routers
│   │   ├── search.py              # 🔍 Web search via SearXNG
│   │   ├── crawl.py               # 🕷️ URL → Markdown (Scrapling/Trafilatura)
│   │   ├── browse.py              # 🤖 Browser automation (Obscura/Playwright)
│   │   ├── youtube.py             # 🎬 YouTube search/download/transcript
│   │   ├── embed.py               # 🧠 Text embeddings (BAAI/bge-small-en-v1.5)
│   │   ├── clip.py                # 🎯 Image embeddings (CLIP)
│   │   ├── reranker.py            # 🔄 Search result reranking
│   │   ├── graph.py               # 📊 Neo4j graph operations
│   │   ├── vector.py              # 🧬 ChromaDB vector operations
│   │   ├── qdrant.py              # 🔎 Qdrant vector operations
│   │   ├── cache.py               # 🗄️ Redis cache operations
│   │   ├── mysql.py               # 💾 MySQL operations
│   │   ├── duckdb.py              # 📈 DuckDB OLAP queries
│   │   ├── storage.py             # 📁 MinIO file storage
│   │   └── pipeline.py            # 🔗 Search→Crawl→Rerank pipeline
│   └── services/                  # Business logic (one per router)
│
├── 📂 caddy/
│   └── Caddyfile                  # Reverse proxy config
├── 📂 scripts/
│   ├── backup.sh                  # Backup Neo4j/ChromaDB/Redis
│   ├── restore.sh                 # Restore from backup
│   └── smoke_test.sh              # Health check script
├── 📂 tests/
│   └── test_smoke.py              # Local smoke tests
├── 📂 data/                       # Persistent data (gitignored)
├── 📂 models/                     # HuggingFace model cache (gitignored)
└── 📂 backups/                    # Backup archives (gitignored)
```

---

## 🚀 Quick Start

### 💻 Local Development

```bash
# 1️⃣ Clone the repo
git clone <your-repo-url> ai-infra-stack
cd ai-infra-stack

# 2️⃣ Configure environment
cp .env.example .env
# Edit .env with your passwords and settings

# 3️⃣ Start everything
make up

# 4️⃣ Verify it works
make smoke-test
# or
curl http://localhost/health
# → {"status":"ok"}
```

### ☁️ Oracle Cloud VM Deployment

```bash
# 1️⃣ SSH into your Oracle VM
ssh -i ~/.ssh/your_key.pem ubuntu@<VM_PUBLIC_IP>

# 2️⃣ Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# Log out and back in for group changes

# 3️⃣ Clone and configure
git clone <your-repo-url> ai-infra-stack
cd ai-infra-stack
cp .env.example .env

# 4️⃣ Edit .env — set REAL passwords!
nano .env

# 5️⃣ Start the stack
make up

# 6️⃣ Verify
curl http://localhost/health
# → {"status":"ok"}
```

### 🌐 Get Your Public URL

**Option A: Direct IP access (quickest)**
```
http://<YOUR_VM_PUBLIC_IP>
```

**Option B: Domain with free HTTPS (recommended)**
1. Point your domain's DNS A record to `<YOUR_VM_PUBLIC_IP>`
2. Edit `.env`:
   ```bash
   DOMAIN=yourdomain.com
   CADDY_ACME_EMAIL=you@email.com
   ```
3. Restart Caddy: `make restart`
4. Your API is now at `https://yourdomain.com`

**Option C: Open specific ports in Oracle Cloud**
Go to **Oracle Cloud Console → Networking → Virtual Cloud Networks → Security Lists** and add:

| Port | Protocol | Purpose | When to open |
|------|----------|---------|--------------|
| 80 | TCP | HTTP (Caddy) | ✅ Always |
| 443 | TCP | HTTPS (Caddy) | ✅ If using domain |
| 7474 | TCP | Neo4j Browser | Only if you need graph UI |
| 9001 | TCP | MinIO Console | Only if you need file storage UI |
| 3001 | TCP | Uptime Kuma | Only if you need monitoring UI |

> ⚠️ **Security**: Only open ports you actually need. The API itself only requires port 80/443.

---

## 📡 API Endpoints

### 🔍 Search — `POST /search`

```bash
curl -X POST http://localhost/search \
  -H "Content-Type: application/json" \
  -d '{"query": "latest AI research papers", "max_results": 5}'
```

**Response:**
```json
{
  "query": "latest AI research papers",
  "number_of_results": 5,
  "results": [
    {
      "title": "AI Research Papers 2026",
      "url": "https://arxiv.org/...",
      "content": "Summary of the paper...",
      "engine": "google"
    }
  ]
}
```

**Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `query` | string | *required* | Search query |
| `categories` | string | `"general"` | Search category |
| `language` | string | `"en"` | Language code |
| `max_results` | int | `10` | Max results (1-50) |
| `safesearch` | int | `1` | Safe search (0-2) |

---

### 🕷️ Crawl — `POST /crawl`

```bash
curl -X POST http://localhost/crawl \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "only_main_content": true}'
```

**Response:**
```json
{
  "url": "https://example.com",
  "markdown": "# Example Domain\n\nThis domain is for use in...",
  "html": null,
  "title": "Example Domain",
  "status_code": 200
}
```

**Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `url` | string | *required* | URL to crawl |
| `only_main_content` | bool | `true` | Extract main content only |
| `include_html` | bool | `false` | Include raw HTML |
| `timeout_ms` | int | `30000` | Timeout (1000-120000) |

---

### 🤖 Browse — `POST /browse`

```bash
curl -X POST http://localhost/browse \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "action": "content"}'
```

**Actions:** `content` | `screenshot` | `click` | `fill_form`

---

### 🎬 YouTube — `POST /youtube/*`

```bash
# 🔍 Search videos
curl -X POST http://localhost/youtube/search \
  -H "Content-Type: application/json" \
  -d '{"query": "Python tutorial", "max_results": 5}'

# ℹ️ Get video info
curl -X POST http://localhost/youtube/info \
  -H "Content-Type: application/json" \
  -d '{"url": "https://youtube.com/watch?v=dQw4w9WgXcQ"}'

# ⬇️ Download audio (async job)
curl -X POST http://localhost/youtube/download/audio \
  -H "Content-Type: application/json" \
  -d '{"url": "https://youtube.com/watch?v=dQw4w9WgXcQ"}'
# → {"job_id": "abc123", "status": "queued", ...}

# 📊 Check job status
curl http://localhost/youtube/jobs/abc123
# → {"job_id": "abc123", "status": "done", "result_path": "/opt/data/youtube/abc123.mp3"}

# 📝 Get transcript (JSON or Markdown)
curl -X POST "http://localhost/youtube/transcript?output_format=markdown" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://youtube.com/watch?v=dQw4w9WgXcQ"}'
# Returns formatted markdown with timestamps

# 🖼️ Get thumbnail
curl -X POST http://localhost/youtube/thumbnail \
  -H "Content-Type: application/json" \
  -d '{"url": "https://youtube.com/watch?v=dQw4w9WgXcQ"}'
```

---

### 🧠 Embed — `POST /embed`

```bash
curl -X POST http://localhost/embed \
  -H "Content-Type: application/json" \
  -d '{"texts": ["Hello world", "AI is amazing"]}'
```

**Response:**
```json
{
  "model": "BAAI/bge-small-en-v1.5",
  "dimensions": 384,
  "embeddings": [[0.023, -0.041, ...], [0.018, -0.035, ...]]
}
```

---

### 🎯 CLIP — `POST /clip/*`

```bash
# Text embedding
curl -X POST http://localhost/clip/text_embedding \
  -H "Content-Type: application/json" \
  -d '{"texts": ["a photo of a cat"]}'

# Image embedding
curl -X POST http://localhost/clip/image_embedding \
  -H "Content-Type: application/json" \
  -d '{"image_urls": ["https://example.com/cat.jpg"]}'

# Similarity search
curl -X POST http://localhost/clip/similarity \
  -H "Content-Type: application/json" \
  -d '{"text": "a cat", "image_urls": ["https://example.com/cat.jpg"]}'
```

---

### 🔄 Rerank — `POST /rerank`

```bash
curl -X POST http://localhost/rerank \
  -H "Content-Type: application/json" \
  -d '{
    "query": "machine learning",
    "documents": [
      "Deep learning is a subset of ML",
      "Cooking pasta al dente",
      "Neural networks are inspired by brains"
    ],
    "top_k": 2
  }'
```

**Response:**
```json
{
  "model": "BAAI/bge-reranker-v2-m3",
  "query": "machine learning",
  "results": [
    {"index": 0, "document": "Deep learning is a subset of ML", "score": 0.95},
    {"index": 2, "document": "Neural networks are inspired by brains", "score": 0.87}
  ]
}
```

---

### 📊 Graph (Neo4j) — `POST /graph/*`

```bash
# ➕ Add a node
curl -X POST http://localhost/graph/add_node \
  -H "Content-Type: application/json" \
  -d '{"label": "Person", "properties": {"name": "Alice", "age": 30}}'
# → {"node_id": "abc123", "label": "Person", "properties": {"name": "Alice", "age": 30}}

# 🔗 Add an edge
curl -X POST http://localhost/graph/add_edge \
  -H "Content-Type: application/json" \
  -d '{
    "from_label": "Person", "from_key": "name", "from_value": "Alice",
    "to_label": "Person", "to_key": "name", "to_value": "Bob",
    "relationship": "KNOWS"
  }'
# → {"relationship": "KNOWS", "from_node": {...}, "to_node": {...}}

# 🔍 Run Cypher query
curl -X POST http://localhost/graph/query \
  -H "Content-Type: application/json" \
  -d '{"cypher": "MATCH (n:Person) RETURN n LIMIT 10"}'
# → {"records": [{...}, ...], "count": 2}
```

---

### 🧬 Vector (ChromaDB) — `POST /vector/*`

```bash
# ➕ Upsert vectors
curl -X POST http://localhost/vector/upsert \
  -H "Content-Type: application/json" \
  -d '{
    "collection": "docs",
    "records": [
      {"id": "1", "embedding": [0.1, 0.2, ...], "document": "AI is great", "metadata": {"source": "web"}}
    ]
  }'
# → {"collection": "docs", "upserted": 1}

# 🔍 Search vectors
curl -X POST http://localhost/vector/search \
  -H "Content-Type: application/json" \
  -d '{"collection": "docs", "query_embedding": [0.1, 0.2, ...], "top_k": 5}'
# → {"collection": "docs", "matches": [{"id": "1", "score": 0.95, ...}]}

# 🗑️ Delete vectors
curl -X POST http://localhost/vector/delete \
  -H "Content-Type: application/json" \
  -d '{"collection": "docs", "ids": ["1"]}'
# → {"collection": "docs", "deleted": 1}
```

### 🔎 Qdrant — `POST /qdrant/*`

```bash
# Create a collection
curl -X POST http://localhost/qdrant/collections \
  -H "Content-Type: application/json" \
  -d '{"collection": "docs", "dimensions": 384, "distance": "Cosine"}'

# List collections
curl http://localhost/qdrant/collections

# Upsert, search, delete — same API shape as ChromaDB vector endpoints
```

---

### 🗄️ Cache (Redis) — `POST /cache/*`

```bash
# Set a value
curl -X POST http://localhost/cache/set \
  -H "Content-Type: application/json" \
  -d '{"key": "user:123", "value": {"name": "Alice"}, "ttl_seconds": 3600}'

# Get a value
curl http://localhost/cache/get/user:123

# Delete a value
curl -X DELETE http://localhost/cache/delete/user:123
```

---

### 💾 MySQL — `POST /mysql/*`

```bash
# Run a query
curl -X POST http://localhost/mysql/query \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT * FROM users LIMIT 10"}'

# Insert data
curl -X POST http://localhost/mysql/insert \
  -H "Content-Type: application/json" \
  -d '{"table": "users", "columns": ["name", "email"], "rows": [{"name": "Alice", "email": "alice@example.com"}]}'

# List tables
curl -X POST http://localhost/mysql/tables
```

---

### 📈 DuckDB — `POST /duckdb/*`

```bash
# Run OLAP query
curl -X POST http://localhost/duckdb/query \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT category, COUNT(*) as cnt FROM sales GROUP BY category ORDER BY cnt DESC"}'

# Insert data
curl -X POST http://localhost/duckdb/insert \
  -H "Content-Type: application/json" \
  -d '{"table": "sales", "columns": ["product", "amount"], "rows": [{"product": "Widget", "amount": 29.99}]}'
```

---

### 📁 Storage (MinIO) — `POST /storage/*`

```bash
# ⬆️ Upload a file
curl -X POST http://localhost/storage/upload \
  -F "key=documents/report.pdf" \
  -F "file=@./report.pdf"
# → {"bucket": "ai-stack", "key": "documents/report.pdf", "size": 1024, "url": "..."}

# ⬇️ Download a file
curl -o report.pdf http://localhost/storage/download/ai-stack/documents/report.pdf

# 📋 List files
curl -X POST http://localhost/storage/list \
  -H "Content-Type: application/json" \
  -d '{"prefix": "documents/"}'
# → {"bucket": "ai-stack", "files": [{"key": "documents/report.pdf", "size": 1024}], "count": 1}

# 🗑️ Delete files
curl -X POST http://localhost/storage/delete \
  -H "Content-Type: application/json" \
  -d '{"keys": ["documents/report.pdf"]}'
# → {"bucket": "ai-stack", "deleted": 1}
```

---

### 🔗 Pipeline — `POST /pipeline` & `POST /pipeline/stream`

The pipeline combines **Search → Crawl → Markdown → Rerank** in a single call:

```bash
# Standard (waits for all results)
curl -X POST http://localhost/pipeline \
  -H "Content-Type: application/json" \
  -d '{"query": "what is the current weather of kolkata?", "top_k": 5}'

# Streaming (SSE — results arrive as they're crawled)
curl -N -X POST http://localhost/pipeline/stream \
  -H "Content-Type: application/json" \
  -d '{"query": "best Python frameworks 2026", "top_k": 5}'
```

**Streaming Events (SSE format):**
```
event: search
data: {"total_results": 15, "timings": {"search": 1.2}}

event: crawl_start
data: {"url": "https://docs.python.org/3/asyncio.html"}

event: crawl_result
data: {"url": "https://docs.python.org/3/asyncio.html", "title": "asyncio — Asynchronous I/O", "chars": 3421, "markdown": "# asyncio\n\nThe asyncio module..."}

event: crawl_error
data: {"url": "https://example.com", "error": "Timeout after 15s"}

event: rerank
data: {"ranked": 5, "timings": {"rerank": 0.3}}

event: result
data: {"rank": 1, "url": "https://...", "title": "...", "score": 0.95, "markdown": "# asyncio\n\nThe asyncio module...", "is_youtube": false}

event: done
data: {"total_searched": 15, "total_crawled": 10, "timings": {"search": 1.2, "crawl": 8.5, "rerank": 0.3}}
```

---

## 🧪 Jupyter Notebook

A complete notebook is included at `testing_notebook.ipynb` with examples for every endpoint.

### Quick Example

```python
import httpx

BASE = "http://localhost"

# 🔍 Search
r = httpx.post(f"{BASE}/search", json={"query": "Python asyncio", "max_results": 3})
print(f"Found {r.json()['number_of_results']} results")

# 🕷️ Crawl → Markdown
r = httpx.post(f"{BASE}/crawl", json={"url": "https://docs.python.org/3/library/asyncio.html"})
print(r.json()["markdown"][:200])

# 🧠 Embed
r = httpx.post(f"{BASE}/embed", json={"texts": ["machine learning", "deep learning"]})
print(f"Dimensions: {r.json()['dimensions']}")

# 🔄 Rerank
r = httpx.post(f"{BASE}/rerank", json={
    "query": "neural networks",
    "documents": ["Deep learning uses neural nets", "Cooking recipes", "Brain-inspired computing"]
})
for doc in r.json()["results"]:
    print(f"  {doc['score']:.2f} — {doc['document'][:50]}")

# 🔗 Full Pipeline
r = httpx.post(f"{BASE}/pipeline", json={"query": "what is quantum computing?", "top_k": 3})
for item in r.json()["results"]:
    print(f"  {item['score']:.2f} — {item['title'][:60]}")
    print(f"  {item['markdown'][:100]}...")
```

---

## 🛠️ Common Commands

| Command | Description |
|---------|-------------|
| `make up` | 🚀 Start everything |
| `make up redis` | 🚀 Start only Redis |
| `make down` | ⏹️ Stop everything |
| `make restart` | 🔄 Restart all containers |
| `make logs` | 📋 Tail all logs |
| `make ps` | 📊 Container status |
| `make build` | 🔨 Rebuild app image |
| `make update` | ⬆️ Pull latest images + rebuild |
| `make backup` | 💾 Backup Neo4j/ChromaDB/Redis |
| `make restore FILE=./backups/xxx.tar.gz` | ♻️ Restore from backup |
| `make smoke-test` | ✅ Health check all services |
| `make clean` | 🧹 Remove containers + dangling images |

---

## 🔐 Logins & Dashboards

| Service | URL | Credentials |
|---------|-----|-------------|
| **Neo4j Browser** | `http://<IP>:7474` | `neo4j` / `changeme` |
| **SearXNG** | `http://<IP>:8080` | No login needed |
| **MinIO Console** | `http://<IP>:9001` | `minioadmin` / `minioadmin` |
| **Uptime Kuma** | `http://<IP>:3001` | First-time setup wizard |
| **Dozzle (Logs)** | `http://<IP>:8081` | No auth |
| **ChromaDB** | `http://<IP>:8000` | No auth |
| **Qdrant** | `http://<IP>:6333` | No auth |

> 💡 **Tip**: In Oracle VM, only expose ports you actually need via Security Lists.

---

## 💾 Backup & Restore

```bash
# Backup all databases
make backup
# Creates: ./backups/aistack_backup_YYYYMMDD_HHMMSS.tar.gz

# Restore from backup
make restore FILE=./backups/aistack_backup_20260730_120000.tar.gz
```

**What's backed up:**
- 📊 Neo4j graph data
- 🧬 ChromaDB vector data
- 🗄️ Redis RDB snapshot

---

## 🔧 Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection URL |
| `NEO4J_USER` | `neo4j` | Neo4j username |
| `NEO4J_PASSWORD` | `changeme` | Neo4j password |
| `SEARXNG_URL` | `http://searxng:8080` | SearXNG internal URL |
| `OBSCURA_CDP_URL` | `http://obscura:9222` | Obscura CDP endpoint |
| `EMBED_MODEL` | `BAAI/bge-small-en-v1.5` | Embedding model |
| `CLIP_MODEL` | `openai/clip-vit-base-patch32` | CLIP model |
| `RERANK_MODEL` | `BAAI/bge-reranker-v2-m3` | Reranker model |
| `WHISPER_MODEL` | `base` | Whisper STT model |
| `USE_PROXIES` | `false` | Enable free proxy routing |
| `DOMAIN` | `localhost` | Your domain for HTTPS |

### 🔄 Model Cache

Models are cached in `./models/` and shared across containers:
- **First run**: Downloads ~500MB of models
- **Subsequent runs**: Instant (loaded from cache)
- **Models**: BGE embeddings, CLIP, BGE reranker, Whisper

---

## 💻 Resource Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| **RAM** | 8 GB | 16 GB |
| **CPU** | 4 cores | 8 cores |
| **Disk** | 50 GB | 100 GB |
| **Docker** | 20.10+ | Latest |

> ⚠️ **First run** downloads ~500MB of AI models (BGE, CLIP, Reranker, Whisper). Subsequent runs use the cached models in `./models/`.

> ⚠️ **Playwright browsers** (Firefox + Chromium) are baked into the app image. The Docker build takes ~5-10 minutes.

---

## 🐛 Troubleshooting

| Issue | Fix |
|-------|-----|
| Container won't start | `docker logs ai-stack-<service>` |
| Port already in use | `lsof -i :<port>` to find culprit |
| Out of memory | Increase Docker memory limit to 8GB+ |
| Model download fails | Check internet connection, retry |
| Obscura image pull fails | Remove `obscura` from docker-compose.yml |
| SearXNG warnings | Harmless — search still works |
| `data/` permission errors | `sudo chmod -R 777 data/` |
| App won't build | `make clean && make up` |
| Pipeline timeout | Increase `crawl_timeout_ms` in request |

---

## 🤝 Contributing

1. Fork the repo
2. Create a feature branch
3. Make your changes
4. Run `make smoke-test`
5. Submit a PR

---

## 📄 License

MIT — use freely in your projects.

---

<div align="center">

### ⭐ Star this repo if you find it useful!

**Built with ❤️ using FastAPI, Docker, and open-source AI models**

</div>
