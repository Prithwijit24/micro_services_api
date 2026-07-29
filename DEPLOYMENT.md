<div align="center">

# ☁️ Oracle Cloud VM Deployment Guide

### *Step-by-step guide to deploy AI Infra Stack on Oracle Cloud Free Tier*

</div>

---

## 📋 Prerequisites Checklist

- [ ] Oracle Cloud account ([sign up free](https://cloud.oracle.com/))
- [ ] A domain name (optional — for HTTPS)
- [ ] Terminal/SSH client on your local machine
- [ ] ~15 minutes of your time

---

## 🏗️ Step 1: Create Oracle Cloud VM

### 1.1 Log in to Oracle Cloud Console

👉 **[https://cloud.oracle.com/](https://cloud.oracle.com/)**

### 1.2 Create a VM Instance

1. Click **☰ Menu** → **Compute** → **Instances** → **Create Instance**
2. **Name:** `ai-infra-stack`
3. **Image:** Choose **Ubuntu 24.04** or **Oracle Linux 9**
4. **Shape:** Select a **Free Tier** eligible shape:
   - **ARM (recommended):** `VM.Standard.A1.Flex` (4 OCPUs, 24GB RAM) ✅
   - **AMD:** `VM.Standard.E2.1.Micro` (1 OCPU, 1GB RAM) ⚠️ too small
5. **Add SSH Keys:** Paste your public key (see Step 1.3 below)
6. Click **Create**

### 1.3 Generate SSH Key (if you don't have one)

Run this on **your local machine** (not the VM):

```bash
# Generate SSH key pair
ssh-keygen -t rsa -N "" -b 2048 -C "ai-stack-key" -f ~/.ssh/oci_vm_key

# Display the public key (copy this — you'll paste it into Oracle Cloud)
cat ~/.ssh/oci_vm_key.pub
```

### 1.4 Note Your VM's Public IP

After the VM is created, copy the **Public IP address** from the instance details page.

---

## 🔓 Step 2: Open Ports (Two Layers)

> ⚠️ **Important:** Oracle Cloud has **two firewall layers**. Both must be configured!

### 2.1 Layer 1: Oracle Cloud Security Lists (Cloud Firewall)

1. Go to **☰ Menu** → **Networking** → **Virtual Cloud Networks**
2. Click your VCN → Click your **Public Subnet**
3. Under **Resources**, click **Security Lists**
4. Click **Add Ingress Rules**

Add these rules one by one:

| # | Source CIDR | Protocol | Port | Purpose |
|---|-------------|----------|------|---------|
| 1 | `0.0.0.0/0` | TCP | `80` | HTTP (Caddy) |
| 2 | `0.0.0.0/0` | TCP | `443` | HTTPS (Caddy) |

👉 **Official Docs:** [Oracle Security Lists Guide](https://docs.oracle.com/iaas/Content/Network/Concepts/securitylists.htm)

### 2.2 Layer 2: OS-Level Firewall (VM Firewall)

SSH into your VM and run:

**For Ubuntu:**
```bash
# Check if ufw is active
sudo ufw status

# If active, open ports
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw reload
```

**For Oracle Linux:**
```bash
# Open ports in firewalld
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

---

## 🔌 Step 3: Connect to Your VM

```bash
# Connect using your SSH key
ssh -i ~/.ssh/oci_vm_key ubuntu@<YOUR_VM_PUBLIC_IP>

# Example:
ssh -i ~/.ssh/oci_vm_key ubuntu@129.153.xxx.xxx
```

---

## 🐳 Step 4: Install Docker

Run these commands **inside your VM**:

```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install prerequisites
sudo apt-get install -y ca-certificates curl gnupg

# Add Docker's official GPG key
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Add Docker repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine + Compose plugin
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Allow running docker without sudo
sudo usermod -aG docker $USER

# Apply group changes (or log out and back in)
newgrp docker

# Verify Docker works
docker --version
docker compose version
```

👉 **Official Docs:** [Docker Install on Ubuntu](https://docs.docker.com/engine/install/ubuntu/)

---

## 📦 Step 5: Deploy AI Infra Stack

### 5.1 Clone the Repository

```bash
# Clone the repo
git clone <your-repo-url> ai-infra-stack
cd ai-infra-stack
```

### 5.2 Configure Environment

```bash
# Copy example env file
cp .env.example .env

# Edit with your settings
nano .env
```

**Key settings to change:**

```bash
# Set your domain (optional — leave as localhost for IP-only access)
DOMAIN=localhost

# Set REAL passwords (never use defaults in production!)
NEO4J_PASSWORD=your_strong_password_here
MYSQL_PASSWORD=your_strong_password_here
MYSQL_ROOT_PASSWORD=your_strong_password_here
MINIO_ROOT_PASSWORD=your_strong_password_here
```

### 5.3 Start the Stack

```bash
# Build and start everything
make up

# This will:
# - Build the FastAPI app image (~5-10 min first time)
# - Download AI models (~500MB)
# - Start all 12 containers
```

### 5.4 Verify It Works

```bash
# Check container status
make ps

# Test health endpoint
curl http://localhost/health
# Expected output: {"status":"ok"}

# Run full smoke test
make smoke-test
```

---

## 🌐 Step 6: Get Your Public URL

### Option A: Direct IP Access (Quickest)

```
http://<YOUR_VM_PUBLIC_IP>
```

**Example:** `http://129.153.xxx.xxx`

### Option B: Domain with Free HTTPS (Recommended)

1. **Point your domain's DNS** to your VM:
   - Create an **A Record**: `@` → `<YOUR_VM_PUBLIC_IP>`
   - Create an **A Record**: `www` → `<YOUR_VM_PUBLIC_IP>`

2. **Update `.env`:**
   ```bash
   DOMAIN=yourdomain.com
   CADDY_ACME_EMAIL=you@email.com
   ```

3. **Restart Caddy:**
   ```bash
   make restart
   ```

4. **Your API is now at:** `https://yourdomain.com`

👉 **Caddy auto-renews SSL certificates** — no manual renewal needed!

---

## 🧪 Step 7: Test Your API

### Quick Test

```bash
# Health check
curl http://<YOUR_VM_IP>/health

# Search
curl -X POST http://<YOUR_VM_IP>/search \
  -H "Content-Type: application/json" \
  -d '{"query": "hello world", "max_results": 3}'

# Full pipeline
curl -X POST http://<YOUR_VM_IP>/pipeline \
  -H "Content-Type: application/json" \
  -d '{"query": "what is python?", "top_k": 3}'
```

### From Your Local Machine

```bash
# Test from your laptop
curl http://<YOUR_VM_PUBLIC_IP>/health
# → {"status":"ok"}

# Test API from Python
python3 -c "
import httpx
r = httpx.post('http://<YOUR_VM_PUBLIC_IP>/search', json={'query': 'test', 'max_results': 2})
print(r.json())
"
```

---

## 🔐 Step 8: Security Hardening (Recommended)

### 8.1 Change All Default Passwords

Edit `.env` and set unique passwords for:
- `NEO4J_PASSWORD`
- `MYSQL_PASSWORD`
- `MYSQL_ROOT_PASSWORD`
- `MINIO_ROOT_PASSWORD`

### 8.2 Restrict Dashboard Access

Only expose ports you actually need in Oracle Cloud Security Lists:

| Port | Service | Expose? |
|------|---------|---------|
| 80 | API (Caddy) | ✅ Yes |
| 443 | API (HTTPS) | ✅ Yes |
| 7474 | Neo4j Browser | ❌ No (unless needed) |
| 9001 | MinIO Console | ❌ No (unless needed) |
| 3001 | Uptime Kuma | ❌ No (unless needed) |
| 8081 | Dozzle Logs | ❌ No (unless needed) |

### 8.3 Optional: Set Up UFW Firewall

```bash
# Allow only SSH and HTTP/HTTPS
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

---

## 🔄 Step 9: Manage Your Stack

### Common Commands

| Command | Description |
|---------|-------------|
| `make up` | Start everything |
| `make down` | Stop everything |
| `make restart` | Restart all containers |
| `make logs` | Tail all logs |
| `make ps` | Show container status |
| `make backup` | Backup databases |
| `make update` | Pull latest images + rebuild |

### View Logs

```bash
# All services
make logs

# Specific service
docker logs ai-stack-app --tail 50

# Watch logs in real-time
docker logs -f ai-stack-app
```

### Restart After Changes

```bash
# After editing .env
make restart

# After code changes
make build
make restart
```

---

## 🐛 Troubleshooting

### Port 80/443 Not Accessible

```bash
# 1. Check Oracle Cloud Security Lists (Step 2.1)
# 2. Check OS firewall
sudo ufw status          # Ubuntu
sudo firewall-cmd --list-all  # Oracle Linux

# 3. Check if Caddy is running
docker ps | grep caddy
docker logs ai-stack-caddy
```

### Container Won't Start

```bash
# Check container status
docker ps -a | grep <service-name>

# View logs
docker logs ai-stack-<service-name>

# Restart specific service
docker compose restart <service-name>
```

### Out of Memory

```bash
# Check memory usage
free -h
docker stats --no-stream

# If swap is needed
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### Model Download Fails

```bash
# Models are cached in ./models/
# If download fails, retry:
docker compose restart app

# Or manually trigger model download
docker exec -it ai-stack-app python3 -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-small-en-v1.5')"
```

---

## 📊 Monitoring

### Check All Services

```bash
# Quick status
docker ps --format 'table {{.Names}}\t{{.Status}}'

# Resource usage
docker stats --no-stream
```

### Access Dashboards (if ports are open)

| Dashboard | URL | What it shows |
|-----------|-----|---------------|
| **Uptime Kuma** | `http://<IP>:3001` | Service uptime monitoring |
| **Dozzle** | `http://<IP>:8081` | Real-time container logs |
| **Neo4j Browser** | `http://<IP>:7474` | Graph database explorer |
| **MinIO Console** | `http://<IP>:9001` | File storage management |

---

## 🎯 Quick Reference Card

```
┌─────────────────────────────────────────────────────────────┐
│  AI INFRA STACK — QUICK REFERENCE                           │
├─────────────────────────────────────────────────────────────┤
│  URL:        http://<VM_IP>  or  https://yourdomain.com    │
│  Health:     GET /health                                    │
│  API Docs:   (auto-generated by FastAPI)                   │
│  Logs:       make logs                                      │
│  Status:     make ps                                        │
│  Restart:    make restart                                   │
│  Backup:     make backup                                    │
├─────────────────────────────────────────────────────────────┤
│  Ports:      80 (HTTP), 443 (HTTPS)                        │
│  Dashboard:  :3001 (Uptime), :8081 (Logs)                  │
│  Database:   :7474 (Neo4j), :3306 (MySQL)                  │
│  Storage:    :9000 (MinIO API), :9001 (MinIO UI)           │
├─────────────────────────────────────────────────────────────┤
│  Support:    docker logs ai-stack-app                       │
│  Cleanup:    make clean                                     │
│  Update:     git pull && make update                        │
└─────────────────────────────────────────────────────────────┘
```

---

## 📚 Useful Links

| Resource | URL |
|----------|-----|
| Oracle Cloud Console | [cloud.oracle.com](https://cloud.oracle.com/) |
| Docker Docs | [docs.docker.com](https://docs.docker.com/) |
| FastAPI Docs | [fastapi.tiangolo.com](https://fastapi.tiangolo.com/) |
| Oracle Security Lists | [docs.oracle.com/iaas/Content/Network/Concepts/securitylists.htm](https://docs.oracle.com/iaas/Content/Network/Concepts/securitylists.htm) |
| Docker Install (Ubuntu) | [docs.docker.com/engine/install/ubuntu](https://docs.docker.com/engine/install/ubuntu/) |
| Oracle Linux Docker | [docs.oracle.com/en/operating-systems/oracle-linux/docker](https://docs.oracle.com/en/operating-systems/oracle-linux/docker/docker-InstallingOracleContainerRuntimeforDocker.html) |

---

## ✅ Post-Deployment Checklist

- [ ] VM is running and accessible via SSH
- [ ] Docker is installed and working
- [ ] All 12 containers are running (`make ps`)
- [ ] Health check passes (`curl http://<IP>/health`)
- [ ] Oracle Cloud Security Lists allow ports 80/443
- [ ] OS firewall allows ports 80/443
- [ ] All default passwords changed
- [ ] (Optional) Domain configured with HTTPS
- [ ] (Optional) Uptime Kuma set up for monitoring

---

<div align="center">

### 🎉 You're live! Your AI infrastructure is now accessible from anywhere.

**Built with ❤️ using FastAPI, Docker, and open-source AI models**

</div>
