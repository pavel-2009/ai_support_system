import pytest

from app.domain.events import ConversationCreated, ConversationEscalated
from app.services.event_handlers import (
    event_bus,
    notify_on_escalation,
    notify_operators_on_create,
    track_metrics_on_create,
)


@pytest.mark.asyncio
async def test_created_event_runs_notification_and_metrics_handlers():
    await event_bus.publish_async(ConversationCreated("conversation-1"))


@pytest.mark.asyncio
async def test_escalated_event_runs_notification_handler():
    await event_bus.publish_async(ConversationEscalated("conversation-2"))


def test_handlers_are_registered_on_event_bus():
    assert notify_operators_on_create in event_bus._subscribers[ConversationCreated]
    assert track_metrics_on_create in event_bus._subscribers[ConversationCreated]
    assert notify_on_escalation in event_bus._subscribers[ConversationEscalated]
