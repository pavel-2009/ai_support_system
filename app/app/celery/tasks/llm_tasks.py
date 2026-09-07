"""Задачи для фоновой работы с LLM."""

import asyncio

from app.core.config import settings
from app.core.logging import get_logger
from app.celery.celery_app import celery_app
from app.db import async_session
from app.core.uow import UnitOfWork
from app.repositories.llm_repo import LLMRepository
from app.services.conversation_service import ConversationService
from app.services.llm_service import LLMService
from app.services.message_service import MessageService
from app.models.conversation import Status
from app.schemas.llm import LLMResponse


logger = get_logger(__name__)


@celery_app.task(bind=True, max_retries=settings.LLM_RETRY_ATTEMPTS, default_retry_delay=5)
def process_llm_task(self, conversation_id: int) -> str:
    """Обработка задачи LLM с повторными попытками при неудаче."""
    logger.info("CELERY LLM START: conversation_id=%s task_id=%s", conversation_id, self.request.id)
    try:
        asyncio.run(_process_llm_task_async(conversation_id))
    except Exception as exc:
        logger.exception(
            "CELERY LLM FAILED: conversation_id=%s task_id=%s; retrying",
            conversation_id, self.request.id,
        )
        raise self.retry(exc=exc)

    logger.info("CELERY LLM SUCCESS: conversation_id=%s task_id=%s", conversation_id, self.request.id)
    return "ok"


async def _process_llm_task_async(conversation_id: int) -> None:
    """Асинхронная обработка LLM-задачи с инициализацией зависимостей внутри Celery."""
    async with UnitOfWork(async_session) as uow:
        logger.info("LLM PIPELINE: generating response for conversation_id=%s", conversation_id)
        llm_service = LLMService(LLMRepository())
        message_service = MessageService(uow)
        conversation_service = ConversationService(uow)

        response: LLMResponse = await llm_service.generate_response(conversation_id, uow.session)
        confidence = response.confidence if hasattr(response, "confidence") else 0
        logger.info(
            "LLM PIPELINE: response generated conversation_id=%s confidence=%s",
            conversation_id, confidence,
        )

        if confidence >= settings.LLM_AI_CONFIDENCE_THRESHOLD:
            message = await message_service.create_message(
                conversation_id=conversation_id,
                sender_type="ai",
                sender_id=None,
                content=response.answer,
                is_auto_reply=True,
                confidence=confidence,
                needs_review=False,
            )
            logger.info("LLM PIPELINE: AI message persisted id=%s", getattr(message, "id", None))
            return

        if confidence >= settings.LLM_ESCALATION_CONFIDENCE_THRESHOLD:
            message = await message_service.create_message(
                conversation_id=conversation_id,
                sender_type="ai",
                sender_id=None,
                content=response.answer,
                is_auto_reply=True,
                confidence=confidence,
                needs_review=True,
            )
            logger.info("LLM PIPELINE: review message persisted id=%s", getattr(message, "id", None))
            return

        logger.info("LLM PIPELINE: confidence too low; escalating conversation_id=%s", conversation_id)
        await conversation_service.update_conversation_status(
            conversation_id=conversation_id,
            new_status=Status.ESCALATED,
        )
