from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.auth import router as auth_router
from app.deps import close_shared_clients, get_http_client
from app.models import DuckDBQueryRequest, HealthResponse, LivenessResponse, RootResponse
from app.routers import register_all_routers
from app.routers.graph import svc as graph_service
from app.services.duckdb import duckdb_service
from app.services.storage import storage_service
from app.services.crawl import close as close_crawl
from app.services.clip import close as close_clip
from app.services.embed import close as close_embed
from app.services.reranker import close as close_reranker
from app.services.youtube import close as close_youtube
from app.middleware import setup_security

HEALTH_TIMEOUT = float(os.getenv("HEALTH_TIMEOUT", "3.0"))


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    await close_shared_clients()
    await graph_service.close()
    duckdb_service.close()
    storage_service.close()
    close_crawl()
    close_clip()
    close_embed()
    close_reranker()
    close_youtube()


app = FastAPI(
    title="AI Infra Stack",
    description="Unified API for search, browse, embed, and more",
    version="2.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

setup_security(app)
app.include_router(auth_router)
register_all_routers(app)


@app.get("/", response_model=RootResponse)
async def root():
    return {
        "service": "AI Infra Stack",
        "version": "2.1.0",
        "docs": "/docs",
        "health": "/health",
        "liveness": "/health/live",
    }


@app.get("/health/live", response_model=LivenessResponse)
async def liveness():
    return {"status": "ok"}


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

        driver = AsyncGraphDatabase.driver(
            os.getenv("NEO4J_URI", "bolt://neo4j:7687"),
            auth=(
                os.getenv("NEO4J_USER", "neo4j"),
                os.getenv("NEO4J_PASSWORD", "changeme"),
            ),
        )
        async with driver.session() as session:
            result = await asyncio.wait_for(session.run("RETURN 1"), timeout=HEALTH_TIMEOUT)
            await asyncio.wait_for(result.consume(), timeout=HEALTH_TIMEOUT)
        return {"status": "up"}
    except Exception:
        return {"status": "down", "error": "unreachable"}
    finally:
        if driver is not None:
            await driver.close()


async def _check_chromadb() -> dict:
    try:
        import chromadb

        client = chromadb.HttpClient(
            host=os.getenv("CHROMA_HOST", "chromadb"),
            port=int(os.getenv("CHROMA_PORT", "8000")),
        )
        await asyncio.wait_for(asyncio.to_thread(client.heartbeat), timeout=HEALTH_TIMEOUT)
        return {"status": "up"}
    except Exception:
        return {"status": "down", "error": "unreachable"}


async def _check_searxng() -> dict:
    try:
        url = os.getenv("SEARXNG_URL", "http://searxng:8080")
        response = await asyncio.wait_for(
            get_http_client().get(f"{url}/healthz"), timeout=HEALTH_TIMEOUT
        )
        response.raise_for_status()
        return {"status": "up"}
    except Exception:
        return {"status": "down", "error": "unreachable"}


async def _check_minio() -> dict:
    try:
        from minio import Minio

        client = Minio(
            os.getenv("MINIO_ENDPOINT", "minio:9000"),
            access_key=os.getenv("MINIO_ROOT_USER", "minioadmin"),
            secret_key=os.getenv("MINIO_ROOT_PASSWORD", "minioadmin"),
            secure=os.getenv("MINIO_SECURE", "false").lower() == "true",
        )
        await asyncio.wait_for(asyncio.to_thread(client.list_buckets), timeout=HEALTH_TIMEOUT)
        return {"status": "up"}
    except Exception:
        return {"status": "down", "error": "unreachable"}


async def _check_duckdb() -> dict:
    try:
        result = await duckdb_service.query(DuckDBQueryRequest(sql="SELECT 1"))
        return {"status": "up"} if result.error is None else {"status": "down", "error": "unreachable"}
    except Exception:
        return {"status": "down", "error": "unreachable"}


@app.get("/health", response_model=HealthResponse)
async def health():
    checks = await asyncio.gather(
        _check_redis(),
        _check_neo4j(),
        _check_chromadb(),
        _check_searxng(),
        _check_minio(),
        _check_duckdb(),
    )
    services = dict(zip(("redis", "neo4j", "chromadb", "searxng", "minio", "duckdb"), checks))
    ready = all(service["status"] == "up" for service in services.values())
    body = {"status": "ok" if ready else "degraded", "services": services}
    return JSONResponse(status_code=200 if ready else 503, content=body)
