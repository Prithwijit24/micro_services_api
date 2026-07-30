# 🧠 AI Infra Stack — Interactive Quickstart

> *A hands-on walkthrough of every endpoint, with real curl commands and expected outputs. Grab a coffee ☕ and let's build something cool.*

---

## 🔑 Before You Begin

Set these in your terminal — we'll reference them throughout:

```bash
API_KEY="${API_KEY:-aistack_demo_replace_me}"
BASE="${API_BASE:-https://aistackapi.duckdns.org}"
```

> 💡 **Set your real API key:** `export API_KEY=aistack_...` before running these commands.
> If you don't have one, see the [Auth Management](#-auth-management-bonus) section below.

---

## 🩺 Step 1: Is This Thing Alive?

Before we do anything fancy, let's make sure the server is awake. Think of this as knocking on the door before entering.

```bash
curl $BASE/health
```

**What comes back:**

```json
{
  "status": "ok",
  "services": {
    "redis":    { "status": "up" },
    "neo4j":    { "status": "up" },
    "chromadb": { "status": "up" },
    "searxng":  { "status": "up" },
    "minio":    { "status": "up" },
    "duckdb":   { "status": "up" }
  }
}
```

> 🎉 All six backend services are healthy. Redis is caching, Neo4j is graphing, ChromaDB is vectorizing, SearXNG is standing by to search, MinIO is ready for files, and DuckDB has its SQL engines warmed up. Let's go.

---

## 🔍 Step 2: Search the Web

*Imagine you're researching a topic. You type a question into Google. Our API does the same thing — but programmatically, so you can build it into your app.*

```bash
curl -X POST $BASE/search \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{"query":"best python libraries for data science","max_results":3}'
```

**What comes back:**

```json
{
  "query": "best python libraries for data science",
  "number_of_results": 3,
  "results": [
    {
      "title": "Top 10 Python Libraries for Data Science in 2026",
      "url": "https://www.datacamp.com/blog/top-python-libraries-for-data-science",
      "content": "Explore the best Python libraries for data science including Pandas, NumPy, Scikit-learn, TensorFlow, and PyTorch...",
      "engine": "ddgs"
    },
    {
      "title": "Python Data Science Handbook",
      "url": "https://jakevdp.github.io/PythonDataScienceHandbook/",
      "content": "The Python Data Science Handbook by Jake VanderPlas covers essential tools like IPython, NumPy, Pandas, Matplotlib...",
      "engine": "ddgs"
    },
    {
      "title": "Best Python Libraries for Machine Learning",
      "url": "https://towardsdatascience.com/best-python-libraries-for-ml",
      "content": "A comprehensive guide to Python machine learning libraries including Scikit-learn, XGBoost, and LightGBM...",
      "engine": "ddgs"
    }
  ]
}
```

> 🔄 **Fallback:** If DDGS (DuckDuckGo) is unreachable, the API automatically falls back to SearXNG. You don't need to do anything — it just works.

---

## 🕸️ Step 3: Crawl a Web Page

*Search is great, but what if you want the actual content of a page? That's where crawl comes in. Give it a URL, and it returns clean markdown you can feed into an AI model.*

```bash
curl -X POST $BASE/crawl \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{"url":"https://example.com","timeout_ms":10000}'
```

**What comes back:**

```json
{
  "url": "https://example.com/",
  "markdown": "This domain is for use in documentation examples without needing permission. Avoid use in operations.\n\nLearn more",
  "title": "Example Domain",
  "status_code": 200
}
```

> 🧹 The API strips away all the HTML, JavaScript, and styling. What you get is clean, readable markdown — perfect for feeding into an LLM or storing in a knowledge base.

> 🔄 **Fallback:** Scrapling is tried first. If it returns thin content (< 50 chars) or fails, Trafilatura takes over automatically.

---

## 🌐 Step 4: Browse a Live Page

*Crawling is great for static content. But what if you need to see what a page actually looks like in a browser? The browse endpoint fetches the full rendered HTML.*

```bash
curl -X POST $BASE/browse \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{"url":"https://example.com","action":"content"}'
```

**What comes back:**

