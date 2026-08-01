"""DB read-only tests — uses httpx against running app (avoids TestClient event-loop issues).

Usage: docker exec ai-stack-app sh -c 'cat > /tmp/db_test.py && cd /app && /app/.venv/bin/python /tmp/db_test.py'
"""

import os, sys, time, json
import httpx

PASS = FAIL = SKIP = 0
BASE = os.getenv("API_BASE") or "http://localhost:8000"

# Get JWT token
admin_pass = os.getenv("ADMIN_PASS", "")
if not admin_pass:
    print("No ADMIN_PASS set")
    sys.exit(1)

client = httpx.Client(timeout=30)
resp = client.post(f"{BASE}/auth/token", json={"username": "admin", "password": admin_pass})
if resp.status_code != 200:
    print(f"Token FAIL: {resp.text}")
    sys.exit(1)
TOKEN = resp.json()["access_token"]
print("Token acquired")

def h():
    return {"Authorization": f"Bearer {TOKEN}"}

def test(name, method, path, json_body=None, params=None, expect_status=200, check_keys=None):
    global PASS, FAIL, SKIP
    try:
        fn = getattr(client, method)
        kwargs = {"headers": h()}
        if json_body is not None:
            kwargs["json"] = json_body
        if params is not None:
            kwargs["params"] = params
        
        t0 = time.time()
        resp = fn(f"{BASE}{path}", **kwargs)
        elapsed = time.time() - t0

        if resp.status_code != expect_status:
            detail = resp.text[:200]
            print(f"  [{name}] FAIL ({resp.status_code} in {elapsed:.1f}s): {detail}")
            FAIL += 1
            return

        data = resp.json() if resp.text else {}
        if check_keys:
            missing = [k for k in check_keys if k not in data]
            if missing:
                print(f"  [{name}] FAIL — missing keys: {missing}")
                FAIL += 1
                return

        summary = ""
        if "matches" in data:
            summary = f" -> {len(data['matches'])} matches"
        elif "records" in data:
            summary = f" -> {data['count']} records"
        elif "found" in data:
            summary = f" -> found={data['found']}"
        elif "row_count" in data:
            summary = f" -> {data['row_count']} rows"
        elif "files" in data:
            summary = f" -> {data['count']} files"
        elif "tables" in data:
            summary = f" -> {len(data['tables'])} tables"

        print(f"  [{name}] PASS ({elapsed:.1f}s){summary}")
        PASS += 1
    except Exception as e:
        print(f"  [{name}] FAIL: {type(e).__name__}: {e}")
        FAIL += 1

print("=" * 50)
print("DB READ-ONLY TESTS (httpx)")

# ── Redis Cache ───────────────────────────────────────────
print("\n-- Redis Cache --")
test("cache-get", "get", "/cache/get/test-key",
     check_keys=["key", "found"])

# ── DuckDB ────────────────────────────────────────────────
print("\n-- DuckDB --")
test("duckdb-query", "post", "/duckdb/query",
     json_body={"sql": "SELECT 1 AS test, 'hello' AS greeting"},
     check_keys=["columns", "rows", "row_count"])
test("duckdb-tables", "get", "/duckdb/tables",
     check_keys=["tables"])

# ── Neo4j Graph ───────────────────────────────────────────
print("\n-- Neo4j Graph --")
test("graph-query", "post", "/graph/query",
     json_body={"cypher": "RETURN 1 AS n", "parameters": {}},
     check_keys=["records", "count"])
test("graph-schema", "post", "/graph/query",
     json_body={"cypher": "CALL db.labels()", "parameters": {}},
     check_keys=["records", "count"])

# ── ChromaDB Vector ───────────────────────────────────────
print("\n-- ChromaDB Vector --")
resp = client.post(f"{BASE}/vector/search", json={
    "collection": "default",
    "query_embedding": [0.01] * 384,
    "top_k": 3
}, headers=h())
if resp.status_code in (200, 404):
    print(f"  [vector-search] PASS ({resp.elapsed.total_seconds():.1f}s) -> status={resp.status_code}")
    PASS += 1
else:
    print(f"  [vector-search] FAIL ({resp.status_code}): {resp.text[:200]}")
    FAIL += 1

# ── MinIO Storage ─────────────────────────────────────────
print("\n-- MinIO Storage --")
test("storage-list", "post", "/storage/list",
     json_body={"prefix": ""},
     check_keys=["bucket", "files", "count"])

# ── Summary ───────────────────────────
total = PASS + FAIL + SKIP
print("\n" + "=" * 50)
print(f"RESULTS: {PASS} pass, {FAIL} fail, {SKIP} skip ({total} total)")
print("=" * 50)
sys.exit(0 if FAIL == 0 else 1)
