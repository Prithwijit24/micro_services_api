"""
Smoke tests for the AI infrastructure microservices.

These tests import each service's FastAPI app directly (no Docker needed) and
exercise the HTTP layer with the fastapi.testclient.TestClient, mocking out
network calls to external infra (SearXNG, Firecrawl, Neo4j, ChromaDB, Redis,
yt-dlp) so that routing, validation, and response-shaping logic is verified
in isolation.

Run with: bash scripts/run_tests.sh
"""
import sys
import os
import importlib
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

REPO_ROOT = Path(__file__).resolve().parent.parent
SERVICES_DIR = REPO_ROOT / "services"

results = []


def record(name, ok, detail=""):
    results.append((name, ok, detail))
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] {name}" + (f" — {detail}" if detail and not ok else ""))


def load_app(service_name: str):
    """Import a service's main:app module with its own directory on sys.path,
    isolated from other services' same-named modules (main, service, models)."""
    svc_path = str(SERVICES_DIR / service_name)
    # Remove any previously-imported same-named modules from other services
    for mod in ["main", "service", "models", "routers", "routers.search",
                "routers.crawl", "routers.browser", "routers.youtube",
                "routers.embed", "routers.clip", "routers.reranker",
                "routers.graph", "routers.vector", "routers.cache",
                "routers.proxy"]:
        sys.modules.pop(mod, None)
    if svc_path not in sys.path:
        sys.path.insert(0, svc_path)
    else:
        sys.path.remove(svc_path)
        sys.path.insert(0, svc_path)
    module = importlib.import_module("main")
    return module.app


def cleanup_path(service_name: str):
    svc_path = str(SERVICES_DIR / service_name)
    if svc_path in sys.path:
        sys.path.remove(svc_path)


# -----------------------------------------------------------------------
# 1. GATEWAY — routing + aggregated health check
# -----------------------------------------------------------------------
def test_gateway():
    from fastapi.testclient import TestClient
    app = load_app("gateway")
    import service as gw_service_mod

    async def fake_check_health(name):
        return "ok", None

    with patch.object(gw_service_mod.gateway_service, "check_health", side_effect=fake_check_health):
        client = TestClient(app)
        r = client.get("/health")
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["gateway"] == "ok"
        assert len(data["services"]) == 10
        assert all(s["status"] == "ok" for s in data["services"])

        r2 = client.get("/")
        assert r2.status_code == 200
        assert "routes" in r2.json()

    # Test proxying: mock the upstream call and confirm routing table works
    import httpx as httpx_mod

    async def fake_proxy(service, path, method, json_body=None, params=None):
        assert service == "search"
        assert path == "/search"
        return httpx_mod.Response(200, json={"query": "test", "number_of_results": 0, "results": []})

    with patch.object(gw_service_mod.gateway_service, "proxy", side_effect=fake_proxy):
        client = TestClient(app)
        r = client.post("/search", json={"query": "test"})
        assert r.status_code == 200, r.text
        assert r.json()["query"] == "test"

    cleanup_path("gateway")
    record("gateway: health aggregation + proxy routing", True)


# -----------------------------------------------------------------------
# 2. SEARCH — SearXNG wrapper
# -----------------------------------------------------------------------
def test_search():
    from fastapi.testclient import TestClient
    app = load_app("search")
    import service as search_service_mod

    fake_response = {
        "results": [
            {"title": "Result 1", "url": "https://example.com/1", "content": "snippet", "engine": "google"},
        ]
    }

    class FakeResp:
        def raise_for_status(self): pass
        def json(self): return fake_response

    async def fake_get(self, url, params=None):
        return FakeResp()

    with patch("httpx.AsyncClient.get", new=fake_get):
        client = TestClient(app)
        r = client.get("/health")
        assert r.status_code == 200
        r2 = client.post("/search", json={"query": "python fastapi"})
        assert r2.status_code == 200, r2.text
        data = r2.json()
        assert data["number_of_results"] == 1
        assert data["results"][0]["title"] == "Result 1"

    cleanup_path("search")
    record("search: SearXNG wrapper", True)


# -----------------------------------------------------------------------
# 3. CRAWL — Firecrawl wrapper
# -----------------------------------------------------------------------
def test_crawl():
    from fastapi.testclient import TestClient
    app = load_app("crawl")

    fake_data = {
        "data": {
            "markdown": "# Hello world",
            "metadata": {"title": "Hello", "statusCode": 200},
        }
    }

    class FakeResp:
        def raise_for_status(self): pass
        def json(self): return fake_data

    async def fake_post(self, url, json=None, headers=None):
        return FakeResp()

    with patch("httpx.AsyncClient.post", new=fake_post):
        client = TestClient(app)
        r = client.post("/crawl", json={"url": "https://example.com"})
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["markdown"] == "# Hello world"
        assert data["title"] == "Hello"

    cleanup_path("crawl")
    record("crawl: Firecrawl wrapper", True)


