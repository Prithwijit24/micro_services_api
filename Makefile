SHELL := /bin/bash
COMPOSE := docker compose
PROJECT := ai-stack
BACKUP_DIR := ./backups
TIMESTAMP := $(shell date +%Y%m%d_%H%M%S)

ALL_SERVICES := postgres redis neo4j chromadb searxng firecrawl browser youtube embed clip reranker \
                search crawl graph vector cache gateway caddy uptime-kuma dozzle

APP_SERVICES := search crawl graph vector cache embed clip reranker

.PHONY: help up down restart logs pull build update ps backup restore clean env-check \
        $(addprefix start-,$(ALL_SERVICES)) $(addprefix stop-,$(ALL_SERVICES)) \
        $(addprefix logs-,$(ALL_SERVICES)) shell test smoke-test

## ---------------------------------------------------------------------------
## General help
## ---------------------------------------------------------------------------
help: ## Show this help
	@echo "AI Infrastructure Stack — available targets:"
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'

## ---------------------------------------------------------------------------
## Top level lifecycle
## ---------------------------------------------------------------------------
env-check: ## Ensure .env exists (copies from .env.example if missing)
	@if [ ! -f .env ]; then \
		echo ".env not found — creating from .env.example"; \
		cp .env.example .env; \
	fi

up: env-check ## Build and start the entire stack in the background
	$(COMPOSE) up -d --build

down: ## Stop and remove all containers (volumes are preserved)
	$(COMPOSE) down

restart: ## Restart every service
	$(COMPOSE) restart

logs: ## Tail logs from all services
	$(COMPOSE) logs -f --tail=200

pull: ## Pull the latest images for infra services (Postgres, Redis, Neo4j, etc.)
	$(COMPOSE) pull postgres redis neo4j chromadb searxng firecrawl uptime-kuma dozzle caddy

build: env-check ## Build (or rebuild) all custom microservice images
	$(COMPOSE) build

update: pull build ## Pull latest infra images, rebuild app images, and recreate containers
	$(COMPOSE) up -d --remove-orphans

ps: ## Show status of all containers
	$(COMPOSE) ps

clean: ## Stop stack and remove containers, networks, and dangling images (data volumes kept)
	$(COMPOSE) down --remove-orphans
	docker image prune -f

## ---------------------------------------------------------------------------
## Backup / restore
## ---------------------------------------------------------------------------
backup: ## Backup Postgres, Neo4j, ChromaDB, and Redis data to ./backups
	@mkdir -p $(BACKUP_DIR)
	@bash scripts/backup.sh $(TIMESTAMP)

restore: ## Restore from a backup. Usage: make restore FILE=./backups/xxxx.tar.gz
	@if [ -z "$(FILE)" ]; then echo "Usage: make restore FILE=./backups/<archive>.tar.gz"; exit 1; fi
	@bash scripts/restore.sh $(FILE)

## ---------------------------------------------------------------------------
## Per-service start/stop/logs
## Usage: make start-embed / make stop-embed / make logs-embed
## ---------------------------------------------------------------------------
$(addprefix start-,$(ALL_SERVICES)): start-%: env-check
	$(COMPOSE) up -d --build $*

$(addprefix stop-,$(ALL_SERVICES)): stop-%:
	$(COMPOSE) stop $*

$(addprefix logs-,$(ALL_SERVICES)): logs-%:
	$(COMPOSE) logs -f --tail=200 $*

# Convenience shortcuts matching the exact names requested in the spec
postgres: start-postgres ## Start Postgres only
redis: start-redis ## Start Redis only
neo4j: start-neo4j ## Start Neo4j only
chromadb: start-chromadb ## Start ChromaDB only
firecrawl: start-firecrawl ## Start Firecrawl only
browser: start-browser ## Start Browser service only
youtube: start-youtube ## Start YouTube service only
embed: start-embed ## Start Embed service only
clip: start-clip ## Start CLIP service only
reranker: start-reranker ## Start Reranker service only
search: start-search ## Start Search service only

stop-all-app-services: ## Stop just the FastAPI microservices, leave infra running
	$(COMPOSE) stop $(APP_SERVICES) gateway

## ---------------------------------------------------------------------------
## Dev / debug
## ---------------------------------------------------------------------------
shell: ## Open a shell in a running service container. Usage: make shell SVC=embed
	@if [ -z "$(SVC)" ]; then echo "Usage: make shell SVC=<service-name>"; exit 1; fi
	$(COMPOSE) exec $(SVC) /bin/bash || $(COMPOSE) exec $(SVC) /bin/sh

test: ## Run local unit/smoke tests for the FastAPI apps (no Docker required)
	bash scripts/run_tests.sh

smoke-test: ## Hit /health on every running service through the gateway
	bash scripts/smoke_test.sh
