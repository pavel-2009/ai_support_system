"""Репозиторий для работы с сообщениями."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation, Status
from app.models.message import Message


class MessageRepository:
    """Репозиторий для работы с сообщениями."""

    def __init__(self, session: AsyncSession):
        self.session = session
        

    async def create_message(
        self,
        conversation_id: int,
        sender_type: str,
        sender_id: int,
        content: str,
        is_auto_reply: bool = False,
        confidence: float = None,
        needs_review: bool = False
    ) -> Message:
        """Создать новое сообщение."""
        
        new_message = Message(
            conversation_id=conversation_id,
            sender_type=sender_type,
            sender_id=sender_id,
            content=content,
            is_auto_reply=is_auto_reply,
            confidence=confidence,
            needs_review=needs_review
        )
        self.session.add(new_message)
        await self.session.commit()
        await self.session.refresh(new_message)
        return new_message

    async def get_messages_by_conversation(
        self,
        conversation_id: int
    ) -> list[Message]:
        """Получить все сообщения для заданного conversation_id."""
        
        result = await self.session.execute(select(Message).where(Message.conversation_id == conversation_id))
        return result.scalars().all()

    async def mark_conversation_for_review(self, conversation_id: int) -> Conversation | None:
        """Пометить диалог на ревью оператором, эскалируя его статус."""

        result = await self.session.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conversation = result.scalar_one_or_none()
        if conversation is None:
            return None

        conversation.status = Status.ESCALATED
        await self.session.commit()
        await self.session.refresh(conversation)
        return conversation
