#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════════════════
# AI Infra Stack — Auth Test Script
# Generates JWT token, creates API key, and tests authenticated access.
# Run on your VM: bash scripts/test_auth.sh
# ══════════════════════════════════════════════════════════════════════════════
set -uo pipefail

BASE="${APP_BASE:-http://localhost}"
ADMIN_USER="${ADMIN_USER:-admin}"
ADMIN_PASS="${ADMIN_PASS:-changeme}"
PASS=0
FAIL=0

pass() { ((PASS++)); echo "  ✅ PASS: $1"; }
fail() { ((FAIL++)); echo "  ❌ FAIL: $1 — $2"; }

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  🔐 AI Infra Stack — Auth & API Key Test Suite"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# ── Step 1: Health Check ──────────────────────────────────────────────────
echo "── Step 1: Health Check ──"
health=$(curl -fsS "${BASE}/health" 2>/dev/null || true)
if echo "$health" | python3 -c "import sys,json; assert json.load(sys.stdin).get('status')=='ok'" 2>/dev/null; then
    pass "health endpoint"
else
    fail "health endpoint" "could not reach /health"
    echo ""
    echo "⚠️  Stack not running. Start with: make up"
    exit 1
fi

# ── Step 2: Test Unauthenticated Access (should be blocked) ──────────────
echo ""
echo "── Step 2: Test Unauthenticated Access ──"
unauth=$(curl -s -o /dev/null -w "%{http_code}" "${BASE}/pipeline" -X POST \
    -H 'Content-Type: application/json' \
    -d '{"query": "test", "top_k": 1}' 2>/dev/null || echo "000")
if [ "$unauth" = "403" ] || [ "$unauth" = "401" ]; then
    pass "unauthenticated access blocked (HTTP $unauth)"
else
    fail "unauthenticated access" "expected 401/403, got HTTP $unauth"
fi

# ── Step 3: Generate JWT Token ────────────────────────────────────────────
echo ""
echo "── Step 3: Generate JWT Token ──"
token_response=$(curl -fsS -X POST "${BASE}/auth/token" \
    -H 'Content-Type: application/json' \
    -d "{\"username\": \"${ADMIN_USER}\", \"password\": \"${ADMIN_PASS}\"}" 2>/dev/null || true)

if [ -z "$token_response" ]; then
    fail "JWT token generation" "no response from /auth/token"
    echo ""
    echo "⚠️  Make sure ADMIN_USER=admin and ADMIN_PASS=changeme are set in .env"
    exit 1
fi

TOKEN=$(echo "$token_response" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null || true)

if [ -z "$TOKEN" ]; then
    fail "JWT token extraction" "could not parse token from response"
    echo "Response: $token_response"
    exit 1
fi

pass "JWT token generated"
echo "  📝 Token (first 50 chars): ${TOKEN:0:50}..."

# ── Step 4: Verify JWT Token Works ────────────────────────────────────────
echo ""
echo "── Step 4: Verify JWT Token ──"
me_response=$(curl -fsS "${BASE}/auth/rate-status" \
    -H "Authorization: Bearer ${TOKEN}" 2>/dev/null || true)

if echo "$me_response" | python3 -c "import sys,json; d=json.load(sys.stdin); assert 'limit' in d" 2>/dev/null; then
    pass "JWT token verification"
    echo "  📊 Rate limit: $(echo "$me_response" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"{d['remaining']}/{d['limit']} remaining\")" 2>/dev/null)"
else
    fail "JWT token verification" "invalid response: ${me_response:0:200}"
fi

# ── Step 5: Create API Key ────────────────────────────────────────────────
echo ""
echo "── Step 5: Create API Key ──"
apikey_response=$(curl -fsS -X POST "${BASE}/auth/apikey" \
    -H 'Content-Type: application/json' \
    -H "Authorization: Bearer ${TOKEN}" \
    -d '{"name": "test-key", "rate_limit": 300, "expires_days": 30}' 2>/dev/null || true)

if [ -z "$apikey_response" ]; then
    fail "API key creation" "no response from /auth/apikey"
else
    API_KEY=$(echo "$apikey_response" | python3 -c "import sys,json; print(json.load(sys.stdin)['key'])" 2>/dev/null || true)
    if [ -n "$API_KEY" ]; then
        pass "API key created"
        echo "  📝 API Key: ${API_KEY}"
        echo "  ⚠️  SAVE THIS KEY — it won't be shown again!"
    else
        fail "API key extraction" "could not parse key from response"
        echo "Response: ${apikey_response:0:200}"
    fi
fi

