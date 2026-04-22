"""Сервис для работы с сообщениями."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.message_repo import MessageRepository


class MessageService:
    """Сервис для работы с сообщениями."""


    def __init__(self, session: AsyncSession):
        self.message_repo = MessageRepository(session)


    async def create_message(
        self,
        conversation_id: int,
        sender_type: str,
        sender_id: int,
        content: str,
        is_auto_reply: bool = False,
        confidence: float = None,
        needs_review: bool = False
    ):
        """Создать новое сообщение."""
        
        new_message = await self.message_repo.create_message(
            conversation_id=conversation_id,
            sender_type=sender_type,
            sender_id=sender_id,
            content=content,
            is_auto_reply=is_auto_reply,
            confidence=confidence,
            needs_review=needs_review
        )
        
        # Если нужно ревью - отмечаем диалог
        if needs_review:
            await self.message_repo.mark_conversation_for_review(conversation_id)

        return new_message


    async def get_messages_by_conversation(self, conversation_id: int):
        """Получить все сообщения для заданного conversation_id."""
        
        return await self.message_repo.get_messages_by_conversation(conversation_id)
