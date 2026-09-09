from unittest.mock import patch

import pytest

from app.domain.events import ConversationCreated, ConversationEscalated
from app.services.event_handlers import (
    event_bus,
    log_escalation,
    notify_operators_on_create,
    track_metrics_on_create,
)


@pytest.mark.asyncio
async def test_created_event_runs_notification_and_metrics_handlers():
    with patch("app.services.event_handlers.logger") as logger:
        await event_bus.publish_async(ConversationCreated("conversation-1"))

    logger.info.assert_called_once_with(
        "Операторы уведомлены о создании диалога %s.",
        "conversation-1",
    )


def test_escalated_event_runs_logging_handler():
    with patch("app.services.event_handlers.logger") as logger:
        event_bus.publish(ConversationEscalated("conversation-2"))

    logger.warning.assert_called_once_with(
        "Диалог %s эскалирован оператору.",
        "conversation-2",
    )


def test_handlers_are_registered_on_event_bus():
    assert notify_operators_on_create in event_bus._subscribers[ConversationCreated]
    assert track_metrics_on_create in event_bus._subscribers[ConversationCreated]
    assert log_escalation in event_bus._subscribers[ConversationEscalated]