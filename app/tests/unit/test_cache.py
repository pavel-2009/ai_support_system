"""Тесты асинхронного Redis-кэша."""

import json
from unittest.mock import AsyncMock

import pytest

from app.core.cache import Cache


@pytest.mark.asyncio
async def test_get_returns_none_on_miss_and_decodes_json():
    redis = AsyncMock()
    cache = Cache(redis)

    redis.get.return_value = None
    assert await cache.get("missing") is None

    redis.get.return_value = b'{"status": "open"}'
    assert await cache.get("conversation:1") == {"status": "open"}


@pytest.mark.asyncio
async def test_set_serializes_json_and_applies_ttl():
    redis = AsyncMock()
    cache = Cache(redis)

    await cache.set("conversation:1", {"id": 1}, ttl=30)

    redis.set.assert_awaited_once_with("conversation:1", '{"id": 1}', ex=30)


@pytest.mark.asyncio
async def test_delete_removes_the_requested_key():
    redis = AsyncMock()
    cache = Cache(redis)

    await cache.delete("conversation:1")

    redis.delete.assert_awaited_once_with("conversation:1")


@pytest.mark.asyncio
async def test_get_or_set_returns_cached_value_without_calling_factory():
    redis = AsyncMock()
    redis.get.return_value = json.dumps({"id": 1})
    cache = Cache(redis)
    factory = AsyncMock(return_value={"id": 2})

    result = await cache.get_or_set("conversation:1", factory, ttl=30)

    assert result == {"id": 1}
    factory.assert_not_awaited()
    redis.set.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_or_set_populates_cache_on_miss():
    redis = AsyncMock()
    redis.get.return_value = None
    cache = Cache(redis)
    factory = AsyncMock(return_value={"id": 1})

    result = await cache.get_or_set("conversation:1", factory, ttl=30)

    assert result == {"id": 1}
    factory.assert_awaited_once_with()
    redis.set.assert_awaited_once_with("conversation:1", '{"id": 1}', ex=30)