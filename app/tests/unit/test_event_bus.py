import pytest
from unittest.mock import AsyncMock, patch

from app.core.event_bus import EventBus, on_event
from app.core.uow import UnitOfWork
from app.domain.events import ConversationCreated


def test_publish_calls_sync_handler_and_decorator_registers_it():
    bus = EventBus()
    received = []

    @bus.on_event(ConversationCreated)
    def handle(event):
        received.append(event.conversation_id)

    event = ConversationCreated("conversation-1")
    bus.publish(event)

    assert received == ["conversation-1"]
    assert handle in bus._subscribers[ConversationCreated]


@pytest.mark.asyncio
async def test_publish_async_calls_sync_and_async_handlers():
    bus = EventBus()
    received = []

    @on_event(ConversationCreated, bus)
    def handle_sync(event):
        received.append(("sync", event.conversation_id))

    @bus.on_event(ConversationCreated)
    async def handle_async(event):
        received.append(("async", event.conversation_id))

    await bus.publish_async(ConversationCreated("conversation-2"))

    assert received == [
        ("sync", "conversation-2"),
        ("async", "conversation-2"),
    ]


@pytest.mark.asyncio
async def test_publish_rejects_async_handler():
    bus = EventBus()

    @bus.on_event(ConversationCreated)
    async def handle(event):
        pass

    with pytest.raises(RuntimeError, match="publish_async"):
        bus.publish(ConversationCreated("conversation-3"))


@pytest.mark.asyncio
async def test_uow_publishes_events_after_commit():
    calls = []

    class Session:
        async def commit(self):
            calls.append("commit")

        async def rollback(self):
            calls.append("rollback")

        async def close(self):
            calls.append("close")

    event = ConversationCreated("conversation-4")

    async def publish(event):
        calls.append(("publish", event.conversation_id))

    with patch("app.core.uow.event_bus.publish_async", new=publish):
        async with UnitOfWork(lambda: Session()) as uow:
            uow.add_event(event)

    assert calls == ["commit", ("publish", "conversation-4"), "close"]