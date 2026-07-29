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
nano .env   # set real passwords!

# Start (first run takes ~10 min)
make up

# Verify
curl http://localhost/health
# → {"status":"ok"}
```

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

```bash
curl http://<YOUR_VM_IP>/health

curl -X POST http://<YOUR_VM_IP>/pipeline \
  -H "Content-Type: application/json" \
  -d '{"query": "what is python?", "top_k": 3}'
```

---

## 🔐 Step 8: Security

### Change Default Passwords

Edit `.env` and set unique passwords for:
- `NEO4J_PASSWORD`
- `MINIO_ROOT_PASSWORD`

### Dashboard Ports (only open if needed)

| Port | Service | Expose? |
|------|---------|---------|
| 80 | API | ✅ Yes |
| 443 | API (HTTPS) | ✅ Yes |
| 7474 | Neo4j Browser | ❌ Unless needed |
| 9001 | MinIO Console | ❌ Unless needed |
| 8081 | Dozzle Logs | ❌ Unless needed |

---

## 🔄 Step 9: Manage

| Command | Description |
|---------|-------------|
| `make up` | Start everything |
| `make down` | Stop everything |
| `make restart` | Restart all |
| `make logs` | Tail logs |
| `make ps` | Container status |
| `make backup` | Backup databases |
| `make update` | Pull latest + rebuild |

---

## 🐛 Troubleshooting

| Issue | Fix |
|-------|-----|
| Port 80/443 not accessible | Check both Oracle Security Lists AND OS firewall |
| Container won't start | `docker logs ai-stack-<service>` |
| Out of memory | Add swap: `sudo fallocate -l 4G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile` |
| Model download fails | `docker compose restart app` |

---

## 📊 Resource Usage

| Container | Idle RAM | Limit |
|-----------|----------|-------|
| App | ~200 MB | 4 GB |
| Neo4j | ~470 MB | unlimited |
| SearXNG | ~120 MB | 512 MB |
| ChromaDB | ~90 MB | 512 MB |
| MinIO | ~90 MB | 512 MB |
| Dozzle | ~25 MB | 128 MB |
| Caddy | ~20 MB | 128 MB |
| Redis | ~10 MB | 256 MB |
| **Total idle** | **~1 GB** | — |

---

<div align="center">

### 🎉 You're live! Your AI infrastructure is now accessible from anywhere.

</div>
