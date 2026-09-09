"""Задачи для фоновой работы с LLM."""

import asyncio

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.celery.celery_app import celery_app
from app.core.config import settings
from app.core.logging import get_logger
from app.core.uow import UnitOfWork
from app.db import create_database_engine
from app.models.conversation import Status
from app.repositories.llm_repo import LLMRepository
from app.schemas.llm import LLMResponse
from app.services.conversation_service import ConversationService
from app.services.llm_service import LLMService
from app.services.message_service import MessageService


logger = get_logger(__name__)


@celery_app.task
def process_llm_task(conversation_id: int) -> str:
    """Обработать LLM-запрос ровно один раз."""
    logger.info("CELERY LLM START: conversation_id=%s", conversation_id)
    try:
        asyncio.run(_process_llm_task_async(conversation_id))
    except Exception:
        logger.exception("CELERY LLM FAILED: conversation_id=%s", conversation_id)
        raise

    logger.info("CELERY LLM SUCCESS: conversation_id=%s", conversation_id)
    return "ok"


async def _process_llm_task_async(conversation_id: int) -> None:
    """Асинхронная обработка с отдельным DB engine для этого event loop."""
    database_engine = create_database_engine(settings.DATABASE_URL)
    session_factory = async_sessionmaker(
        database_engine,
        expire_on_commit=False,
    )

    try:
        async with UnitOfWork(session_factory) as uow:
            logger.info(
                "LLM PIPELINE: generating response for conversation_id=%s",
                conversation_id,
            )
            llm_service = LLMService(LLMRepository())
            message_service = MessageService(uow)
            conversation_service = ConversationService(uow)

            response: LLMResponse = await llm_service.generate_response(
                conversation_id,
                uow.session,
            )
            logger.info(
                "LLM PIPELINE: validated response conversation_id=%s confidence=%s",
                conversation_id,
                response.confidence,
            )

            if response.confidence >= settings.LLM_AI_CONFIDENCE_THRESHOLD:
                message = await message_service.create_message(
                    conversation_id=conversation_id,
                    sender_type="ai",
                    sender_id=None,
                    content=response.answer,
                    is_auto_reply=True,
                    confidence=response.confidence,
                    needs_review=False,
                )
                logger.info(
                    "LLM PIPELINE: AI message persisted id=%s",
                    getattr(message, "id", None),
                )
                return

            if response.confidence >= settings.LLM_ESCALATION_CONFIDENCE_THRESHOLD:
                message = await message_service.create_message(
                    conversation_id=conversation_id,
                    sender_type="ai",
                    sender_id=None,
                    content=response.answer,
                    is_auto_reply=True,
                    confidence=response.confidence,
                    needs_review=True,
                )
                logger.info(
                    "LLM PIPELINE: review message persisted id=%s",
                    getattr(message, "id", None),
                )
                return

            logger.info(
                "LLM PIPELINE: confidence too low; escalating conversation_id=%s",
                conversation_id,
            )
            await conversation_service.update_conversation_status(
                conversation_id=conversation_id,
                new_status=Status.ESCALATED,
            )
    finally:
        await database_engine.dispose()
        logger.debug(
            "CELERY DB ENGINE DISPOSED: conversation_id=%s",
            conversation_id,
        )
