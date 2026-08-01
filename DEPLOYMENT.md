<div align="center">

# ☁️ Oracle Cloud VM Deployment Guide

### *Step-by-step guide to deploy AI Infra Stack on Oracle Cloud Free Tier*

</div>

---

## 📋 Prerequisites

- [ ] Oracle Cloud account ([sign up free](https://cloud.oracle.com/))
- [ ] A domain name (optional — for HTTPS)
- [ ] Terminal/SSH client on your local machine
- [ ] ~15 minutes of your time

---

## 🏗️ Step 1: Create Oracle Cloud VM

1. Log in to **[cloud.oracle.com](https://cloud.oracle.com/)**
2. Click **☰ Menu** → **Compute** → **Instances** → **Create Instance**
3. **Name:** `ai-infra-stack`
4. **Image:** Ubuntu 24.04 or Oracle Linux 9
5. **Shape:** `VM.Standard.A1.Flex` (ARM, 4 OCPUs, 24GB RAM) — Free Tier eligible ✅
6. **SSH Keys:** Paste your public key
7. Click **Create**

### Generate SSH Key (if you don't have one)

```bash
ssh-keygen -t rsa -N "" -b 2048 -C "ai-stack-key" -f ~/.ssh/oci_vm_key
cat ~/.ssh/oci_vm_key.pub   # copy this into Oracle Cloud
```

---

## 🔓 Step 2: Open Ports

> ⚠️ Oracle Cloud has **two firewall layers**. Both must allow ports 80/443!

### Layer 1: Oracle Cloud Security Lists

1. **☰ Menu** → **Networking** → **Virtual Cloud Networks** → your VCN → **Public Subnet**
2. Click **Security Lists** → **Add Ingress Rules**

| Source CIDR | Protocol | Port | Purpose |
|-------------|----------|------|---------|
| `0.0.0.0/0` | TCP | `80` | HTTP |
| `0.0.0.0/0` | TCP | `443` | HTTPS |

👉 **Docs:** [Oracle Security Lists](https://docs.oracle.com/iaas/Content/Network/Concepts/securitylists.htm)

### Layer 2: OS Firewall

```bash
# Ubuntu
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw reload

# Oracle Linux
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

---

## 🔌 Step 3: SSH Into Your VM

```bash
ssh -i ~/.ssh/oci_vm_key ubuntu@<YOUR_VM_PUBLIC_IP>
```

---

## 🐳 Step 4: Install Docker

```bash
sudo apt-get update && sudo apt-get upgrade -y
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker
docker --version
docker compose version
```

---

## 📦 Step 5: Deploy

```bash
# Clone
git clone <your-repo-url> ai-infra-stack
cd ai-infra-stack

# Configure
cp .env.example .env
nano .env   # at minimum set: JWT_SECRET, ADMIN_PASS, NEO4J_PASSWORD, MINIO_ROOT_PASSWORD
#     JWT_SECRET=$(openssl rand -hex 32)

# Start (first run takes ~10 min)
make up

# Verify — liveness first (200 even if a dependency is down)
curl -s http://localhost/health/live
# → {"status":"ok"}

# Verify — readiness (200 only when all 6 backend services are up)
curl -s http://localhost/health | jq
# → {"status":"ok","services":{"redis":{...}, "neo4j":{...}, ...}}
```

> 💡 `./models/` (Hugging Face cache) and `./data/` (Neo4j, ChromaDB, Redis, MinIO, DuckDB, YouTube downloads) live on the host — no extra setup needed. First request to any ML endpoint will download the model (~2 GB one-time cost).
>
> 📚 Once everything is up, see [README.md](README.md) and [QUICKSTART.md](QUICKSTART.md) for every endpoint and a runnable curl walkthrough.

---

## 🌐 Step 6: Get Your Public URL

**Option A: Direct IP**
```
http://<YOUR_VM_PUBLIC_IP>
```

**Option B: Domain with free HTTPS**
1. Point DNS A record to `<YOUR_VM_PUBLIC_IP>`
2. Edit `.env`: set `DOMAIN=yourdomain.com` and `CADDY_ACME_EMAIL=you@email.com`
3. Run `make restart`
4. Your API is at `https://yourdomain.com` 🔒

---

## 🧪 Step 7: Test

Smoke-test the public surface first, then run a real protected call:

```bash
# Liveness (always returns 200)
curl http://<YOUR_VM_IP>/health/live

# Interactive API docs (Swagger UI) — open in your local browser
# macOS: open https://<YOUR_VM_IP_OR_DOMAIN>/docs
# Linux: xdg-open https://<YOUR_VM_IP_OR_DOMAIN>/docs
echo "Open https://<YOUR_VM_IP_OR_DOMAIN>/docs in your browser"

# Real pipeline call — needs an API key + admin password (set in .env)
export API_KEY=aistack_...            # mint one via /auth/apikey (see QUICKSTART)
export BASE=https://<YOUR_VM_IP_OR_DOMAIN>

curl -X POST $BASE/pipeline \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{"query": "what is python?", "top_k": 3, "crawl_limit": 5}'

# Streaming variant — Server-Sent Events
curl -N -X POST $BASE/pipeline/stream \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{"query": "rlhf explained", "top_k": 3}'

# Web search (DDGS → SearXNG fallback chain)
curl -X POST $BASE/search \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{"query":"latest AI news","max_results":5}'

# News / images / videos
curl -X POST $BASE/news   -H "Content-Type: application/json" -H "X-API-Key: $API_KEY" -d '{"query":"ai regulation","max_results":3}'
curl -X POST $BASE/images -H "Content-Type: application/json" -H "X-API-Key: $API_KEY" -d '{"query":"aurora borealis","max_results":4,"use_clip":true}'
curl -X POST $BASE/videos -H "Content-Type: application/json" -H "X-API-Key: $API_KEY" -d '{"query":"rust async tutorial","max_results":3}'
```

> 📚 For a full tour of every endpoint with expected JSON responses, see [QUICKSTART.md](QUICKSTART.md).
>
> 🧪 For the live test suite (~30 tests), set `API_KEY` and `ADMIN_PASS` and run `bash tests/comprehensive.sh`. CI runs it every 6 hours against this stack — see `.github/workflows/ci.yml`.

---

## 🔐 Step 8: Security

### Change Default Passwords

Edit `.env` and set unique passwords for:
- `NEO4J_PASSWORD`
- `MINIO_ROOT_PASSWORD`

### Dashboard Ports (only open if needed)

| Port | Service | Expose? |
|------|---------|---------|
| 80 | API (FastAPI via Caddy) | ✅ Yes |
| 443 | API (HTTPS via Caddy) | ✅ Yes |
| 7474 | Neo4j Browser | ❌ SSH tunnel: `ssh -L 7474:localhost:7474 ubuntu@<VM_IP>` |
| 8080 | SearXNG meta-search | ❌ SSH tunnel: `ssh -L 8080:localhost:8080 ubuntu@<VM_IP>` |
| 9001 | MinIO Console | ❌ SSH tunnel: `ssh -L 9001:localhost:9001 ubuntu@<VM_IP>` |
| 8081 → 8080 | Dozzle log viewer | ❌ SSH tunnel: `ssh -L 8081:localhost:8080 ubuntu@<VM_IP>` |
| 8000 | ChromaDB heartbeat | ❌ SSH tunnel: `ssh -L 8000:localhost:8000 ubuntu@<VM_IP>` |

> 🔐 All dashboards stay on the private Docker network and are **not** reachable through Caddy. The host-side port (left of `→`) is yours to choose; the container-side port (right) is what's exposed in `docker-compose.yml`.

---

## 🔄 Step 9: Manage

| Command | Description |
|---------|-------------|
| `make help` | Show every available target |
| `make up` | Build and start everything |
| `make up redis` | Start (or rebuild-restart) a single service |
| `make down` | Stop everything |
| `make restart` | Restart all services |
| `make logs` | Tail last 200 lines from every container |
| `make ps` | Container status |
| `make build` | Rebuild the app image |
| `make pull` | Pull latest infra images (Redis, Neo4j, ChromaDB, SearXNG, MinIO, Dozzle) |
| `make update` | `pull` + rebuild app + restart with orphans removed |
| `make backup` | Snapshot Neo4j, ChromaDB, Redis to `./backups/` |
| `make restore FILE=./backups/xxx.tar.gz` | Restore from a snapshot |
| `make smoke-test` | Hit `/health` on the running app |
| `make clean` | Remove containers + dangling images (volumes kept) |

---

## 🐛 Troubleshooting

| Issue | Fix |
|-------|-----|
| Port 80/443 not accessible | Check both Oracle Security Lists **and** OS firewall (UFW / firewalld) |
| Container won't start | `docker logs ai-stack-<service>` |
| `/health` returns 503 / `degraded` | Inspect the per-service `status` in the body; compare with `/health/live` (always 200) |
| `401 Unauthorized` on every call | Set `AUTH_STRICT=false` in `.env`, or send a valid `X-API-Key` / `Authorization: Bearer <jwt>` header |
| Out of memory | Add swap: `sudo fallocate -l 4G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile` |
| `Permission denied` on `./data` | `sudo chown -R $USER:$USER ./data ./models` (or `chmod -R 777` for a quick fix) |
| Model download fails / hangs | `docker compose restart app` — caches live in `./models/` |
| SearXNG / DDGS returns empty | Provider connectivity issue — API falls back automatically; check logs |
| Playwright browsers crash in `/browse` | Known Docker limitation — `/browse` falls back to fast HTTP for `/crawl` workloads |

---

## 📊 Resource Usage

The stack ships **7 Docker services + Caddy on the host** (Caddy is purposely host-managed so it can bind privileged ports and use Let's Encrypt without `NET_BIND_SERVICE` inside the container).

| Container | Idle RAM | Limit | Host mount |
|-----------|----------|-------|------------|
| App (FastAPI) | ~200 MB | 4 GB | `./models:/root/.cache/huggingface` |
| Neo4j | ~470 MB | unlimited* | `./data/neo4j/data:/data` |
| SearXNG | ~120 MB | 512 MB | `./data/searxng:/etc/searxng` |
| ChromaDB | ~90 MB | 512 MB | `./data/chroma:/chroma/chroma` |
| MinIO | ~90 MB | 512 MB | `./data/minio:/data` |
| Dozzle | ~25 MB | 128 MB | (read-only Docker socket) |
| Redis | ~10 MB | 256 MB | `./data/redis:/data` |
| **Docker total** | **~1 GB idle** | — | — |
| Caddy *(host)* | ~20 MB | — | `/var/log/caddy/access.log` |

\* Neo4j is constrained via `NEO4J_HEAP_MAX` / `NEO4J_PAGECACHE` in `.env`, not a hard cgroup cap.

---

<div align="center">

### 🎉 You're live! Your AI infrastructure is now accessible from anywhere.

</div>
