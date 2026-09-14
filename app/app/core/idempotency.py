"""Idempotency key generation and validation."""

from fastapi import Depends, Request, Response
from redis import Redis

from app.core.redis import get_redis_client


class IdempotencyKey:
    """Idempotency key generation and validation."""

    def __init__(self, redis_client: Redis):
        self.redis_client = redis_client

    def store(self, key: str, response: Response, ttl: int = 86400) -> None:
        """Store the response in Redis with the given key and expiration time."""
        self.redis_client.setex(key, ttl, response.body)

    def get(self, key: str) -> bytes | None:
        """Retrieve the response from Redis using the given key."""
        return self.redis_client.get(key)

    def exists(self, key: str) -> bool:
        """Check if the key exists in Redis."""
        return self.redis_client.exists(key) > 0
