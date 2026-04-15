"""Тесты инициализации сервисов и startup/lifespan."""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock

import pytest


@pytest.fixture
def clean_services_registry():
    """Очищает внутренний реестр сервисов до/после теста."""
    import app.services_init as services_init

    services_init.__services.clear()
    yield
    services_init.__services.clear()


@pytest.mark.asyncio
async def test_init_services_registers_user_and_conversation_services(clean_services_registry):
    """Проверяем, что init_services создает оба сервиса в реестре."""
    import app.services_init as services_init

    session = AsyncMock()
    await services_init.init_services(session)

    user_service = await services_init.get_user_service()
    conversation_service = await services_init.get_conversation_service()

    assert user_service is not None
    assert conversation_service is not None
    assert user_service.session is session
    assert conversation_service.session is session


@pytest.mark.asyncio
async def test_lifespan_calls_init_services_with_startup_session(monkeypatch):
    """Проверяем вызов init_services при старте приложения."""
    from main import lifespan

    fake_session = object()
    init_mock = AsyncMock()

    async def fake_get_async_session():
        yield fake_session

    monkeypatch.setattr("main.get_async_session", fake_get_async_session)
    monkeypatch.setattr("main.init_services", init_mock)

    @asynccontextmanager
    async def _lifespan_ctx():
        async with lifespan(app=object()):
            yield

    async with _lifespan_ctx():
        pass

    init_mock.assert_awaited_once_with(fake_session)
