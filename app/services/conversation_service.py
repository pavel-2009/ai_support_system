"""Сервис для работы с диалогами."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.conversation_repo import ConversationRepository


class ConversationService:
    """Сервис для работы с диалогами."""

    def __init__(
        self,
        session: AsyncSession,
    ):
        self.session = session
        self.conversation_repo = ConversationRepository(session)


    async def create_conversation(self, user_id: int, priority: str, channel: str):
        """Создать новый диалог."""
        return await self.conversation_repo.create_conversation(user_id, priority, channel)


    async def get_conversation_by_id(self, conversation_id: int):
        """Получить диалог по ID."""
        return await self.conversation_repo.get_conversation_by_id(conversation_id)


    async def update_conversation_status(self, conversation_id: int, new_status: str):
        """Обновить статус диалога."""
        return await self.conversation_repo.update_conversation_status(conversation_id, new_status)


    async def assign_operator(self, conversation_id: int, operator_id: int):
        """Назначить оператора на диалог."""
        return await self.conversation_repo.assign_operator(conversation_id, operator_id)
    
    
    async def close(self, conversation_id: int):
        """Закрыть диалог."""
        return await self.conversation_repo.update_conversation_status(conversation_id, 'closed')
