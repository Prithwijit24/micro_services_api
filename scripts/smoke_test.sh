#!/usr/bin/env bash
# Hits /health, /crawl, /browse, and /pipeline on the app and prints a pass/fail summary.
# Requires the stack to be running: make up
set -uo pipefail

APP_BASE="${APP_BASE:-http://localhost}"
PASS=0
FAIL=0

pass() { ((PASS++)); echo "[PASS] $1"; }
fail() { ((FAIL++)); echo "[FAIL] $1 — $2"; }

echo "========================================"
echo " AI Infra Stack — Smoke Test"
echo "========================================"
echo ""

# ── 1. Health ──────────────────────────────────────────────────────────────
echo "--- Health ---"
response=$(curl -fsS "${APP_BASE}/health" 2>/dev/null || true)
if echo "$response" | python3 -c "import sys,json; assert json.load(sys.stdin).get('status')=='ok'" 2>/dev/null; then
    pass "health endpoint"
else
    fail "health endpoint" "could not reach /health"
fi

# ── 2. Crawl (static site) ────────────────────────────────────────────────
echo ""
echo "--- Crawl (static site) ---"
crawl_response=$(curl -fsS -X POST "${APP_BASE}/crawl" \
    -H 'Content-Type: application/json' \
    -d '{"url": "https://example.com", "timeout_ms": 15000}' 2>/dev/null || true)

if echo "$crawl_response" | python3 -c "import sys,json; d=json.load(sys.stdin); assert d.get('title')=='Example Domain'" 2>/dev/null; then
    pass "crawl: static site (example.com)"
else
    fail "crawl: static site" "unexpected response: ${crawl_response:0:200}"
fi

# ── 3. Crawl (bot-protected site via Firefox fallback) ─────────────────────
echo ""
echo "--- Crawl (bot-protected site) ---"
mmt_response=$(timeout 90 curl -fsS -X POST "${APP_BASE}/crawl" \
    -H 'Content-Type: application/json' \
    -d '{"url": "https://www.makemytrip.com/hotels/jaipur-hotels.html", "timeout_ms": 60000}' 2>/dev/null || true)

mmt_md_len=$(echo "$mmt_response" | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('markdown','')))" 2>/dev/null || echo "0")
if [ "$mmt_md_len" -gt 100 ]; then
    pass "crawl: bot-protected site via Firefox (MakeMyTrip, ${mmt_md_len} chars)"
else
    fail "crawl: bot-protected site" "markdown too short (${mmt_md_len} chars)"
fi

# ── 4. Browse (example.com) ───────────────────────────────────────────────
echo ""
echo "--- Browse ---"
browse_response=$(curl -fsS -X POST "${APP_BASE}/browse" \
    -H 'Content-Type: application/json' \
    -d '{"url": "https://example.com", "action": "content"}' 2>/dev/null || true)

if echo "$browse_response" | python3 -c "import sys,json; d=json.load(sys.stdin); c=d.get('content',''); assert 'Example Domain' in c" 2>/dev/null; then
    pass "browse: local Playwright (example.com)"
else
    fail "browse: local Playwright" "unexpected response: ${browse_response:0:200}"
fi

# ── 5. Pipeline (simple query) ────────────────────────────────────────────
echo ""
echo "--- Pipeline (simple query) ---"
pipeline_response=$(timeout 120 curl -fsS -X POST "${APP_BASE}/pipeline" \
    -H 'Content-Type: application/json' \
    -d '{"query": "python programming tutorial", "top_k": 2, "crawl_limit": 2}' 2>/dev/null || true)

pipeline_result=$(echo "$pipeline_response" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    searched = d.get('total_searched', 0)
    crawled = d.get('total_crawled', 0)
    results = len(d.get('results', []))
    print(f'{searched}|{crawled}|{results}')
except:
    print('error')
" 2>/dev/null || echo "error")

if [ "$pipeline_result" != "error" ]; then
    IFS='|' read -r searched crawled results <<< "$pipeline_result"
    if [ "$results" -gt 0 ]; then
        pass "pipeline: Search→Crawl→Rerank (searched=${searched}, crawled=${crawled}, results=${results})"
    else
        fail "pipeline: Search→Crawl→Rerank" "no results returned"
    fi
else
    fail "pipeline: Search→Crawl→Rerank" "invalid response: ${pipeline_response:0:200}"
fi

# ── 6. Pipeline (bot-protected query) ─────────────────────────────────────
echo ""
echo "--- Pipeline (bot-protected query) ---"
pipeline_mmt=$(timeout 120 curl -fsS -X POST "${APP_BASE}/pipeline" \
    -H 'Content-Type: application/json' \
    -d '{"query": "hotels in jaipur", "top_k": 2, "crawl_limit": 2}' 2>/dev/null || true)

pipeline_mmt_result=$(echo "$pipeline_mmt" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    searched = d.get('total_searched', 0)
    crawled = d.get('total_crawled', 0)
    results = len(d.get('results', []))
    max_md = max((len(r.get('markdown', '')) for r in d.get('results', [])), default=0)
    print(f'{searched}|{crawled}|{results}|{max_md}')
except:
    print('error')
" 2>/dev/null || echo "error")

if [ "$pipeline_mmt_result" != "error" ]; then
    IFS='|' read -r searched crawled results max_md <<< "$pipeline_mmt_result"
    if [ "$results" -gt 0 ]; then
        pass "pipeline: bot-protected query (searched=${searched}, crawled=${crawled}, max_md=${max_md} chars)"
    else
        fail "pipeline: bot-protected query" "no results returned"
    fi
else
    fail "pipeline: bot-protected query" "invalid response: ${pipeline_mmt:0:200}"
fi

# ── Summary ────────────────────────────────────────────────────────────────
echo ""
echo "========================================"
echo " RESULTS: ${PASS} passed, ${FAIL} failed"
echo "========================================"

if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
