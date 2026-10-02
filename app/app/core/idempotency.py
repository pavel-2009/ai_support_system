"""Простая работа с Idempotency-Key."""

import json
from enum import Enum

from redis.asyncio import Redis


class IdempotencyStatus(str, Enum):
    """Статусы Idempotency-Key."""

    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class IdempotencyKey:
    """Хранит состояние запроса в Redis."""

    def __init__(self, redis: Redis):
        self.redis = redis

    async def get(self, key: str) -> dict | None:
        """Get the state of the request by key. Returns None if the key does not exist."""
        value = await self.redis.get(key)
        if value is None:
            return None
        if isinstance(value, bytes):
            value = value.decode("utf-8")
        return json.loads(value)

    async def reserve(self, key: str, fingerprint: str, ttl: int = 300) -> bool:
        """Try to reserve the key for processing. Returns True if the key was reserved, False if it already exists."""
        value = json.dumps({"fingerprint": fingerprint, "status": IdempotencyStatus.PROCESSING.value})
        return bool(await self.redis.set(key, value, ex=ttl, nx=True))

    async def complete(
        self,
        key: str,
        fingerprint: str,
        response: dict,
        ttl: int = 86400,
    ) -> None:
        """Set the key as completed with the response and fingerprint. The key will expire after ttl seconds."""
        value = json.dumps(
            {
                "fingerprint": fingerprint,
                "status": IdempotencyStatus.COMPLETED.value,
                "response": response,
            }
        )
        await self.redis.setex(key, ttl, value)

    async def fail(self, key: str, fingerprint: str, ttl: int = 300) -> None:
        """Set the key as failed with the fingerprint. The key will expire after ttl seconds."""
        value = json.dumps({"fingerprint": fingerprint, "status": IdempotencyStatus.FAILED.value})
        await self.redis.setex(key, ttl, value)

    async def delete(self, key: str) -> None:
        """Delete the key from Redis."""
        await self.redis.delete(key)