```json
{
  "url": "https://example.com/",
  "action": "content",
  "content": "<!doctype html>\n<html lang=\"en\">\n<head>\n    <title>Example Domain</title>\n    <meta charset=\"utf-8\">\n    ...",
  "success": true
}
```

> ⚡ **Fast-fail:** If the browser layer isn't available (Playwright in Docker), the endpoint falls back to a fast HTTP GET. No hanging, no timeouts — just a clear response or error.

---

## 🧠 Step 5: Turn Text Into Vectors

*AI models don't understand words — they understand numbers. The embed endpoint converts your text into dense vectors (lists of floats) that capture semantic meaning. "Hello" and "Hi" get similar vectors; "Hello" and "Car" get very different ones.*

```bash
curl -X POST $BASE/embed \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{"texts":["python is a programming language","cookies are delicious"]}'
```

**What comes back:**

```json
{
  "model": "BAAI/bge-small-en-v1.5",
  "dimensions": 384,
  "embeddings": [
    [0.0234, -0.0156, 0.0891, ...384 floats total...],
    [0.0412, 0.0031, -0.0678, ...384 floats total...]
  ]
}
```

> 🔢 Each text is now a 384-dimensional vector. You can compare them with cosine similarity, store them in ChromaDB, or feed them into a neural network.

---

## 🎯 Step 6: Rerank Search Results

*You've got a pile of documents, but which ones actually matter? The reranker scores each document by how relevant it is to your query. Think of it as a smarter Ctrl+F.*

```bash
curl -X POST $BASE/rerank \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{"query":"python programming","documents":["Python is a programming language","Cookies are baked goods","Django is a Python framework"]}'
```

**What comes back:**

```json
{
  "model": "BAAI/bge-reranker-v2-m3",
  "query": "python programming",
  "results": [
    { "index": 0, "document": "Python is a programming language", "score": 0.94 },
    { "index": 2, "document": "Django is a Python framework", "score": 0.87 },
    { "index": 1, "document": "Cookies are baked goods", "score": 0.12 }
  ]
}
```

> 📊 The Python document scores 0.94 (highly relevant), Django scores 0.87 (also Python-related!), and cookies... well, 0.12 (not relevant at all). The model *understands* meaning, not just keywords.

---

## 🗄️ Step 7: Cache Things in Redis

*Sometimes you compute something expensive and want to save it for later. Redis is your high-speed storage locker — store anything, get it back in milliseconds.*

```bash
# Store a value (expires in 5 minutes)
curl -X POST $BASE/cache/set \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{"key":"greeting","value":{"lang":"en","text":"hello world"},"ttl_seconds":300}'

# Get it back
curl $BASE/cache/get/greeting -H "X-API-Key: $API_KEY"

# Delete it
curl -X DELETE $BASE/cache/delete/greeting -H "X-API-Key: $API_KEY"
```

**What comes back:**

```json
// SET → { "key": "greeting", "success": true }
// GET → { "key": "greeting", "value": { "lang": "en", "text": "hello world" }, "found": true }
// DELETE → { "key": "greeting", "deleted": true }
```

---

## 🕸️ Step 8: Build a Knowledge Graph

*Relationships matter. "Alice knows Bob." "Paris is in France." Neo4j lets you store these connections and query them with Cypher, a graph query language.*

```bash
# Add a person
curl -X POST $BASE/graph/add_node \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{"label":"Person","properties":{"name":"Ada Lovelace","born":1815},"merge_key":"name"}'

# Run a query
curl -X POST $BASE/graph/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{"cypher":"MATCH (p:Person) RETURN p.name AS name, p.born AS born ORDER BY p.born"}'
```

**What comes back:**

```json
{
  "records": [
    { "name": "Ada Lovelace", "born": 1815 }
  ],
  "count": 1
}
```

> 🛡️ **Injection guard:** The API automatically rejects Cypher injection attempts. Try `{"label":"Person`) DETACH DELETE n //"}` and you'll get a 400 error. Safe by default.

---

## 📊 Step 9: Run SQL with DuckDB

*Need to crunch numbers? DuckDB is an embedded analytical database — think SQLite, but built for OLAP. Run SQL queries directly via the API.*

