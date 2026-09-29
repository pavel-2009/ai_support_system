import pytest
from fastapi import HTTPException, Request

from app.core.dependencies import get_idempotency_key
from app.core.idempotency import IdempotencyKey


class FakeRedis:
    def __init__(self):
        self.values = {}
        self.expirations = {}

    async def set(self, key, value, ex=None, nx=False):
        if nx and key in self.values:
            return False
        self.values[key] = value
        self.expirations[key] = ex
        return True

    async def setex(self, key, ttl, value):
        self.values[key] = value
        self.expirations[key] = ttl

    async def get(self, key):
        return self.values.get(key)

    async def delete(self, key):
        self.values.pop(key, None)
        self.expirations.pop(key, None)


def make_request(idempotency_key=None):
    headers = []
    if idempotency_key is not None:
        headers.append((b"idempotency-key", idempotency_key.encode()))
    return Request({"type": "http", "headers": headers})


class TestIdempotencyKey:
    async def test_reserve_is_atomic_and_stores_processing_state(self):
        redis_client = FakeRedis()
        service = IdempotencyKey(redis_client)

        assert await service.reserve("message-key", "request-fingerprint", ttl=30)
        assert not await service.reserve("message-key", "request-fingerprint", ttl=30)
        assert await service.get("message-key") == {
            "fingerprint": "request-fingerprint",
            "status": "processing",
        }
        assert redis_client.expirations["message-key"] == 30

    async def test_complete_round_trips_json_and_supports_bytes_from_redis(self):
        redis_client = FakeRedis()
        service = IdempotencyKey(redis_client)

        await service.complete(
            "message-key",
            "request-fingerprint",
            {"id": 42, "content": "hello"},
        )
        redis_client.values["message-key"] = redis_client.values["message-key"].encode()

        assert await service.get("message-key") == {
            "fingerprint": "request-fingerprint",
            "status": "completed",
            "response": {"id": 42, "content": "hello"},
        }
        assert redis_client.expirations["message-key"] == 86400

    async def test_delete_releases_reservation(self):
        redis_client = FakeRedis()
        service = IdempotencyKey(redis_client)
        await service.reserve("message-key", "request-fingerprint")

        await service.delete("message-key")

        assert await service.get("message-key") is None
        assert await service.reserve("message-key", "retry-fingerprint")


class TestGetIdempotencyKey:
    def test_returns_trimmed_header_value(self):
        assert get_idempotency_key(make_request("  request-123  ")) == "request-123"

    def test_returns_none_when_header_is_missing(self):
        assert get_idempotency_key(make_request()) is None

    @pytest.mark.parametrize(
        "header_value, expected_detail",
        [
            ("   ", "Idempotency-Key не может быть пустым."),
            ("x" * 256, "Idempotency-Key слишком длинный."),
        ],
    )
    def test_rejects_invalid_header(self, header_value, expected_detail):
        with pytest.raises(HTTPException) as exc_info:
            get_idempotency_key(make_request(header_value))

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail == expected_detail
