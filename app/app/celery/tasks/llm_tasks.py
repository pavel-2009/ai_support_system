"""Задачи для фоновой работы с LLM."""

import asyncio

from opentelemetry import trace
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.celery.celery_app import celery_app
from app.core.config import settings
from app.core.circut_breaker import CircuitOpen
from app.core.logging import get_logger
from app.core.telemetry import get_tracer
from app.core.uow import UnitOfWork
from app.db import create_database_engine
from app.models.conversation import Status
from app.repositories.llm_repo import LLMRepository
from app.schemas.llm import LLMResponse
from app.services.conversation_service import ConversationService
from app.services.llm_service import LLMService
from app.services.message_service import MessageService


logger = get_logger(__name__)
tracer = get_tracer("app.celery")
RETRYABLE_TASK_ERRORS = (CircuitOpen, ConnectionError, TimeoutError)


@celery_app.task(bind=True)
def process_llm_task(task, conversation_id: int, correlation_id: str = "-") -> str:
    """Обработать LLM-запрос с повтором только при временных ошибках."""
    set_correlation_id(correlation_id)\n    with tracer.start_as_current_span("celery.process_llm_task") as span:
        span.set_attributes(
            {
                "celery.task.name": task.name,
                "celery.task.id": task.request.id,
                "celery.task.conversation_id": conversation_id,
            }
        )
        logger.info("celery_task_started", conversation_id=conversation_id, task_id=task.request.id)
        try:
            asyncio.run(_process_llm_task_async(conversation_id))
        except RETRYABLE_TASK_ERRORS as exc:
            span.record_exception(exc)
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(exc)))
            logger.warning(
                "CELERY LLM RETRY: conversation_id=%s error=%s",
                conversation_id,
                type(exc).__name__,
            )
            raise task.retry(exc=exc)
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(exc)))
            logger.exception("celery_task_failed", conversation_id=conversation_id)
            raise

        logger.info("celery_task_succeeded", conversation_id=conversation_id)
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
            conversation_repository = getattr(uow, "conversation", None)
            if conversation_repository is not None:
                conversation = await conversation_repository.get_conversation_by_id(conversation_id)
                if conversation is None or conversation.status != Status.PENDING_AI:
                    logger.info("LLM PIPELINE SKIPPED: conversation_id=%s is no longer awaiting AI", conversation_id)
                    return
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
            await conversation_service.escalate(conversation_id)
    finally:
        await database_engine.dispose()
        logger.debug(
            "CELERY DB ENGINE DISPOSED: conversation_id=%s",
            conversation_id,
        )
