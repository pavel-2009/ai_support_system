"""Обработчики доменных событий приложения."""

from prometheus_client import Counter

from app.core.event_bus import event_bus
from app.core.logging import get_logger
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


logger = get_logger(__name__)

conversation_created_total = Counter(
    "conversations_created_total",
    "Total number of created conversations.",
)
message_sent_total = Counter(
    "messages_sent_total",
    "Total number of sent messages.",
)
conversation_escalated_total = Counter(
    "conversations_escalated_total",
    "Total number of escalated conversations.",
)
operator_assigned_total = Counter(
    "operators_assigned_total",
    "Total number of operator assignments.",
)
conversation_closed_total = Counter(
    "conversations_closed_total",
    "Total number of closed conversations.",
)
conversation_returned_to_ai_total = Counter(
    "conversations_returned_to_ai_total",
    "Total number of conversations returned to AI.",
)
conversation_review_total = Counter(
    "conversations_marked_for_review_total",
    "Total number of conversations marked for review.",
)
user_registered_total = Counter(
    "users_registered_total",
    "Total number of registered users.",
)
user_updated_total = Counter(
    "users_updated_total",
    "Total number of updated users.",
)
user_deleted_total = Counter(
    "users_deleted_total",
    "Total number of deleted users.",
)


@event_bus.on_event(ConversationCreated)
async def notify_operators_on_create(event: ConversationCreated) -> None:
    """Уведомить операторов о новом диалоге."""
    logger.info("DOMAIN EVENT: conversation created id=%s", event.conversation_id)


@event_bus.on_event(ConversationCreated)
def track_metrics_on_create(event: ConversationCreated) -> None:
    conversation_created_total.inc()


@event_bus.on_event(MessageSent)
async def notify_on_message_sent(event: MessageSent) -> None:
    """Зафиксировать событие нового сообщения для downstream-уведомлений."""
    logger.info(
        "DOMAIN EVENT: message sent id=%s conversation_id=%s",
        event.message_id,
        event.conversation_id,
    )
    message_sent_total.inc()


@event_bus.on_event(ConversationEscalated)
def notify_on_escalation(event: ConversationEscalated) -> None:
    """Уведомить операторов об эскалации диалога."""
    logger.warning("DOMAIN EVENT: conversation escalated id=%s", event.conversation_id)
    conversation_escalated_total.inc()


@event_bus.on_event(OperatorAssigned)
def notify_on_operator_assigned(event: OperatorAssigned) -> None:
    """Уведомить участников о назначении оператора."""
    logger.info(
        "DOMAIN EVENT: operator assigned conversation_id=%s operator_id=%s",
        event.conversation_id,
        event.operator_id,
    )
    operator_assigned_total.inc()


@event_bus.on_event(ConversationClosed)
def notify_on_conversation_closed(event: ConversationClosed) -> None:
    """Зафиксировать закрытие диалога."""
    logger.info("DOMAIN EVENT: conversation closed id=%s", event.conversation_id)
    conversation_closed_total.inc()


@event_bus.on_event(ConversationReturnedToAI)
def notify_on_return_to_ai(event: ConversationReturnedToAI) -> None:
    """Уведомить систему о возврате диалога ИИ."""
    logger.info(
        "DOMAIN EVENT: conversation returned to AI id=%s operator_id=%s",
        event.conversation_id,
        event.operator_id,
    )
    conversation_returned_to_ai_total.inc()


@event_bus.on_event(ConversationMarkedForReview)
def notify_on_review_required(event: ConversationMarkedForReview) -> None:
    """Уведомить операторов о необходимости ревью."""
    logger.warning("DOMAIN EVENT: conversation requires review id=%s", event.conversation_id)
    conversation_review_total.inc()


@event_bus.on_event(UserRegistered)
def track_user_registered(event: UserRegistered) -> None:
    logger.info("DOMAIN EVENT: user registered id=%s", event.user_id)
    user_registered_total.inc()


@event_bus.on_event(UserUpdated)
def track_user_updated(event: UserUpdated) -> None:
    logger.info("DOMAIN EVENT: user updated id=%s", event.user_id)
    user_updated_total.inc()


@event_bus.on_event(UserDeleted)
def track_user_deleted(event: UserDeleted) -> None:
    logger.info("DOMAIN EVENT: user deleted id=%s", event.user_id)
    user_deleted_total.inc()
