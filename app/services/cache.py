"""Cache service via Redis."""

import json
import logging

from app.deps import get_redis
from app.models import CacheSetResponse, CacheGetResponse, CacheDeleteResponse

logger = logging.getLogger("cache")


class CacheService:
    async def set(self, key: str, value, ttl_seconds: int | None = None) -> bool:
        client = get_redis()
        payload = json.dumps(value)
        if ttl_seconds:
            await client.set(key, payload, ex=ttl_seconds)
        else:
            await client.set(key, payload)
        return True

    async def get(self, key: str):
        client = get_redis()
        raw = await client.get(key)
        if raw is None:
            return None, False
        return json.loads(raw), True

    async def delete(self, key: str) -> bool:
        client = get_redis()
        deleted = await client.delete(key)
        return deleted > 0
