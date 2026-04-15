"""Тесты сервиса диалогов (делегирование в репозиторий)."""

from unittest.mock import AsyncMock

import pytest


@pytest.mark.asyncio
async def test_create_conversation_delegates_to_repository():
    from app.services.conversation_service import ConversationService

    service = ConversationService(session=AsyncMock())
    expected = object()
    service.conversation_repo.create_conversation = AsyncMock(return_value=expected)

    result = await service.create_conversation(user_id=7, priority="high", channel="api")

    assert result is expected
    service.conversation_repo.create_conversation.assert_awaited_once_with(7, "high", "api")


@pytest.mark.asyncio
async def test_get_conversation_by_id_delegates_to_repository():
    from app.services.conversation_service import ConversationService

    service = ConversationService(session=AsyncMock())
    expected = object()
    service.conversation_repo.get_conversation_by_id = AsyncMock(return_value=expected)

    result = await service.get_conversation_by_id(101)

    assert result is expected
    service.conversation_repo.get_conversation_by_id.assert_awaited_once_with(101)


@pytest.mark.asyncio
async def test_update_and_assign_and_close_delegate_to_repository():
    from app.services.conversation_service import ConversationService

    service = ConversationService(session=AsyncMock())
    service.conversation_repo.update_conversation_status = AsyncMock(return_value={"status": "ok"})
    service.conversation_repo.assign_operator = AsyncMock(return_value={"operator": 5})

    update_result = await service.update_conversation_status(15, "waiting_for_operator")
    assign_result = await service.assign_operator(15, 5)
    close_result = await service.close(15)

    assert update_result == {"status": "ok"}
    assert assign_result == {"operator": 5}
    assert close_result == {"status": "ok"}

    service.conversation_repo.update_conversation_status.assert_any_await(15, "waiting_for_operator")
    service.conversation_repo.assign_operator.assert_awaited_once_with(15, 5)
    service.conversation_repo.update_conversation_status.assert_any_await(15, "closed")
