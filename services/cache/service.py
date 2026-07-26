import os
import json
import logging

import redis.asyncio as redis

logger = logging.getLogger("cache")

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")


class CacheService:
    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None:
            self._client = redis.from_url(REDIS_URL, decode_responses=True)
        return self._client

    async def set(self, key: str, value, ttl_seconds: int | None = None) -> bool:
        client = self._get_client()
        payload = json.dumps(value)
        if ttl_seconds:
            await client.set(key, payload, ex=ttl_seconds)
        else:
            await client.set(key, payload)
        return True

    async def get(self, key: str):
        client = self._get_client()
        raw = await client.get(key)
        if raw is None:
            return None, False
        return json.loads(raw), True

    async def delete(self, key: str) -> bool:
        client = self._get_client()
        deleted = await client.delete(key)
        return deleted > 0

    async def close(self):
        if self._client is not None:
            await self._client.aclose()


cache_service = CacheService()