# ── Step 6: Test API Key Access ───────────────────────────────────────────
echo ""
echo "── Step 6: Test API Key Access ──"
if [ -n "${API_KEY:-}" ]; then
    apikey_test=$(curl -fsS "${BASE}/auth/rate-status" \
        -H "X-API-Key: ${API_KEY}" 2>/dev/null || true)
    
    if echo "$apikey_test" | python3 -c "import sys,json; d=json.load(sys.stdin); assert 'limit' in d" 2>/dev/null; then
        pass "API key access"
        echo "  📊 Rate limit: $(echo "$apikey_test" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"{d['remaining']}/{d['limit']} remaining\")" 2>/dev/null)"
    else
        fail "API key access" "invalid response: ${apikey_test:0:200}"
    fi
else
    fail "API key access" "no API key available"
fi

# ── Step 7: Test Authenticated Pipeline ───────────────────────────────────
echo ""
echo "── Step 7: Test Authenticated Pipeline Access ──"
pipeline_response=$(timeout 120 curl -fsS -X POST "${BASE}/pipeline" \
    -H 'Content-Type: application/json' \
    -H "Authorization: Bearer ${TOKEN}" \
    -d '{"query": "python programming", "top_k": 2, "crawl_limit": 2}' 2>/dev/null || true)

if echo "$pipeline_response" | python3 -c "import sys,json; d=json.load(sys.stdin); assert 'results' in d" 2>/dev/null; then
    pass "authenticated pipeline access"
    echo "  📊 Results: $(echo "$pipeline_response" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"{len(d.get('results',[]))} results, searched={d.get('total_searched',0)}, crawled={d.get('total_crawled',0)}\")" 2>/dev/null)"
else
    fail "authenticated pipeline access" "invalid response: ${pipeline_response:0:200}"
fi

# ── Step 8: Test API Key Pipeline Access ──────────────────────────────────
echo ""
echo "── Step 8: Test API Key Pipeline Access ──"
if [ -n "${API_KEY:-}" ]; then    apikey_pipeline=$(timeout 120 curl -fsS -X POST "${BASE}/pipeline" \
    -H 'Content-Type: application/json' \
    -H "X-API-Key: ${API_KEY}" \
    -d '{"query": "python programming", "top_k": 2, "crawl_limit": 2}' 2>/dev/null || true)
    
    if echo "$apikey_pipeline" | python3 -c "import sys,json; d=json.load(sys.stdin); assert 'results' in d" 2>/dev/null; then
        pass "API key pipeline access"
    else
        fail "API key pipeline access" "invalid response: ${apikey_pipeline:0:200}"
    fi
else
    fail "API key pipeline access" "no API key available"
fi

# ── Step 9: Test Expired Token ────────────────────────────────────────────
echo ""
echo "── Step 9: Test Expired/Invalid Token ──"
expired_test=$(curl -s -o /dev/null -w "%{http_code}" "${BASE}/pipeline" \
    -X POST -H 'Content-Type: application/json' \
    -H "Authorization: Bearer invalid.token.here" \
    -d '{"query": "test", "top_k": 1}' 2>/dev/null || echo "000")

if [ "$expired_test" = "401" ] || [ "$expired_test" = "403" ]; then
    pass "invalid token rejected (HTTP $expired_test)"
else
    fail "invalid token" "expected 401/403, got HTTP $expired_test"
fi

# ── Step 10: List All API Keys ────────────────────────────────────────────
echo ""
echo "── Step 10: List All API Keys ──"
keys_list=$(curl -fsS "${BASE}/auth/apikeys" \
    -H "Authorization: Bearer ${TOKEN}" 2>/dev/null || true)

if echo "$keys_list" | python3 -c "import sys,json; d=json.load(sys.stdin); assert isinstance(d, list)" 2>/dev/null; then
    key_count=$(echo "$keys_list" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null)
    pass "list API keys (${key_count} keys)"
else
    fail "list API keys" "invalid response: ${keys_list:0:200}"
fi

# ── Summary ───────────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  📊 RESULTS: ${PASS} passed, ${FAIL} failed"
echo "═══════════════════════════════════════════════════════════════"
echo ""

if [ -n "${API_KEY:-}" ]; then
    echo "📋 Your Credentials:"
    echo "  JWT Token: ${TOKEN:0:50}..."
    echo "  API Key:   ${API_KEY}"
    echo ""
    echo "🔑 Use these to access protected endpoints:"
    echo "  curl -H 'Authorization: Bearer ${TOKEN}' ${BASE}/pipeline ..."
    echo "  curl -H 'X-API-Key: ${API_KEY}' ${BASE}/pipeline ..."
    echo ""
fi

# ── Cleanup ───────────────────────────────────────────────────────────────
if [ -n "${API_KEY:-}" ]; then
    echo "🧹 Cleaning up test API key..."
    curl -s -X DELETE "${BASE}/auth/apikey?key=${API_KEY}" \
        -H "Authorization: Bearer ${TOKEN}" >/dev/null 2>&1 || true
    echo "  ✅ Test API key revoked"
fi

if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