# -----------------------------------------------------------------------
# 4. CACHE — Redis wrapper
# -----------------------------------------------------------------------
def test_cache():
    from fastapi.testclient import TestClient
    app = load_app("cache")
    import service as cache_service_mod

    store = {}

    class FakeRedis:
        async def set(self, key, value, ex=None):
            store[key] = value
        async def get(self, key):
            return store.get(key)
        async def delete(self, key):
            existed = key in store
            store.pop(key, None)
            return 1 if existed else 0
        async def aclose(self):
            pass

    cache_service_mod.cache_service._client = FakeRedis()

    client = TestClient(app)
    r = client.post("/cache/set", json={"key": "foo", "value": {"a": 1}, "ttl_seconds": 60})
    assert r.status_code == 200, r.text
    assert r.json()["success"] is True

    r2 = client.get("/cache/get/foo")
    assert r2.status_code == 200
    assert r2.json()["found"] is True
    assert r2.json()["value"] == {"a": 1}

    r3 = client.delete("/cache/delete/foo")
    assert r3.status_code == 200
    assert r3.json()["deleted"] is True

    r4 = client.get("/cache/get/missing")
    assert r4.json()["found"] is False

    cleanup_path("cache")
    record("cache: Redis wrapper (set/get/delete)", True)


# -----------------------------------------------------------------------
# 5. VECTOR — ChromaDB wrapper
# -----------------------------------------------------------------------
def test_vector():
    from fastapi.testclient import TestClient
    app = load_app("vector")
    import service as vector_service_mod

    class FakeCollection:
        def __init__(self):
            self.store = {}
        def upsert(self, ids, embeddings, documents, metadatas):
            for i, _id in enumerate(ids):
                self.store[_id] = (embeddings[i], documents[i], metadatas[i])
        def query(self, query_embeddings, n_results, where=None):
            ids = list(self.store.keys())[:n_results]
            return {
                "ids": [ids],
                "distances": [[0.1] * len(ids)],
                "documents": [[self.store[i][1] for i in ids]],
                "metadatas": [[self.store[i][2] for i in ids]],
            }
        def delete(self, ids):
            for i in ids:
                self.store.pop(i, None)

    fake_collection = FakeCollection()

    class FakeClient:
        def get_or_create_collection(self, name):
            return fake_collection

    vector_service_mod.vector_service._client = FakeClient()

    client = TestClient(app)
    r = client.post("/vector/upsert", json={
        "collection": "docs",
        "records": [{"id": "1", "embedding": [0.1, 0.2], "document": "hello", "metadata": {"src": "test"}}],
    })
    assert r.status_code == 200, r.text
    assert r.json()["upserted"] == 1

    r2 = client.post("/vector/search", json={
        "collection": "docs", "query_embedding": [0.1, 0.2], "top_k": 5,
    })
    assert r2.status_code == 200, r2.text
    assert len(r2.json()["matches"]) == 1
    assert r2.json()["matches"][0]["document"] == "hello"

    r3 = client.post("/vector/delete", json={"collection": "docs", "ids": ["1"]})
    assert r3.status_code == 200
    assert r3.json()["deleted"] == 1

    cleanup_path("vector")
    record("vector: ChromaDB wrapper (upsert/search/delete)", True)


# -----------------------------------------------------------------------
# 6. GRAPH — Neo4j wrapper (validates Cypher-injection guard + flow)
# -----------------------------------------------------------------------
def test_graph():
    from fastapi.testclient import TestClient
    app = load_app("graph")
    import service as graph_service_mod

    class FakeResult:
        def __init__(self, records):
            self._records = records
            self._i = 0
        def __aiter__(self):
            return self
        async def __anext__(self):
            if self._i >= len(self._records):
                raise StopAsyncIteration
            rec = self._records[self._i]
            self._i += 1
            return rec
        async def single(self):
            return self._records[0] if self._records else None

    class FakeSession:
        async def __aenter__(self):
            return self
        async def __aexit__(self, *a):
            return False
        async def run(self, cypher, params=None):
            if cypher.startswith("MERGE (n:Person"):
                return FakeResult([{"node_id": "n1", "props": {"name": "Alice"}}])
            return FakeResult([{"name": "Alice"}])

    class FakeDriver:
        def session(self):
            return FakeSession()
        async def close(self):
            pass

    graph_service_mod.graph_service._driver = FakeDriver()

    client = TestClient(app)
    r = client.post("/graph/query", json={"cypher": "MATCH (n) RETURN n.name AS name", "parameters": {}})
    assert r.status_code == 200, r.text
    assert r.json()["count"] == 1

    r2 = client.post("/graph/add_node", json={
        "label": "Person", "properties": {"name": "Alice"}, "merge_key": "name",
    })
    assert r2.status_code == 200, r2.text
    assert r2.json()["node_id"] == "n1"

    # Cypher-injection guard: invalid label must be rejected with 400
    r3 = client.post("/graph/add_node", json={"label": "Person`) DETACH DELETE n //", "properties": {}})
    assert r3.status_code == 400, r3.text

    cleanup_path("graph")
    record("graph: Neo4j wrapper + injection guard", True)


