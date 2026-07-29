<div align="center">

# 🧠 AI Infrastructure Stack

### *Production-ready, self-hosted AI infrastructure — one API to rule them all*

[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker&logoColor=white)](https://docker.com)

```
🌐 Internet → 🔒 Caddy (TLS) → ⚡ FastAPI App → 🐳 8 Docker Services
```

</div>

---

## 📋 Table of Contents

- [Architecture Overview](#-architecture-overview)
- [Quick Start](#-quick-start)
- [API Reference](#-api-endpoints)
- [Common Commands](#-common-commands)
- [Configuration](#-configuration)
- [Troubleshooting](#-troubleshooting)

---

## 🏗️ Architecture Overview

```
┌──────────────────────────────────────────────────────────┐
│                     🌐 INTERNET                           │
└─────────────────────────┬────────────────────────────────┘
                          │
               ┌──────────▼──────────┐
               │   🔒 CADDY (TLS)    │  Port 80/443
               │   Reverse Proxy     │
               └──────────┬──────────┘
                          │
               ┌──────────▼──────────┐
               │  ⚡ FASTAPI APP      │  Port 8000 (internal)
               │  Single Container   │
               │  13 routers         │
               │  30+ endpoints      │
               └──────────┬──────────┘
                          │
     ┌────────┬───────────┼───────────┬────────┐
     │        │           │           │        │
┌────▼───┐ ┌──▼────┐ ┌────▼────┐ ┌───▼───┐ ┌──▼─────┐
│🔍SearXNG│ │🧬Chroma│ │📊Neo4j │ │🗄️Redis│ │📁MinIO │
│ Search │ │Vector │ │ Graph  │ │ Cache │ │  S3   │
└────────┘ └───────┘ └────────┘ └───────┘ └───────┘
```

### 🐳 Docker Services (8 containers)

| # | Service | Image | Port | Purpose |
|---|---------|-------|------|---------|
| 1 | **App** | Custom build | 8000 | FastAPI application (all capabilities) |
| 2 | **Caddy** | `caddy:2.9-alpine` | 80/443 | Reverse proxy + auto HTTPS |
| 3 | **Redis** | `redis:7.4-alpine` | 6379 | Cache + message broker |
| 4 | **Neo4j** | `neo4j:5.26-community` | 7474/7687 | Graph database |
| 5 | **ChromaDB** | `chromadb/chroma:0.5.23` | 8000 | Vector database |
| 6 | **SearXNG** | `searxng/searxng:latest` | 8080 | Meta search engine |
| 7 | **MinIO** | `minio/minio:latest` | 9000/9001 | S3-compatible file storage |
| 8 | **Dozzle** | `amir20/dozzle:latest` | 8081 | Log viewer |

### 🧠 ML Models (loaded on-demand)

| Model | Size | Used By |
|-------|------|---------|
| BAAI/bge-small-en-v1.5 | ~130MB | `/embed` |
| openai/clip-vit-base-patch32 | ~600MB | `/clip` |
| BAAI/bge-reranker-v2-m3 | ~1.1GB | `/rerank` |
| faster-whisper base | ~150MB | `/youtube/transcript` |

---

## 🚀 Quick Start

```bash
# 1️⃣ Clone the repo
git clone <your-repo-url> ai-infra-stack
cd ai-infra-stack

# 2️⃣ Configure environment
cp .env.example .env
# Edit .env with your passwords

# 3️⃣ Start everything
make up

# 4️⃣ Verify
curl http://localhost/health
# → {"status":"ok"}
```

---

## 📡 API Endpoints

### 🔍 Search — `POST /search`

```bash
curl -X POST http://localhost/search \
  -H "Content-Type: application/json" \
  -d '{"query": "latest AI research", "max_results": 5}'
```

### 🕷️ Crawl — `POST /crawl`

```bash
curl -X POST http://localhost/crawl \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "only_main_content": true}'
```

### 🤖 Browse — `POST /browse`

```bash
curl -X POST http://localhost/browse \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "action": "content"}'
```

**Actions:** `content` | `screenshot` | `click` | `fill_form`

### 🎬 YouTube — `POST /youtube/*`

```bash
# Search videos
curl -X POST http://localhost/youtube/search \
  -H "Content-Type: application/json" \
  -d '{"query": "Python tutorial", "max_results": 5}'

# Get video info
curl -X POST http://localhost/youtube/info \
  -H "Content-Type: application/json" \
  -d '{"url": "https://youtube.com/watch?v=dQw4w9WgXcQ"}'

# Download audio (async job)
curl -X POST http://localhost/youtube/download/audio \
  -H "Content-Type: application/json" \
  -d '{"url": "https://youtube.com/watch?v=dQw4w9WgXcQ"}'

# Get transcript (JSON or Markdown)
curl -X POST "http://localhost/youtube/transcript?output_format=markdown" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://youtube.com/watch?v=dQw4w9WgXcQ"}'

# Get thumbnail
curl -X POST http://localhost/youtube/thumbnail \
  -H "Content-Type: application/json" \
  -d '{"url": "https://youtube.com/watch?v=dQw4w9WgXcQ"}'
```

### 🧠 Embed — `POST /embed`

```bash
curl -X POST http://localhost/embed \
  -H "Content-Type: application/json" \
  -d '{"texts": ["Hello world", "AI is amazing"]}'
```

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

### 🔄 Rerank — `POST /rerank`

```bash
curl -X POST http://localhost/rerank \
  -H "Content-Type: application/json" \
  -d '{
    "query": "machine learning",
    "documents": ["Deep learning is a subset of ML", "Cooking pasta", "Neural networks"],
    "top_k": 2
  }'
```

### 📊 Graph (Neo4j) — `POST /graph/*`

```bash
# Add a node
curl -X POST http://localhost/graph/add_node \
  -H "Content-Type: application/json" \
  -d '{"label": "Person", "properties": {"name": "Alice"}}'

# Add an edge
curl -X POST http://localhost/graph/add_edge \
  -H "Content-Type: application/json" \
  -d '{
    "from_label": "Person", "from_key": "name", "from_value": "Alice",
    "to_label": "Person", "to_key": "name", "to_value": "Bob",
    "relationship": "KNOWS"
  }'

# Run Cypher query
curl -X POST http://localhost/graph/query \
  -H "Content-Type: application/json" \
  -d '{"cypher": "MATCH (n:Person) RETURN n LIMIT 10"}'
```

### 🧬 Vector (ChromaDB) — `POST /vector/*`

```bash
# Upsert vectors
curl -X POST http://localhost/vector/upsert \
  -H "Content-Type: application/json" \
  -d '{
    "collection": "docs",
    "records": [{"id": "1", "embedding": [0.1, 0.2], "document": "AI is great", "metadata": {}}]
  }'

# Search vectors
curl -X POST http://localhost/vector/search \
  -H "Content-Type: application/json" \
  -d '{"collection": "docs", "query_embedding": [0.1, 0.2], "top_k": 5}'

# Delete vectors
curl -X POST http://localhost/vector/delete \
  -H "Content-Type: application/json" \
  -d '{"collection": "docs", "ids": ["1"]}'
```

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

### 📈 DuckDB — `POST /duckdb/*`

```bash
# Run OLAP query
curl -X POST http://localhost/duckdb/query \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT category, COUNT(*) as cnt FROM sales GROUP BY category"}'

# Insert data
curl -X POST http://localhost/duckdb/insert \
  -H "Content-Type: application/json" \
  -d '{"table": "sales", "columns": ["product", "amount"], "rows": [{"product": "Widget", "amount": 29.99}]}'
```

### 📁 Storage (MinIO) — `POST /storage/*`

```bash
# Upload a file
curl -X POST http://localhost/storage/upload \
  -F "key=documents/report.pdf" \
  -F "file=@./report.pdf"

# Download a file
curl -o report.pdf http://localhost/storage/download/ai-stack/documents/report.pdf

# List files
curl -X POST http://localhost/storage/list \
  -H "Content-Type: application/json" \
  -d '{"prefix": "documents/"}'

# Delete files
curl -X POST http://localhost/storage/delete \
  -H "Content-Type: application/json" \
  -d '{"keys": ["documents/report.pdf"]}'
```

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

---

## 🧪 Jupyter Notebook

A complete notebook is included at `testing_notebook.ipynb` with examples for every endpoint.

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
| **Dozzle (Logs)** | `http://<IP>:8081` | No auth |
| **ChromaDB** | `http://<IP>:8000` | No auth |

---

## 🔧 Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection URL |
| `NEO4J_USER` | `neo4j` | Neo4j username |
| `NEO4J_PASSWORD` | `changeme` | Neo4j password |
| `SEARXNG_URL` | `http://searxng:8080` | SearXNG internal URL |
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

---

## 💻 Resource Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| **RAM** | 4 GB | 8 GB |
| **CPU** | 2 cores | 4 cores |
| **Disk** | 30 GB | 100 GB |
| **Swap** | 4 GB | 8 GB |

---

## 🐛 Troubleshooting

| Issue | Fix |
|-------|-----|
| Container won't start | `docker logs ai-stack-<service>` |
| Port already in use | `lsof -i :<port>` |
| Out of memory | Increase Docker memory or add swap |
| Model download fails | Check internet, retry `make up` |
| SearXNG warnings | Harmless — search still works |
| `data/` permission errors | `sudo chmod -R 777 data/` |
| App won't build | `make clean && make up` |

---

## 📄 License

MIT — use freely in your projects.
