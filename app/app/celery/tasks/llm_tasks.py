"""Задачи для фоновой работы с LLM."""

import asyncio
import os
import time

from opentelemetry import trace
from celery.signals import worker_process_init, worker_process_shutdown, worker_ready
from prometheus_client import CollectorRegistry, multiprocess, start_http_server

from app.celery.celery_app import celery_app
from app.core.config import settings
from app.core.cache import Cache
from app.core.redis import create_redis_client
from app.core.correlation import set_correlation_id
from app.core.circut_breaker import CircuitOpen
from app.core.logging import get_logger
from app.core.metrics import (
    celery_task_duration_seconds,
    celery_tasks_total,
    llm_latency_seconds,
)
from app.core.telemetry import get_tracer
from app.core.uow import UnitOfWork
from app.celery.worker_db import close_worker_database, get_worker_session_factory, initialize_worker_database
from app.models.conversation import Status
from app.repositories.llm_repo import LLMRepository
from app.schemas.llm import LLMResponse
from app.services.conversation_service import ConversationService
from app.services.message_service import MessageService


logger = get_logger(__name__)
tracer = get_tracer("app.celery")
RETRYABLE_TASK_ERRORS = (CircuitOpen, ConnectionError, TimeoutError)


@worker_ready.connect
def start_prometheus_exporter(**kwargs) -> None:
    """Expose worker-process metrics through a multiprocess Prometheus registry."""
    if not os.environ.get("PROMETHEUS_MULTIPROC_DIR"):
        return

    registry = CollectorRegistry()
    multiprocess.MultiProcessCollector(registry)
    start_http_server(8002, addr="0.0.0.0", registry=registry)


@worker_process_init.connect
def initialize_worker_database_process(**kwargs) -> None:
    """Initialize one database engine/session factory in each prefork worker process."""
    initialize_worker_database()


@worker_process_shutdown.connect
def shutdown_worker_database_process(pid=None, **kwargs) -> None:
    """Dispose the worker-local database engine before the process exits."""
    asyncio.run(close_worker_database())
    if pid is not None:
        multiprocess.mark_process_dead(pid)


@celery_app.task(bind=True)
def process_llm_task(task, conversation_id: int, correlation_id: str = "-") -> str:
    """Обработать LLM-запрос с повтором только при временных ошибках."""
    set_correlation_id(correlation_id)
    task_name = task.name or "unknown"
    started_at = time.perf_counter()
    outcome = "failure"
    try:
        with tracer.start_as_current_span("celery.process_llm_task") as span:
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
                outcome = "retry"
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

            outcome = "success"
            logger.info("celery_task_succeeded", conversation_id=conversation_id)
            return "ok"
    finally:
        celery_tasks_total.labels(task_name, outcome).inc()
        celery_task_duration_seconds.labels(task_name).observe(time.perf_counter() - started_at)


async def _process_llm_task_async(conversation_id: int) -> None:
    """Обработать LLM-запрос короткими DB-фазами без удержания connection во время генерации."""
    session_factory = get_worker_session_factory()
    redis_client = create_redis_client()

    try:
        llm_repo = LLMRepository()
        cache = Cache(redis_client)

        # Phase 1: read conversation state and prompt, then release the DB session.
        async with UnitOfWork(session_factory) as uow:
            conversation_repository = getattr(uow, "conversation", None)
            if conversation_repository is not None:
                conversation = await conversation_repository.get_conversation_by_id(conversation_id)
                if conversation is None or conversation.status != Status.PENDING_AI:
                    logger.info(
                        "LLM PIPELINE SKIPPED: conversation_id=%s is no longer awaiting AI",
                        conversation_id,
                    )
                    return

            messages = await llm_repo.get_prompt(
                conversation_id,
                uow.session,
            )

        logger.info("llm_generation_started", conversation_id=conversation_id)

        # No DB session/transaction is held while waiting for the LLM.
        with llm_latency_seconds.time():
            response: LLMResponse = await llm_repo.request_response(messages, conversation_id=conversation_id)

        logger.info(
            "llm_response_validated",
            conversation_id=conversation_id,
            confidence=response.confidence,
        )

        # Phase 2: persist the result in a fresh, short-lived DB transaction.
        async with UnitOfWork(session_factory) as uow:
            message_service = MessageService(uow, cache)
            conversation_service = ConversationService(uow, cache)

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
                    "ai_message_persisted",
                    conversation_id=conversation_id,
                    message_id=getattr(message, "id", None),
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
                    "ai_message_persisted_for_review",
                    conversation_id=conversation_id,
                    message_id=getattr(message, "id", None),
                )
                return

            logger.info(
                "llm_escalation_required",
                conversation_id=conversation_id,
                confidence=response.confidence,
            )
            await conversation_service.escalate(conversation_id)
    finally:
        try:
            await redis_client.aclose()
        finally:
            logger.debug(
                "CELERY DB SESSION FACTORY REUSED: conversation_id=%s",
                conversation_id,
            )
