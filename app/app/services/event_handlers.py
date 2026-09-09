"""Обработчики событий для приложения."""

from prometheus_client import Counter

from app.core.event_bus import EventBus
from app.core.logging import get_logger
from app.domain.events import ConversationCreated, ConversationEscalated


logger = get_logger(__name__)
conversation_created_total = Counter(
	"conversations_created_total",
	"Total number of created conversations.",
)

event_bus = EventBus()


@event_bus.on_event(ConversationCreated)
async def notify_operators_on_create(event: ConversationCreated) -> None:
	"""Уведомить операторов о новом диалоге."""
	logger.info(
		"Операторы уведомлены о создании диалога %s.",
		event.conversation_id,
	)


@event_bus.on_event(ConversationCreated)
def track_metrics_on_create(event: ConversationCreated) -> None:
	"""Записать метрику создания диалога."""
	conversation_created_total.inc()


@event_bus.on_event(ConversationEscalated)
def log_escalation(event: ConversationEscalated) -> None:
	"""Записать эскалацию диалога в лог."""
	logger.warning(
		"Диалог %s эскалирован оператору.",
		event.conversation_id,
	)


