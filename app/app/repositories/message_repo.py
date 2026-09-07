"""Репозиторий для работы с сообщениями."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.conversation import Conversation, Status
from app.models.message import Message
from app.models.user import UserRole


logger = get_logger(__name__)


class MessageRepository:
    """Репозиторий для работы с сообщениями."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_message(
        self,
        conversation_id: int,
        sender_type: str,
        sender_id: int | None,
        content: str,
        is_auto_reply: bool = False,
        confidence: float | None = None,
        needs_review: bool = False,
    ) -> Message | None:
        """Создать новое сообщение."""
        logger.info(
            "DB CREATE message: conversation_id=%s sender_type=%s sender_id=%s auto=%s review=%s",
            conversation_id, sender_type, sender_id, is_auto_reply, needs_review,
        )

        conversation = (
            await self.session.execute(
                select(Conversation).where(Conversation.id == conversation_id)
            )
        ).scalar_one_or_none()
        if conversation is None:
            logger.warning("DB CREATE message skipped: conversation %s not found", conversation_id)
            return None

        if sender_type == UserRole.OPERATOR.value:
            if conversation.operator_id != sender_id or conversation.status != Status.WAITING_FOR_OPERATOR:
                logger.warning(
                    "DB CREATE message rejected: operator=%s conversation=%s status=%s operator_id=%s",
                    sender_id, conversation_id, conversation.status, conversation.operator_id,
                )
                return None

        new_message = Message(
            conversation_id=conversation_id,
            sender_type=sender_type,
            sender_id=sender_id,
            content=content,
            is_auto_reply=is_auto_reply,
            confidence=confidence,
            needs_review=needs_review,
        )
        self.session.add(new_message)
        await self.session.flush()
        await self.session.refresh(new_message)
        logger.info("DB CREATE message successful: id=%s conversation_id=%s", new_message.id, conversation_id)
        return new_message

    async def get_messages_by_conversation(self, conversation_id: int) -> list[Message]:
        """Получить все сообщения для заданного conversation_id."""
        logger.info("DB SELECT messages: conversation_id=%s", conversation_id)
        result = await self.session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc(), Message.id.asc())
        )
        messages = result.scalars().all()
        logger.info("DB SELECT messages successful: conversation_id=%s count=%s", conversation_id, len(messages))
        return messages

    async def mark_conversation_for_review(self, conversation_id: int) -> Conversation | None:
        """Пометить диалог на ревью оператором, эскалируя его статус."""
        logger.info("DB UPDATE conversation status: id=%s -> %s", conversation_id, Status.ESCALATED)
        result = await self.session.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conversation = result.scalar_one_or_none()
        if conversation is None:
            logger.warning("DB UPDATE skipped: conversation %s not found", conversation_id)
            return None

        conversation.status = Status.ESCALATED
        await self.session.flush()
        await self.session.refresh(conversation)
        logger.info("DB UPDATE conversation successful: id=%s status=%s", conversation_id, conversation.status)
        return conversation