```bash
curl -X POST $BASE/duckdb/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{"sql":"SELECT 42 AS answer, 'hello' AS greeting, 3.14 AS pi"}'
```

**What comes back:**

```json
{
  "columns": ["answer", "greeting", "pi"],
  "rows": [
    { "answer": 42, "greeting": "hello", "pi": 3.14 }
  ],
  "row_count": 1,
  "error": null
}
```

> 📈 DuckDB handles millions of rows in memory. Great for analytics, aggregations, and temporary data processing.

---

## 🎬 Step 10: Extract YouTube Insights

*Videos are the internet's largest knowledge source — but they're opaque to AI. Our YouTube endpoint extracts metadata, transcripts, and even downloads audio for Whisper transcription.*

```bash
# Get video info
curl -X POST $BASE/youtube/info \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{"url":"https://www.youtube.com/watch?v=dQw4w9WgXcQ"}'
```

**What comes back:**

```json
{
  "id": "dQw4w9WgXcQ",
  "title": "Rick Astley - Never Gonna Give You Up",
  "duration": 212,
  "uploader": "Rick Astley",
  "view_count": 1500000000,
  "thumbnail": "https://i.ytimg.com/vi/dQw4w9WgXcQ/maxresdefault.jpg",
  "webpage_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
}
```

```bash
# Get the transcript as markdown
curl -X POST "$BASE/youtube/transcript?output_format=markdown" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{"url":"https://www.youtube.com/watch?v=dQw4w9WgXcQ"}'
```

**What comes back:**

```markdown
# Transcript: dQw4w9WgXcQ

**Video ID:** dQw4w9WgXcQ
**Language:** en
**Source:** youtube_subtitles
**Segments:** 48

---

## Full Transcript

**[0:00]** We're no strangers to love

**[0:04]** You know the rules and so do I

**[0:08]** A full commitment's what I'm thinking of
...
```

> 🎤 **Whisper fallback:** If YouTube subtitles aren't available, the API downloads the audio and transcribes it with OpenAI's Whisper model. Works in 99 languages.

---

## 📦 Step 11: Store Files with MinIO

*S3-compatible storage right in your stack. Upload files, list them, download them — just like AWS S3, but self-hosted.*

```bash
# Upload
curl -X POST $BASE/storage/upload \
  -H "X-API-Key: $API_KEY" \
  -F "key=notes/todo.txt" \
  -F "file=@/path/to/your/file.txt"

# List files
curl -X POST $BASE/storage/list \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{"prefix":"notes/"}'

# Download
curl $BASE/storage/download/ai-stack/notes/todo.txt \
  -H "X-API-Key: $API_KEY" \
  -o downloaded.txt
```

---

## ⚡ Step 12: The Full Pipeline (Search → Crawl → Rerank)

*This is where the magic happens. One API call does it all: search the web, crawl the top results, extract clean markdown, and rerank everything by relevance. What would take 50 lines of code is now a single curl.*

```bash
curl -X POST $BASE/pipeline \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{"query":"latest breakthroughs in quantum computing 2026","top_k":3,"crawl_limit":5}'
```

**What comes back:**

```json
{
  "query": "latest breakthroughs in quantum computing 2026",
  "results": [
    {
      "url": "https://www.nature.com/articles/quantum-breakthrough-2026",
      "title": "Quantum computing reaches new milestone with 1000-qubit processor",
      "score": 0.95,
      "markdown": "Researchers at IBM announced today a 1000-qubit quantum processor...",
      "search_snippet": "IBM's new quantum processor...",
      "is_youtube": false
    },
    {
      "url": "https://news.mit.edu/2026/quantum-error-correction",
      "title": "MIT researchers demonstrate practical quantum error correction",
      "score": 0.89,
      "markdown": "A team at MIT has developed a new error correction technique...",
      "search_snippet": "MIT's error correction breakthrough...",
      "is_youtube": false
    },
    {
      "url": "https://www.youtube.com/watch?v=abc123",
      "title": "Quantum Computing Explained in 10 Minutes",
      "score": 0.82,
      "markdown": "## Transcript\n\n**[0:00]** Quantum computing is fundamentally different from classical computing...",
      "search_snippet": "Understanding quantum computing...",
      "is_youtube": true,
      "video_id": "abc123",
      "transcript_source": "youtube_subtitles"
    }
  ],
  "total_searched": 15,
  "total_crawled": 5,
  "timings": {
    "search": 1.2,
    "crawl": 4.8,
    "rerank": 0.3,
    "total": 6.3
  }
}
```

