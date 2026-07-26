# AI Infrastructure Stack

Production-ready, self-hosted AI infrastructure for an Oracle Cloud VPS (or any
Docker host). Every capability — search, crawling, browser automation,
YouTube, embeddings, CLIP, reranking, graph, vector, cache — is exposed as an
independent **FastAPI microservice**. Your main application (e.g. a
LangGraph agent) talks only to the **API Gateway**; it never touches Neo4j,
ChromaDB, Redis, Postgres, SearXNG, or Firecrawl directly. Swap any backend
(e.g. ChromaDB → Qdrant) later without changing a single line of client code.

```
Internet → Cloudflare (optional) → Caddy (TLS) → Gateway → internal services
```

## Repository layout

```
ai-infra-stack/
├── docker-compose.yml       # full stack definition
├── Makefile                 # up/down/backup/restore/per-service targets
├── .env.example             # copy to .env and fill in secrets
├── caddy/Caddyfile          # reverse proxy + automatic HTTPS
├── scripts/                 # backup.sh, restore.sh, run_tests.sh, smoke_test.sh
├── tests/test_smoke.py      # local, Docker-free smoke tests for every service
├── services/
│   ├── gateway/    # routes external traffic to internal services
│   ├── search/     # -> SearXNG
│   ├── crawl/      # -> Firecrawl (returns Markdown)
│   ├── browser/    # -> Camoufox + Playwright
│   ├── youtube/    # -> yt-dlp (info/download/transcript/thumbnail)
│   ├── embed/      # -> BAAI/bge-small-en-v1.5
│   ├── clip/       # -> openai/clip-vit-base-patch32
│   ├── reranker/   # -> BAAI/bge-reranker-v2-m3
│   ├── graph/      # -> Neo4j (app never writes Cypher directly)
│   ├── vector/     # -> ChromaDB
│   └── cache/      # -> Redis
├── data/                     # bind-mounted persistent data (gitignored)
├── models/                   # shared Hugging Face cache (gitignored)
└── backups/                  # generated backup archives (gitignored)
```

Each service directory follows the same shape:
`main.py`, `routers/`, `service.py`, `models.py`, `requirements.txt`, `Dockerfile`.

## Quick start

```bash
git clone <this-repo> ai-infra-stack
cd ai-infra-stack
cp .env.example .env        # edit passwords, domain, etc.
make up                     # builds and starts everything
make ps                     # check container status
make smoke-test             # curl /health through the gateway
```

The gateway is the **only** service reachable from the reverse proxy.
Everything else lives on the internal Docker network (`internal`) and is
never port-published to the host.

## Common commands

| Command | Description |
|---|---|
| `make up` / `make down` | start / stop the whole stack |
| `make restart` | restart all containers |
| `make logs` | tail logs for everything |
| `make logs-embed` | tail logs for a single service |
| `make ps` | container status |
| `make build` | rebuild microservice images |
| `make update` | pull latest infra images + rebuild app images |
| `make backup` | dump Postgres/Neo4j/ChromaDB/Redis to `./backups` |
| `make restore FILE=./backups/xxxx.tar.gz` | restore from a backup |
| `make start-<service>` / `make stop-<service>` | control one service |
| `make shell SVC=embed` | shell into a running container |
| `make test` | run local FastAPI smoke tests (no Docker required) |
| `make clean` | remove stopped containers + dangling images (data kept) |

Per-service shortcuts exist for the ones called out in the spec directly:
`make postgres`, `make redis`, `make neo4j`, `make chromadb`, `make firecrawl`,
`make browser`, `make youtube`, `make embed`, `make clip`, `make reranker`,
`make search` (each is `start-<service>`; stop with `make stop-<service>`).

## Gateway routing

The gateway forwards by path prefix to the matching internal service:

| Path prefix | Internal service |
|---|---|
| `/search` | search → SearXNG |
| `/crawl` | crawl → Firecrawl |
| `/browse` | browser → Camoufox/Playwright |
| `/youtube/*` | youtube → yt-dlp |
| `/embed` | embed → bge-small-en-v1.5 |
| `/clip/*` | clip → CLIP |
| `/rerank` | reranker → bge-reranker-v2-m3 |
| `/graph/*` | graph → Neo4j |
| `/vector/*` | vector → ChromaDB |
| `/cache/*` | cache → Redis |

`GET /health` on the gateway checks every downstream service and reports
`ok` / `degraded` / `unreachable` per service.

## Hugging Face model cache

`embed`, `clip`, and `reranker` all mount `./models` to
`/root/.cache/huggingface` so models are downloaded **once** on first use and
shared across containers and restarts — never baked into the image at build
time.

## Testing without Docker

`tests/test_smoke.py` imports each service's FastAPI app in-process, mocks
the external dependency (SearXNG/Firecrawl/Redis/ChromaDB/Neo4j/yt-dlp/model
weights), and exercises the real request-validation and response-shaping
code paths — including a check that the graph service rejects Cypher-label
injection attempts. Run it with:

```bash
make test
```

## Security notes

- Only `caddy` (host ports 80/443) and, indirectly, `gateway` are reachable
  from outside the Docker network.
- The `graph` service validates node labels and relationship types against
  a strict identifier regex before interpolating them into Cypher (Neo4j has
  no native way to parameterize labels/relationship types), preventing
  Cypher injection through the label/relationship fields.
- Set real, unique passwords in `.env` before deploying — the defaults in
  `.env.example` are placeholders only.
- Firecrawl and Postgres both read credentials from `.env` via `env_file`.

## Extending the stack

Because every capability is behind an HTTP API, you can add or replace
infrastructure (Ollama, Qdrant, MinIO, Whisper, OCR, image generation)
without touching any client code — just point the relevant microservice's
`service.py` at the new backend and keep its FastAPI contract the same.
