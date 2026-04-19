"""Сервис для взаимодействия с LLM моделями."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.llm_repo import LLMRepository


class LLMService:
    """Сервис для взаимодействия с LLM моделями."""

    def __init__(self, llm_repo: LLMRepository):
        self.llm_repo = llm_repo

    def generate_response(self, conversation_id: int, session: AsyncSession) -> str:
        """Генерирует ответ на заданный вопрос с помощью LLM модели."""
        
        return self.llm_repo.get_llm_response(conversation_id, session)
