"""Idempotency key storage and response caching."""

import json

from fastapi import Response
from redis import Redis


class IdempotencyKey:
    """Store idempotency state and serialized responses in Redis."""

    def __init__(self, redis_client: Redis):
        self.redis_client = redis_client

    def store(self, key: str, response: Response, ttl: int = 86400) -> None:
        """Store the response in Redis with the given key and expiration time."""
        self.redis_client.setex(key, ttl, response.body)

    def reserve(self, key: str, fingerprint: str, ttl: int = 300) -> bool:
        """Reserve a key atomically before processing the request."""
        value = json.dumps({"fingerprint": fingerprint, "status": "processing"})
        return bool(self.redis_client.set(key, value, ex=ttl, nx=True))

    def store_response(
        self,
        key: str,
        fingerprint: str,
        response: dict,
        ttl: int = 86400,
    ) -> None:
        """Store a completed response together with its request fingerprint."""
        value = json.dumps(
            {"fingerprint": fingerprint, "status": "completed", "response": response},
            default=str,
        )
        self.redis_client.setex(key, ttl, value)

    def get_state(self, key: str) -> dict | None:
        """Return the stored idempotency state, if any."""
        value = self.redis_client.get(key)
        if value is None:
            return None
        if isinstance(value, bytes):
            value = value.decode("utf-8")
        return json.loads(value)

    def delete(self, key: str) -> None:
        """Release a reservation when request processing fails."""
        self.redis_client.delete(key)

    def get(self, key: str) -> bytes | None:
        """Retrieve the response from Redis using the given key."""
        return self.redis_client.get(key)

    def exists(self, key: str) -> bool:
        """Check if the key exists in Redis."""
        return self.redis_client.exists(key) > 0
