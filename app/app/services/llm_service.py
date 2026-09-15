"""Сервис для взаимодействия с LLM моделями."""

from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import (
    retry, stop_after_attempt, wait_exponential, retry_if_exception_type,
    retry_if_not_exception_type, before_sleep_log, RetryCallState
)

from app.repositories.llm_repo import LLMRepository
from app.schemas.llm import LLMResponse
from app.core.circut_breaker import Circuit, CircuitOpen


class LLMService:
    """Сервис для взаимодействия с LLM моделями."""

    def __init__(self, llm_repo: LLMRepository):
        self.llm_repo = llm_repo

    async def generate_response(self, conversation_id: int, session: AsyncSession) -> LLMResponse:
        """Генерирует ответ на заданный вопрос с помощью LLM модели."""
        
        return await self.llm_repo.get_llm_response(conversation_id, session)
