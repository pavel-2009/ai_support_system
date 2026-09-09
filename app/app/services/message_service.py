"""Сервис для работы с сообщениями."""

from app.core.logging import get_logger
from app.core.uow import UnitOfWork
from app.domain.events import ConversationMarkedForReview, MessageSent


logger = get_logger(__name__)


class MessageService:
    """Сервис для работы с сообщениями."""

    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def create_message(
        self,
        conversation_id: int,
        sender_type: str,
        sender_id: int | None,
        content: str,
        is_auto_reply: bool = False,
        confidence: float | None = None,
        needs_review: bool = False,
    ):
        """Создать новое сообщение."""
        new_message = await self.uow.message.create_message(
            conversation_id=conversation_id,
            sender_type=sender_type,
            sender_id=sender_id,
            content=content,
            is_auto_reply=is_auto_reply,
            confidence=confidence,
            needs_review=needs_review,
        )
        if new_message is None:
            logger.warning(
                "MESSAGE SERVICE CREATE REJECTED: conversation_id=%s sender_type=%s sender_id=%s",
                conversation_id,
                sender_type,
                sender_id,
            )
            return None

        add_event = getattr(self.uow, "add_event", None)
        if needs_review:
            updated_conversation = await self.uow.message.mark_conversation_for_review(conversation_id)
            if updated_conversation is not None and add_event is not None:
                add_event(ConversationMarkedForReview(str(conversation_id)))

        if add_event is not None:
            add_event(MessageSent(str(new_message.id), str(conversation_id)))

        logger.debug(
            "MESSAGE SERVICE CREATE OK: id=%s conversation_id=%s sender_type=%s",
            new_message.id,
            conversation_id,
            sender_type,
        )
        return new_message

    async def get_messages_by_conversation(self, conversation_id: int):
        """Получить все сообщения для заданного conversation_id."""
        return await self.uow.message.get_messages_by_conversation(conversation_id)
