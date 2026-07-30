import asyncio
import os

from fastapi import FastAPI

from app.routers import register_all_routers
from app.middleware import setup_security
from app.auth import router as auth_router

app = FastAPI(
    title="AI Infra Stack",
    description="Unified API for search, browse, embed, and more",
    version="2.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Security middleware (CORS, rate limiting, auth, headers)
setup_security(app)

# Auth routes (token generation, API key management)
app.include_router(auth_router)

# All service routers
register_all_routers(app)


@app.get("/")
async def root():
    return {
        "service": "AI Infra Stack",
        "version": "2.1.0",
        "docs": "/docs",
        "health": "/health",
    }


# ── Health-check timeout per service ───────────────────────────────────────

HEALTH_TIMEOUT = float(os.getenv("HEALTH_TIMEOUT", "3.0"))


async def _check_redis() -> dict:
    r = None
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(
            os.getenv("REDIS_URL", "redis://redis:6379/0"),
            socket_connect_timeout=HEALTH_TIMEOUT,
        )
        await asyncio.wait_for(r.ping(), timeout=HEALTH_TIMEOUT)
        return {"status": "up"}
    except Exception:
        return {"status": "down", "error": "unreachable"}
    finally:
        if r is not None:
            await r.aclose()


async def _check_neo4j() -> dict:
    driver = None
    try:
        from neo4j import AsyncGraphDatabase
        uri = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "changeme")
        driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
        async with driver.session() as session:
            await asyncio.wait_for(
                session.run("RETURN 1"), timeout=HEALTH_TIMEOUT
            )
        return {"status": "up"}
    except Exception:
        return {"status": "down", "error": "unreachable"}
    finally:
        if driver is not None:
            await driver.close()


async def _check_chromadb() -> dict:
    try:
        import chromadb
        host = os.getenv("CHROMA_HOST", "chromadb")
        port = int(os.getenv("CHROMA_PORT", "8000"))
        client = chromadb.HttpClient(host=host, port=port)
        await asyncio.wait_for(
            asyncio.to_thread(client.heartbeat), timeout=HEALTH_TIMEOUT
        )
        return {"status": "up"}
    except Exception:
        return {"status": "down", "error": "unreachable"}


async def _check_searxng() -> dict:
    try:
        from app.deps import get_http_client
        url = os.getenv("SEARXNG_URL", "http://searxng:8080")
        client = get_http_client()
        resp = await asyncio.wait_for(
            client.get(f"{url}/healthz"), timeout=HEALTH_TIMEOUT
        )
        resp.raise_for_status()
        return {"status": "up"}
    except Exception:
        return {"status": "down", "error": "unreachable"}


async def _check_minio() -> dict:
    try:
        from minio import Minio
        endpoint = os.getenv("MINIO_ENDPOINT", "minio:9000")
        access_key = os.getenv("MINIO_ROOT_USER", "minioadmin")
        secret_key = os.getenv("MINIO_ROOT_PASSWORD", "minioadmin")
        client = Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=False)
        await asyncio.wait_for(
            asyncio.to_thread(client.list_buckets), timeout=HEALTH_TIMEOUT
        )
        return {"status": "up"}
    except Exception:
        return {"status": "down", "error": "unreachable"}


async def _check_duckdb() -> dict:
    try:
        import duckdb
        con = duckdb.connect(":memory:")
        await asyncio.wait_for(
            asyncio.to_thread(lambda: con.execute("SELECT 1").fetchall()),
            timeout=HEALTH_TIMEOUT,
        )
        con.close()
        return {"status": "up"}
    except Exception:
        return {"status": "down", "error": "unreachable"}


@app.get("/health")
async def health():
    checks = await asyncio.gather(
        _check_redis(),
        _check_neo4j(),
        _check_chromadb(),
        _check_searxng(),
        _check_minio(),
        _check_duckdb(),
        return_exceptions=True,
    )
    services = {
        "redis": checks[0],
        "neo4j": checks[1],
        "chromadb": checks[2],
        "searxng": checks[3],
        "minio": checks[4],
        "duckdb": checks[5],
    }
    all_up = all(s["status"] == "up" for s in services.values())
    return {
        "status": "ok" if all_up else "degraded",
        "services": services,
    }
