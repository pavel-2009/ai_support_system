"""Сервис для взаимодействия с LLM моделями."""

from sqlalchemy.ext.asyncio import AsyncSession

from ..repositories.llm_repo import LLMRepository
from ..schemas.llm import LLMResponse


class LLMService:
    """Сервис для взаимодействия с LLM моделями."""

    def __init__(self, llm_repo: LLMRepository):
        self.llm_repo = llm_repo

    async def generate_response(self, conversation_id: int, session: AsyncSession) -> LLMResponse:
        """Генерирует ответ на заданный вопрос с помощью LLM модели."""
        
        return await self.llm_repo.get_llm_response(conversation_id, session)
