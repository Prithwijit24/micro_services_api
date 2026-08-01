"""Lazy-loaded shared resources. Heavy models load on first use, not at startup."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import httpx
    import redis.asyncio as redis


# ── HTTP Client (shared across search, crawl, gateway) ─────────────────────

_http_client: httpx.AsyncClient | None = None


def get_http_client() -> httpx.AsyncClient:
    import httpx

    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(timeout=30.0)
    return _http_client


# ── Redis Client (shared across cache) ────────────────────────────────────

_redis_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    import redis.asyncio as aioredis

    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            os.getenv("REDIS_URL", "redis://redis:6379/0"),
            decode_responses=True,
        )
    return _redis_client


async def close_shared_clients() -> None:
    """Close shared network clients during application shutdown."""
    global _http_client, _redis_client
    if _http_client is not None:
        await _http_client.aclose()
        _http_client = None
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None


# ── Embedding Model (lazy) ────────────────────────────────────────────────

_embed_model: Any = None


def get_embed_model() -> Any:
    from sentence_transformers import SentenceTransformer

    global _embed_model
    if _embed_model is None:
        name = os.getenv("EMBED_MODEL", "BAAI/bge-small-en-v1.5")
        _embed_model = SentenceTransformer(name, cache_folder=os.getenv("HF_HOME"))
    return _embed_model


# ── CLIP Model (lazy) ─────────────────────────────────────────────────────

_clip_model: Any = None
_clip_processor: Any = None


def get_clip_model() -> tuple[Any, Any]:
    from transformers import CLIPModel, CLIPProcessor

    global _clip_model, _clip_processor
    if _clip_model is None:
        name = os.getenv("CLIP_MODEL", "openai/clip-vit-base-patch32")
        _clip_model = CLIPModel.from_pretrained(name, cache_dir=os.getenv("HF_HOME"))
        _clip_processor = CLIPProcessor.from_pretrained(name, cache_dir=os.getenv("HF_HOME"))
    return _clip_model, _clip_processor


# ── Reranker Model (lazy) ─────────────────────────────────────────────────

_reranker_model: Any = None


def get_reranker_model() -> Any:
    from sentence_transformers import CrossEncoder

    global _reranker_model
    if _reranker_model is None:
        name = os.getenv("RERANK_MODEL", "BAAI/bge-reranker-v2-m3")
        _reranker_model = CrossEncoder(name, cache_folder=os.getenv("HF_HOME"))
    return _reranker_model
