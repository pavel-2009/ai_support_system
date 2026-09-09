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
conversation_created_total = Counter("conversations_created_total", "Total number of created conversations.")
message_sent_total = Counter("messages_sent_total", "Total number of sent messages.")
conversation_escalated_total = Counter("conversations_escalated_total", "Total number of escalated conversations.")
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
    logger.info("Операторы уведомлены о создании диалога %s.", event.conversation_id)


@event_bus.on_event(ConversationCreated)
def track_metrics_on_create(event: ConversationCreated) -> None:
    conversation_created_total.inc()


@event_bus.on_event(MessageSent)
async def notify_on_message_sent(event: MessageSent) -> None:
    logger.info("Сообщение %s отправлено в диалоге %s.", event.message_id, event.conversation_id)
    message_sent_total.inc()


@event_bus.on_event(ConversationEscalated)
def log_escalation(event: ConversationEscalated) -> None:
    """Записать эскалацию диалога в лог."""
    logger.warning("Диалог %s эскалирован оператору.", event.conversation_id)
    conversation_escalated_total.inc()


@event_bus.on_event(OperatorAssigned)
def notify_on_operator_assigned(event: OperatorAssigned) -> None:
    logger.info("Оператор %s назначен на диалог %s.", event.operator_id, event.conversation_id)
    operator_assigned_total.inc()


@event_bus.on_event(ConversationClosed)
def notify_on_conversation_closed(event: ConversationClosed) -> None:
    logger.info("Диалог %s закрыт.", event.conversation_id)
    conversation_closed_total.inc()


@event_bus.on_event(ConversationReturnedToAI)
def notify_on_return_to_ai(event: ConversationReturnedToAI) -> None:
    logger.info("Диалог %s возвращён ИИ после оператора %s.", event.conversation_id, event.operator_id)
    conversation_returned_to_ai_total.inc()


@event_bus.on_event(ConversationMarkedForReview)
def notify_on_review_required(event: ConversationMarkedForReview) -> None:
    logger.warning("Диалог %s требует ревью оператора.", event.conversation_id)
    conversation_review_total.inc()


@event_bus.on_event(UserRegistered)
def track_user_registered(event: UserRegistered) -> None:
    logger.info("Пользователь %s зарегистрирован.", event.user_id)
    user_registered_total.inc()


@event_bus.on_event(UserUpdated)
def track_user_updated(event: UserUpdated) -> None:
    logger.info("Пользователь %s обновлён.", event.user_id)
    user_updated_total.inc()


@event_bus.on_event(UserDeleted)
def track_user_deleted(event: UserDeleted) -> None:
    logger.info("Пользователь %s удалён.", event.user_id)
    user_deleted_total.inc()
