"""Задачи для фоновой работы с LLM."""

import asyncio

from app.core.config import settings
from app.celery.celery_app import celery_app
from app.db import async_session
from app.repositories.llm_repo import LLMRepository
from app.services.conversation_service import ConversationService
from app.services.llm_service import LLMService
from app.services.message_service import MessageService
from app.models.conversation import Status
from app.schemas.llm import LLMResponse


@celery_app.task(bind=True, max_retries=settings.LLM_RETRY_ATTEMPTS, default_retry_delay=5)
def process_llm_task(
    self,
    conversation_id: int,
    ) -> str:
    """Обработка задачи LLM с повторными попытками при неудаче."""

    try:
        asyncio.run(_process_llm_task_async(conversation_id))
    except Exception as exc:
        raise self.retry(exc=exc)

    return "ok"


async def _process_llm_task_async(conversation_id: int) -> None:
    """Асинхронная обработка LLM-задачи с инициализацией зависимостей внутри Celery."""
    async with async_session() as session:
        llm_service = LLMService(LLMRepository())
        message_service = MessageService(session)
        conversation_service = ConversationService(session)

        response: LLMResponse = await llm_service.generate_response(conversation_id, session)
        confidence = response.confidence if hasattr(response, "confidence") else 0

        if confidence >= settings.LLM_AI_CONFIDENCE_THRESHOLD:
            await message_service.create_message(
                conversation_id=conversation_id,
                sender_type="ai",
                sender_id=None,
                content=response.answer,
                is_auto_reply=True,
                confidence=confidence,
                needs_review=False,
            )
            return
        
        elif confidence >= settings.LLM_ESCALATION_CONFIDENCE_THRESHOLD:
            await message_service.create_message(
                conversation_id=conversation_id,
                sender_type="ai",
                sender_id=None,
                content=response.answer,
                is_auto_reply=True,
                confidence=confidence,
                needs_review=True,
            )
            return

        await conversation_service.update_conversation_status(
            conversation_id=conversation_id,
            new_status=Status.ESCALATED,
        )
