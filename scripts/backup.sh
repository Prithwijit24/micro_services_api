#!/usr/bin/env bash
# Backs up Postgres, Neo4j, ChromaDB, and Redis data into a single timestamped
# tarball under ./backups. Meant to be invoked via `make backup`.
set -euo pipefail

TIMESTAMP="${1:-$(date +%Y%m%d_%H%M%S)}"
BACKUP_ROOT="./backups"
WORKDIR="${BACKUP_ROOT}/tmp_${TIMESTAMP}"
ARCHIVE="${BACKUP_ROOT}/aistack_backup_${TIMESTAMP}.tar.gz"

mkdir -p "${WORKDIR}"

echo "[backup] Dumping PostgreSQL..."
docker compose exec -T postgres pg_dumpall -U "${POSTGRES_USER:-aistack}" > "${WORKDIR}/postgres.sql" \
  || echo "[backup] WARNING: postgres dump failed (is the container running?)"

echo "[backup] Snapshotting Neo4j data directory..."
mkdir -p "${WORKDIR}/neo4j"
cp -a ./data/neo4j/data "${WORKDIR}/neo4j/" 2>/dev/null \
  || echo "[backup] WARNING: neo4j data copy failed"

echo "[backup] Snapshotting ChromaDB data directory..."
mkdir -p "${WORKDIR}/chroma"
cp -a ./data/chroma/. "${WORKDIR}/chroma/" 2>/dev/null \
  || echo "[backup] WARNING: chroma data copy failed"

echo "[backup] Dumping Redis (RDB snapshot)..."
docker compose exec -T redis redis-cli -a "${REDIS_PASSWORD:-changeme}" --no-auth-warning SAVE \
  || echo "[backup] WARNING: redis SAVE failed"
mkdir -p "${WORKDIR}/redis"
cp -a ./data/redis/dump.rdb "${WORKDIR}/redis/" 2>/dev/null \
  || echo "[backup] WARNING: redis dump copy failed"

echo "[backup] Creating archive ${ARCHIVE}..."
tar -czf "${ARCHIVE}" -C "${WORKDIR}" .
rm -rf "${WORKDIR}"

echo "[backup] Done: ${ARCHIVE}"
