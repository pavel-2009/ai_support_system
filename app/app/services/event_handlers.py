"""Обработчики доменных событий приложения."""

from prometheus_client import Counter

from app.core.event_bus import event_bus
from app.core.metrics import (
    conversations_created_total,
    escalations_total,
    messages_sent_total,
)
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

operator_assigned_total = Counter("operators_assigned_total", "Total number of operator assignments.")
conversation_closed_total = Counter("conversations_closed_total", "Total number of closed conversations.")
conversation_returned_to_ai_total = Counter("conversations_returned_to_ai_total", "Total number of conversations returned to AI.")
conversation_review_total = Counter("conversations_marked_for_review_total", "Total number of conversations marked for review.")
user_registered_total = Counter("users_registered_total", "Total number of registered users.")
user_updated_total = Counter("users_updated_total", "Total number of updated users.")
user_deleted_total = Counter("users_deleted_total", "Total number of deleted users.")


@event_bus.on_event(ConversationCreated)
async def notify_operators_on_create(event: ConversationCreated) -> None:
    """Уведомить операторов о новом диалоге."""
    # Presence of the event handler is enough for future operator notifications.
    # Do not log every normal event: these are high-frequency application events.


@event_bus.on_event(ConversationCreated)
async def track_metrics_on_create(event: ConversationCreated) -> None:
    conversations_created_total.inc()


@event_bus.on_event(MessageSent)
async def notify_on_message_sent(event: MessageSent) -> None:
    messages_sent_total.inc()
    await operator_connection_manager.broadcast(
        {
            "type": "message_sent",
            "conversation_id": str(event.conversation_id),
            "message_id": str(event.message_id),
        }
    )


@event_bus.on_event(ConversationEscalated)
async def notify_on_escalation(event: ConversationEscalated) -> None:
    escalations_total.inc()
    await operator_connection_manager.broadcast(
        {
            "type": "conversation_escalated",
            "conversation_id": str(event.conversation_id),
        }
    )


@event_bus.on_event(OperatorAssigned)
async def notify_on_operator_assigned(event: OperatorAssigned) -> None:
    operator_assigned_total.inc()
    await operator_connection_manager.broadcast(
        {
            "type": "operator_assigned",
            "conversation_id": str(event.conversation_id),
            "operator_id": event.operator_id,
        }
    )


@event_bus.on_event(ConversationClosed)
async def notify_on_conversation_closed(event: ConversationClosed) -> None:
    conversation_closed_total.inc()
    await operator_connection_manager.broadcast(
        {
            "type": "conversation_closed",
            "conversation_id": str(event.conversation_id),
        }
    )


@event_bus.on_event(ConversationReturnedToAI)
async def notify_on_return_to_ai(event: ConversationReturnedToAI) -> None:
    conversation_returned_to_ai_total.inc()
    await operator_connection_manager.broadcast(
        {
            "type": "conversation_returned_to_ai",
            "conversation_id": str(event.conversation_id),
            "operator_id": event.operator_id,
        }
    )


@event_bus.on_event(ConversationMarkedForReview)
async def notify_on_review_required(event: ConversationMarkedForReview) -> None:
    conversation_review_total.inc()
    await operator_connection_manager.broadcast(
        {
            "type": "conversation_escalated",
            "conversation_id": str(event.conversation_id),
        }
    )


@event_bus.on_event(UserRegistered)
async def track_user_registered(event: UserRegistered) -> None:
    user_registered_total.inc()


@event_bus.on_event(UserUpdated)
async def track_user_updated(event: UserUpdated) -> None:
    user_updated_total.inc()


@event_bus.on_event(UserDeleted)
async def track_user_deleted(event: UserDeleted) -> None:
    user_deleted_total.inc()
