"""Репозиторий для работы с сообщениями."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.conversation import Conversation, Status
from app.models.message import Message
from app.models.user import UserRole


logger = get_logger(__name__)


class MessageRepository:
    """Репозиторий для CRUD и query-операций с сообщениями."""

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
        conversation = (
            await self.session.execute(
                select(Conversation).where(Conversation.id == conversation_id)
            )
        ).scalar_one_or_none()
        if conversation is None:
            logger.warning("DB CREATE message skipped: conversation %s not found", conversation_id)
            return None

        if sender_type == UserRole.USER.value and conversation.status not in (Status.OPEN, Status.WAITING_FOR_USER):
            logger.warning("MESSAGE REJECTED: user reply is not expected conversation=%s status=%s", conversation_id, conversation.status)
            return None

        if sender_type == "ai" and conversation.status != Status.PENDING_AI:
            logger.info("AI RESPONSE SKIPPED: conversation=%s status=%s", conversation_id, conversation.status)
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
        return new_message

    async def get_messages_by_conversation(self, conversation_id: int) -> list[Message]:
        """Получить все сообщения для заданного conversation_id."""
        result = await self.session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc(), Message.id.asc())
        )
        return result.scalars().all()
