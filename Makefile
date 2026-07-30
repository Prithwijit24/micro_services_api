SHELL := /bin/bash
COMPOSE := docker compose
BACKUP_DIR := ./backups
TIMESTAMP := $(shell date +%Y%m%d_%H%M%S)

.PHONY: help up down logs build restart ps clean backup restore smoke-test pull update

## ─── General ─────────────────────────────────────────────────────────────────
help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

## ─── Lifecycle ───────────────────────────────────────────────────────────────
SERVICES := app redis neo4j chromadb searxng minio dozzle beszel beszel-agent

# Positional arg after `up` (e.g. `make up redis`)
SERVICE := $(filter-out up,$(MAKECMDGOALS))

# Suppress 'make: *** No rule to make target' for service names
$(filter-out up,$(MAKECMDGOALS)):
	@:

up: ## Build and start everything (or specific: make up <service>)
	@test -f .env || cp .env.example .env
	@set -e; \
	  if [ -n "$(SERVICE)" ] && ! echo '$(SERVICES)' | tr ' ' '\n' | grep -qx '$(SERVICE)'; then \
	    echo '\033[31mError: "$(SERVICE)" is not a valid service.\033[0m'; \
	    echo ''; \
	    echo 'Available services:'; \
	    echo '$(SERVICES)' | tr ' ' '\n' | awk '{printf "  \033[36m%s\033[0m\n", $$1}'; \
	    echo ''; \
	    exit 1; \
	  fi; \
	  $(COMPOSE) up -d --build $(SERVICE)

down: ## Stop everything
	$(COMPOSE) down

restart: ## Restart all services
	$(COMPOSE) restart

logs: ## Tail logs from all services
	$(COMPOSE) logs -f --tail=200

ps: ## Show container status
	$(COMPOSE) ps

## ─── Build ───────────────────────────────────────────────────────────────────
build: ## Rebuild the app image
	$(COMPOSE) build app

pull: ## Pull latest infra images
	$(COMPOSE) pull redis neo4j chromadb searxng minio dozzle

update: pull build ## Pull latest images and rebuild app
	$(COMPOSE) up -d --remove-orphans

## ─── Cleanup ─────────────────────────────────────────────────────────────────
clean: ## Remove containers + dangling images (data volumes kept)
	$(COMPOSE) down --remove-orphans
	docker image prune -f

## ─── Backup / Restore ────────────────────────────────────────────────────────
backup: ## Backup Neo4j, ChromaDB, and Redis
	@mkdir -p $(BACKUP_DIR)
	@bash scripts/backup.sh $(TIMESTAMP)

restore: ## Restore from backup. Usage: make restore FILE=./backups/xxx.tar.gz
	@if [ -z "$(FILE)" ]; then echo "Usage: make restore FILE=./backups/<archive>.tar.gz"; exit 1; fi
	@bash scripts/restore.sh $(FILE)

## ─── Testing ─────────────────────────────────────────────────────────────────
smoke-test: ## Hit /health on app through gateway
	@bash scripts/smoke_test.sh