# -----------------------------------------------------------------------
# 7. YOUTUBE — yt-dlp wrapper (mocked extraction, real yt_dlp import)
# -----------------------------------------------------------------------
def test_youtube():
    from fastapi.testclient import TestClient
    app = load_app("youtube")
    import service as yt_service_mod

    fake_info = {
        "id": "abc123",
        "title": "Test Video",
        "duration": 120,
        "uploader": "Tester",
        "view_count": 42,
        "thumbnail": "https://example.com/thumb.jpg",
        "webpage_url": "https://youtube.com/watch?v=abc123",
    }

    def fake_extract_info(self, url):
        return fake_info

    with patch.object(yt_service_mod.YoutubeService, "_extract_info", new=fake_extract_info):
        client = TestClient(app)
        r = client.post("/youtube/info", json={"url": "https://youtube.com/watch?v=abc123"})
        assert r.status_code == 200, r.text
        assert r.json()["title"] == "Test Video"

    cleanup_path("youtube")
    record("youtube: yt-dlp info wrapper", True)


# -----------------------------------------------------------------------
# 8/9/10. EMBED / CLIP / RERANKER — verify routes wired without requiring
# torch/transformers to be installed (heavy libs are imported lazily)
# -----------------------------------------------------------------------
def test_embed_routes_wired():
    from fastapi.testclient import TestClient
    app = load_app("embed")
    import service as embed_service_mod

    class FakeModel:
        def encode(self, texts, normalize_embeddings=True):
            import numpy as np
            return np.array([[0.1, 0.2, 0.3] for _ in texts])
        def get_sentence_embedding_dimension(self):
            return 3

    embed_service_mod.embed_service._model = FakeModel()

    client = TestClient(app)
    r = client.post("/embed", json={"texts": ["hello", "world"]})
    assert r.status_code == 200, r.text
    assert r.json()["dimensions"] == 3
    assert len(r.json()["embeddings"]) == 2

    cleanup_path("embed")
    record("embed: route wiring + response shape (model mocked)", True)


def test_reranker_routes_wired():
    from fastapi.testclient import TestClient
    app = load_app("reranker")
    import service as rr_service_mod

    class FakeModel:
        def predict(self, pairs):
            return [0.9, 0.1]

    rr_service_mod.reranker_service._model = FakeModel()

    client = TestClient(app)
    r = client.post("/rerank", json={"query": "q", "documents": ["doc a", "doc b"]})
    assert r.status_code == 200, r.text
    assert r.json()["results"][0]["document"] == "doc a"
    assert r.json()["results"][0]["score"] == 0.9

    cleanup_path("reranker")
    record("reranker: route wiring + ranking order (model mocked)", True)


def test_clip_health_only():
    # CLIP requires torch/transformers/pillow which aren't installed in this
    # lightweight test env; verify the app at least constructs and /health works.
    from fastapi.testclient import TestClient
    try:
        app = load_app("clip")
    except ModuleNotFoundError as e:
        record("clip: app import (skipped, optional heavy deps not installed)", True, str(e))
        cleanup_path("clip")
        return
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200
    cleanup_path("clip")
    record("clip: health check", True)


def test_browser_health_only():
    from fastapi.testclient import TestClient
    try:
        app = load_app("browser")
    except ModuleNotFoundError as e:
        record("browser: app import (skipped, playwright not installed)", True, str(e))
        cleanup_path("browser")
        return
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200
    cleanup_path("browser")
    record("browser: health check", True)


if __name__ == "__main__":
    tests = [
        test_gateway, test_search, test_crawl, test_cache, test_vector,
        test_graph, test_youtube, test_embed_routes_wired,
        test_reranker_routes_wired, test_clip_health_only, test_browser_health_only,
    ]
    failed = 0
    for t in tests:
        try:
            t()
        except Exception as e:
            failed += 1
            record(t.__name__, False, f"{type(e).__name__}: {e}")

    print("\n" + "=" * 60)
    passed = sum(1 for _, ok, _ in results if ok)
    print(f"RESULTS: {passed}/{len(results)} passed")
    print("=" * 60)
    sys.exit(1 if failed else 0)
