"""Проверки интеграции доменных событий с бизнес-сервисами."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domain.events import (
    ConversationClosed,
    ConversationCreated,
    ConversationEscalated,
    ConversationMarkedForReview,
    ConversationReturnedToAI,
    MessageSent,
    OperatorAssigned,
    UserDeleted,
    UserRegistered,
    UserUpdated,
)
from app.models.conversation import Channel, Priority


@pytest.mark.asyncio
async def test_conversation_service_queues_events_for_mutations():
    from app.services.conversation_service import ConversationService

    conversation = MagicMock(id=42, operator_id=7)
    returned = MagicMock(id=42, operator_id=None)
    uow = SimpleNamespace(conversation=AsyncMock(), state_machine=AsyncMock(), _events=[])
    uow.add_event = uow._events.append
    service = ConversationService(uow)

    uow.conversation.create_conversation.return_value = conversation
    uow.conversation.get_conversation_by_id.return_value = conversation
    uow.state_machine.escalate.return_value = conversation
    uow.state_machine.assign_operator.return_value = conversation
    uow.state_machine.close.return_value = conversation
    uow.state_machine.back_to_ai.return_value = returned
    uow.state_machine.mark_for_review.return_value = conversation

    await service.create_conversation(1, Priority.MEDIUM, Channel.WEB)
    await service.escalate(42)
    await service.assign_operator(42, 9)
    await service.close(42)
    await service.back_to_ai(42)
    await service.mark_conversation_for_review(42)

    assert [type(event) for event in uow._events] == [
        ConversationCreated,
        ConversationEscalated,
        OperatorAssigned,
        ConversationClosed,
        ConversationReturnedToAI,
        ConversationMarkedForReview,
        ConversationEscalated,
    ]
    uow.state_machine.escalate.assert_awaited_once_with(42)
    uow.state_machine.assign_operator.assert_awaited_once_with(42, 9)
    uow.state_machine.close.assert_awaited_once_with(42)
    uow.state_machine.back_to_ai.assert_awaited_once_with(42)
    uow.state_machine.mark_for_review.assert_awaited_once_with(42)


@pytest.mark.asyncio
async def test_message_service_queues_message_and_review_events():
    from app.services.message_service import MessageService

    message = MagicMock(id=100)
    uow = SimpleNamespace(message=AsyncMock(), state_machine=AsyncMock(), _events=[])
    uow.add_event = uow._events.append
    service = MessageService(uow)
    uow.message.create_message.return_value = message
    uow.state_machine.mark_for_review.return_value = MagicMock(id=55)

    await service.create_message(55, "user", 1, "hello", needs_review=True)

    assert [type(event) for event in uow._events] == [
        ConversationMarkedForReview,
        MessageSent,
    ]
    uow.state_machine.mark_for_review.assert_awaited_once_with(55)


@pytest.mark.asyncio
async def test_user_service_queues_user_lifecycle_events():
    from app.services.user_service import UserService
    from app.schemas.user import UserCreate, UserUpdate
    from app.models.user import UserRole

    created = MagicMock(id=1)
    updated = MagicMock(id=1)
    target = MagicMock(id=1)
    admin = MagicMock(role=UserRole.ADMIN, id=99)

    uow = SimpleNamespace(users=AsyncMock(), _events=[])
    uow.add_event = uow._events.append
    service = UserService(uow)
    uow.users.exists.return_value = False
    uow.users.create.return_value = created
    uow.users.update.return_value = updated
    uow.users.delete.return_value = None

    with patch("app.services.user_service.hash_password", return_value="hash"):
        await service.register_user(
            UserCreate(email="event@example.com", password="Pass123!", nickname="event")
        )
    with patch.object(service, "get_user_by_id", AsyncMock(return_value=target)):
        await service.update_user(1, UserUpdate(nickname="updated"), admin)
        await service.delete_user(1, admin)

    assert [type(event) for event in uow._events] == [
        UserRegistered,
        UserUpdated,
        UserDeleted,
    ]
