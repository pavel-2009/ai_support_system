"""Тесты роутера диалогов."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException


@pytest.mark.asyncio
async def test_create_conversation_calls_service():
    from app.routers.conversation import create_conversation

    current_user = SimpleNamespace(id=11)
    service = AsyncMock()
    service.create_conversation = AsyncMock(return_value={"id": 77})

    payload = SimpleNamespace(priority="high", channel="api")

    result = await create_conversation(
        conversation_data=payload,
        current_user=current_user,
        conversation_service=service,
    )

    assert result == {"id": 77}
    service.create_conversation.assert_awaited_once_with(11, payload)


@pytest.mark.asyncio
async def test_get_conversation_returns_404_when_not_found():
    from app.routers.conversation import get_conversation

    current_user = SimpleNamespace(id=5)
    service = AsyncMock()
    service.get_conversation_by_id = AsyncMock(return_value=None)

    with pytest.raises(HTTPException) as exc:
        await get_conversation(15, current_user=current_user, conversation_service=service)

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_conversation_returns_403_for_foreign_user():
    from app.routers.conversation import get_conversation

    current_user = SimpleNamespace(id=1)
    service = AsyncMock()
    service.get_conversation_by_id = AsyncMock(return_value=SimpleNamespace(user_id=2))

    with pytest.raises(HTTPException) as exc:
        await get_conversation(15, current_user=current_user, conversation_service=service)

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_get_conversation_returns_entity_for_owner():
    from app.routers.conversation import get_conversation

    current_user = SimpleNamespace(id=2)
    convo = SimpleNamespace(id=15, user_id=2)
    service = AsyncMock()
    service.get_conversation_by_id = AsyncMock(return_value=convo)

    result = await get_conversation(15, current_user=current_user, conversation_service=service)

    assert result is convo
