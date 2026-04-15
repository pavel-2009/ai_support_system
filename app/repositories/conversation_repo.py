"""Репозиторий для работы с диалогами."""

from sqlalchemy import select, update, insert, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation, Status, Priority, Channel


class ConversationRepository:
    """Репозиторий для работы с диалогами."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_conversation(
        self,
        user_id: int,
        priority: Priority,
        channel: Channel
    ) -> Conversation:
        """Создать новый диалог."""
        new_conversation = Conversation(
            user_id=user_id,
            priority=priority,
            channel=channel,
            status=Status.OPEN
        )
        self.session.add(new_conversation)
    
        await self.session.commit()
        await self.session.refresh(new_conversation)
        
        return new_conversation
    
    
    async def get_conversation_by_id(self, conversation_id: int) -> Conversation:
        """Получить диалог по ID."""
        result = await self.session.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        
        return result.scalar_one_or_none()
    
    
    async def update_conversation_status(self, conversation_id: int, new_status: Status) -> Conversation:
        """Обновить статус диалога."""
        result = await self.session.execute(
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(status=new_status, updated_at=func.now())
            .returning(Conversation)
        )
        
        await self.session.commit()
        
        return result.scalar_one_or_none()
    
    
    async def assign_operator(self, conversation_id: int, operator_id: int) -> Conversation:
        """Назначить оператора на диалог."""
        result = await self.session.execute(
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(operator_id=operator_id, status=Status.WAITING_FOR_OPERATOR, updated_at=func.now())
            .returning(Conversation)
        )
        
        await self.session.commit()
        
        return result.scalar_one_or_none()
    
        
    async def close_conversation(self, conversation_id: int) -> Conversation:
        """Закрыть диалог."""
        result = await self.session.execute(
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(status=Status.CLOSED, closed_at=func.now(), updated_at=func.now())
            .returning(Conversation)
        )
        
        await self.session.commit()
        
        return result.scalar_one_or_none()
    