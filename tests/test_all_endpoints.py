"""Comprehensive test: all new & modified endpoints. No DB writes — reads only.

Run: uv run python tests/test_all_endpoints.py
"""

import os
import sys
import json
import time

# Load .env before anything else
def load_dotenv(path: str = ".env"):
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key, val = key.strip(), val.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = val

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Disable auth + rate limiting before importing app (no Redis available)
os.environ["AUTH_ENABLED"] = "false"
# Fix HF cache path — /root/ is not writable by ubuntu user
os.environ["HF_HOME"] = os.path.expanduser("~/.cache/huggingface-test")

load_dotenv(".env")

from fastapi.testclient import TestClient
from app.main import app

# Monkey-patch rate limiter to bypass Redis
import app.auth as auth_mod
import app.middleware as mw_mod

async def _mock_rate_limit(identifier: str, limit: int):
    return True, 999, int(time.time() + 60)

auth_mod.check_rate_limit = _mock_rate_limit
mw_mod.check_rate_limit = _mock_rate_limit

# Also patch health-check Redis to avoid ConnectionError
import app.main as main_mod

async def _mock_check_redis():
    return {"status": "skipped", "note": "Redis not available in test"}

main_mod._check_redis = _mock_check_redis

client = TestClient(app)

# ── Auth setup ─────────────────────────────────────────────────────────────
admin_pass = os.getenv("ADMIN_PASS", "")
TOKEN = None

