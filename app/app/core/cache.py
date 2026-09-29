"""Redis cache realisation"""

import json
from collections.abc import Awaitable, Callable
from typing import Any

from redis.asyncio import Redis


class Cache:
    """Async Redis cache abstraction."""

    def __init__(self, redis: Redis):
        self.redis = redis

    async def get(self, key: str) -> Any | None:
        value = await self.redis.get(key)

        if value is None:
            return None

        return json.loads(value)

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int,
    ) -> None:
        await self.redis.set(
            key,
            json.dumps(value, default=str),
            ex=ttl,
        )

    async def delete(self, key: str) -> None:
        await self.redis.delete(key)

    async def get_or_set(
        self,
        key: str,
        factory: Callable[[], Awaitable[Any]],
        ttl: int,
    ) -> Any:
        cached = await self.get(key)

        if cached is not None:
            return cached

        value = await factory()

        await self.set(key, value, ttl)

        return value