> ⚡ In 6.3 seconds, the pipeline searched 15 results, crawled 5 pages (including a YouTube video with automatic transcript extraction), and reranked everything by relevance. Each result comes with clean markdown ready for your AI application.

---

## 🧪 Step 13: Run the Full Test Suite

Want to verify everything is working? Run the comprehensive test suite — 40+ tests covering all endpoints and edge cases:

```bash
export API_KEY="${API_KEY:-}"
export ADMIN_PASS="${ADMIN_PASS:-}"
bash tests/comprehensive.sh
```

**What you'll see:**

```
============================================
 COMPREHENSIVE API TEST SUITE
============================================

── Public (no auth) ──
  [PASS] Health endpoint (HTTP 200)
  [PASS] Root endpoint (HTTP 200)
  [PASS] Docs (Swagger) (HTTP 200)
  [PASS] OpenAPI JSON (HTTP 200)
  [PASS] Auth token (login) (HTTP 200)

── Auth enforcement ──
  [PASS] Protected without key (HTTP 401)
  [PASS] Protected POST no key (HTTP 401)

── Search ──
  [PASS] Search basic (HTTP 200)
  [PASS] Search single result (HTTP 200)

── Crawl ──
  [PASS] Crawl example.com (HTTP 200)
  [PASS] Crawl with html flag (HTTP 200)

── Browse ──
  [PASS] Browse example.com (HTTP 200)

── Embed ──
  [PASS] Embed single text (HTTP 200)

── Cache ──
  [PASS] Cache set (HTTP 200)
  [PASS] Cache get (HTTP 200)
  [PASS] Cache delete (HTTP 200)

── Graph ──
  [PASS] Graph query (HTTP 200)
  [PASS] Graph add node (HTTP 200)
  [PASS] Graph injection guard (HTTP 400)

── DuckDB ──
  [PASS] DuckDB query (HTTP 200)

── YouTube ──
  [PASS] YouTube info (HTTP 200)

── Storage ──
  [PASS] Storage list (HTTP 200)

── Pipeline ──
  [PASS] Pipeline (HTTP 200)

── Edge cases ──
  [PASS] Wrong password rejected (HTTP 401)
  [PASS] Wrong API key rejected (HTTP 401)

============================================
 RESULTS: 42 passed, 2 failed
============================================
```

---

## 🔐 Auth Management (Bonus)

*Need more API keys? Manage them programmatically:*

```bash
# 1. Login to get a JWT
TOKEN=$(curl -s -X POST $BASE/auth/token \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"admin\",\"password\":\"$ADMIN_PASS\"}" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

echo "Token: ${TOKEN:0:30}..."

# 2. Create a new API key (valid for 4 years)
curl -X POST $BASE/auth/apikey \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"name":"production-app","expires_days":1460}'

# 3. List all keys
curl $BASE/auth/apikeys -H "Authorization: Bearer $TOKEN"

# 4. Delete a key
curl -X DELETE "$BASE/auth/apikey?key=aistack_..." -H "Authorization: Bearer $TOKEN"
```

---

## 🎉 You Made It!

You've now used every endpoint in the AI Infra Stack. Here's what you can build with it:

- **RAG pipeline**: `/pipeline` → feed markdown into an LLM
- **Knowledge graph**: `/graph` → build entity relationships
- **Semantic search**: `/embed` + `/vector` → search by meaning, not keywords
- **Content extraction**: `/crawl` + `/youtube/transcript` → turn web content into text
- **Analytics**: `/duckdb` → run SQL on any data
- **File storage**: `/storage` → S3-compatible object storage

> 📚 **Interactive docs:** `https://aistackapi.duckdns.org/docs`
>
> 🧪 **Test suite:** `bash tests/comprehensive.sh`
>
> 🤖 **CI pipeline:** Runs every 6 hours — `.github/workflows/ci.yml`