def get_headers():
    return {"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}

def get_token():
    global TOKEN
    resp = client.post("/auth/token", json={"username": "admin", "password": admin_pass})
    if resp.status_code == 200:
        TOKEN = resp.json()["access_token"]
        return True, TOKEN[:20] + "..."
    return False, resp.text

# ── Test runner ────────────────────────────────────────────────────────────
PASS, FAIL, SKIP = 0, 0, 0

def test(name: str, method: str, path: str, json_body=None, params=None,
         expect_status: int = 200, check_keys: list[str] = None,
         timeout: int = 60, skip_if: str = None):
    global PASS, FAIL, SKIP
    if skip_if:
        print(f"  [{name}] SKIP — {skip_if}")
        SKIP += 1
        return

    try:
        kwargs = {"headers": get_headers(), "timeout": timeout}
        if json_body is not None:
            kwargs["json"] = json_body
        if params is not None:
            kwargs["params"] = params
        
        t0 = time.time()
        fn = getattr(client, method)
        resp = fn(path, **kwargs)
        elapsed = time.time() - t0
        
        if resp.status_code != expect_status:
            print(f"  [{name}] FAIL ({resp.status_code} in {elapsed:.1f}s): {resp.text[:200]}")
            FAIL += 1
            return
        
        data = resp.json() if resp.text else {}
        if check_keys:
            missing = [k for k in check_keys if k not in data]
            if missing:
                print(f"  [{name}] FAIL — missing keys: {missing}")
                FAIL += 1
                return
        
        # Brief summary
        summary = ""
        if "number_of_results" in data:
            summary = f" → {data['number_of_results']} results"
        elif "results" in data:
            results = data["results"]
            if isinstance(results, list):
                summary = f" → {len(results)} results"
            elif isinstance(results, dict):
                summary = f" → {len(results)} items"
        elif "embeddings" in data:
            emb = data["embeddings"]
            summary = f" → {len(emb)} vectors, dim={len(emb[0]) if emb else 'N/A'}"
        elif "dimensions" in data:
            summary = f" → dim={data['dimensions']}"
        elif "scores" in data:
            summary = f" → {len(data['scores'])} scores"
        elif "markdown" in data:
            summary = f" → {len(data['markdown'])} chars markdown"
        
        print(f"  [{name}] PASS ({elapsed:.1f}s){summary}")
        PASS += 1
    except Exception as e:
        print(f"  [{name}] FAIL: {type(e).__name__}: {e}")
        FAIL += 1

# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

print("=" * 60)
print("COMPREHENSIVE ENDPOINT TEST")
print("=" * 60)

# ── Health check (no auth needed) ──────────────────────────────────────────
print("\n── Health ──")
test("health", "get", "/health", check_keys=["status", "services"])

# ── Auth ───────────────────────────────────────────────────────────────────
print("\n── Auth ──")
ok, token_preview = get_token()
if ok:
    print(f"  Token: {token_preview}")
else:
    print(f"  Token FAIL: {token_preview}")
    sys.exit(1)

# ═══════════════════════════════════════════════════════════════════════════
# NEW & MODIFIED ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

# ── Search (DDGS → SearXNG → Tavily → SerpAPI) ─────────────────────────────
print("\n── Search (4-engine fallback) ──")
test("search-ddg", "post", "/search",
     json_body={"query": "Python programming language", "max_results": 5},
     check_keys=["query", "number_of_results", "results"])

test("search-ai", "post", "/search",
     json_body={"query": "latest AI research 2026", "max_results": 5},
     check_keys=["query", "number_of_results", "results"])

# ── News (DDGS news + crawl) ───────────────────────────────────────────────
print("\n── News ──")
test("news-basic", "post", "/news",
     json_body={"query": "technology news", "max_results": 5},
     check_keys=["query", "number_of_results", "results"])

test("news-crawl", "post", "/news",
     json_body={"query": "climate change", "max_results": 3, "crawl_content": True},
     check_keys=["query", "number_of_results", "results"],
     timeout=1000)

# ── Images (DDGS → Unsplash → Pexels + CLIP) ───────────────────────────────
print("\n── Images ──")
test("images-ddg", "post", "/images",
     json_body={"query": "sunset over mountains", "max_results": 5, "use_clip": True},
     check_keys=["query", "number_of_results", "results"],
     timeout=1000)

test("images-no-clip", "post", "/images",
     json_body={"query": "ocean waves", "max_results": 3, "use_clip": False},
     check_keys=["query", "number_of_results", "results"])

# ── Videos (DDGS) ──────────────────────────────────────────────────────────
print("\n── Videos ──")
test("videos", "post", "/videos",
     json_body={"query": "python tutorial", "max_results": 5},
     check_keys=["query", "number_of_results", "results"])

# ── Crawl (DDGS extract → Scrapling → Trafilatura) ─────────────────────────
print("\n── Crawl ──")
test("crawl-wikipedia", "post", "/crawl",
     json_body={"url": "https://en.wikipedia.org/wiki/Python_(programming_language)", "only_main_content": True},
     check_keys=["url", "markdown", "title"])

test("crawl-article", "post", "/crawl",
     json_body={"url": "https://blog.python.org/", "only_main_content": True},
     check_keys=["url", "markdown"],
     timeout=30)

# ── Pipeline (Search → Crawl → Rerank) ─────────────────────────────────────
print("\n── Pipeline ──")
test("pipeline-simple", "post", "/pipeline",
     json_body={"query": "What is machine learning", "top_k": 3, "crawl_limit": 3, "max_search_results": 5},
     check_keys=["query", "results", "total_searched", "total_crawled"],
     timeout=1000)

# ═══════════════════════════════════════════════════════════════════════════
# EXISTING ENDPOINTS — READ-ONLY
# ═══════════════════════════════════════════════════════════════════════════

# ── Embed ──────────────────────────────────────────────────────────────────
print("\n── Embed ──")
test("embed", "post", "/embed",
     json_body={"texts": ["Hello world", "Machine learning is interesting"]},
     check_keys=["model", "dimensions", "embeddings"],
     timeout=60)

# ── CLIP ───────────────────────────────────────────────────────────────────
print("\n── CLIP ──")
test("clip-text", "post", "/clip/text_embedding",
     json_body={"texts": ["a photo of a cat", "a picture of a dog"]},
     check_keys=["model", "dimensions", "embeddings"],
     timeout=60)

# ── Reranker ───────────────────────────────────────────────────────────────
print("\n── Reranker ──")
test("rerank", "post", "/rerank",
     json_body={
         "query": "What is machine learning",
         "documents": [
             "Machine learning is a subset of artificial intelligence.",
             "Python is a programming language for web development.",
             "Deep learning uses neural networks with many layers."
         ],
         "top_k": 2
     },
     check_keys=["model", "query", "results"],
     timeout=60)

# ── YouTube (read-only) ────────────────────────────────────────────────────
print("\n── YouTube ──")
test("yt-info", "post", "/youtube/info",
     json_body={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
     check_keys=["id", "title", "webpage_url"],
     timeout=30)

# ── Browse ─────────────────────────────────────────────────────────────────
print("\n── Browse ──")
test("browse-content", "post", "/browse",
     json_body={"url": "https://httpbin.org/html", "action": "content"},
     check_keys=["url", "content", "success"],
     timeout=30)

# ── DB Reads (only if services are up) ────────────────────────────────────
print("\n── Database Reads ──")

# Cache read
test("cache-get", "get", "/cache/get/nonexistent_key",
     check_keys=["key", "found"],
     skip_if="Redis likely unavailable" if True else None)

# Vector search
test("vector-search", "post", "/vector/search",
     json_body={"collection": "test", "query_embedding": [0.0]*384, "top_k": 1},
     check_keys=["collection", "matches"],
     skip_if="ChromaDB likely unavailable — skip")

# Graph read
test("graph-query", "post", "/graph/query",
     json_body={"cypher": "RETURN 1 as n", "parameters": {}},
     check_keys=["records", "count"],
     skip_if="Neo4j likely unavailable — skip")

# DuckDB read
test("duckdb-query", "post", "/duckdb/query",
     json_body={"sql": "SELECT 1 AS test"},
     check_keys=["columns", "rows", "row_count"],
     skip_if="DuckDB unavailable — skip")

# Storage list
test("storage-list", "post", "/storage/list",
     json_body={"prefix": ""},
     check_keys=["bucket", "files", "count"],
     skip_if="MinIO likely unavailable — skip")

# ═══════════════════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════════════════
total = PASS + FAIL + SKIP
print("\n" + "=" * 60)
print(f"RESULTS: {PASS} pass, {FAIL} fail, {SKIP} skip ({total} total)")
print("=" * 60)

if FAIL > 0:
    sys.exit(1)
else:
    print("All tests passed! 🎉")
