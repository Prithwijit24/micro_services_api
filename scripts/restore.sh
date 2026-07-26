#!/usr/bin/env bash
# Restores Postgres, Neo4j, ChromaDB, and Redis data from a backup archive
# created by scripts/backup.sh. Meant to be invoked via `make restore FILE=...`.
set -euo pipefail

ARCHIVE="${1:?Usage: restore.sh <path-to-backup.tar.gz>}"
WORKDIR="./backups/restore_tmp_$$"

if [ ! -f "${ARCHIVE}" ]; then
  echo "[restore] ERROR: archive not found: ${ARCHIVE}"
  exit 1
fi

mkdir -p "${WORKDIR}"
tar -xzf "${ARCHIVE}" -C "${WORKDIR}"

echo "[restore] This will overwrite current Postgres, Neo4j, ChromaDB, and Redis data."
read -r -p "Continue? [y/N] " confirm
if [[ "${confirm}" != "y" && "${confirm}" != "Y" ]]; then
  echo "[restore] Aborted."
  rm -rf "${WORKDIR}"
  exit 0
fi

if [ -f "${WORKDIR}/postgres.sql" ]; then
  echo "[restore] Restoring PostgreSQL..."
  docker compose exec -T postgres psql -U "${POSTGRES_USER:-aistack}" -d postgres < "${WORKDIR}/postgres.sql" \
    || echo "[restore] WARNING: postgres restore failed"
fi

if [ -d "${WORKDIR}/neo4j/data" ]; then
  echo "[restore] Restoring Neo4j data (stop neo4j first for consistency)..."
  docker compose stop neo4j || true
  rm -rf ./data/neo4j/data
  cp -a "${WORKDIR}/neo4j/data" ./data/neo4j/data
  docker compose start neo4j || true
fi

if [ -d "${WORKDIR}/chroma" ]; then
  echo "[restore] Restoring ChromaDB data..."
  docker compose stop chromadb || true
  rm -rf ./data/chroma
  mkdir -p ./data/chroma
  cp -a "${WORKDIR}/chroma/." ./data/chroma/
  docker compose start chromadb || true
fi

if [ -f "${WORKDIR}/redis/dump.rdb" ]; then
  echo "[restore] Restoring Redis dump..."
  docker compose stop redis || true
  cp -a "${WORKDIR}/redis/dump.rdb" ./data/redis/dump.rdb
  docker compose start redis || true
fi

rm -rf "${WORKDIR}"
echo "[restore] Done."
