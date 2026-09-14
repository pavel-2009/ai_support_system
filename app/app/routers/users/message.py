"""Пользовательский роутер для работы с сообщениями."""

import hashlib
import json

from fastapi import APIRouter, Depends, HTTPException, Request, status
from redis import Redis

from app.core.dependencies import (
    get_message_service,
    get_open_conversation_for_user,
    require_authenticated_user,
    get_idempotency_key,
    get_redis_client,
)
from app.core.logging import get_logger
from app.core.rate_limit import limiter, get_user_identifier
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.user import User
from app.schemas.message import MessageCreate, MessageGet
from app.core.idempotency import IdempotencyKey
from app.services.message_service import MessageService
from app.celery.tasks.llm_tasks import process_llm_task

router = APIRouter(prefix="/conversations", tags=["messages"])
logger = get_logger(__name__)


@router.post(
    "/{conversation_id}/messages",
    response_model=MessageGet,
    status_code=status.HTTP_201_CREATED,
    summary="Создать новое сообщение в беседе",
)
@limiter.limit("30/minute", key_func=get_user_identifier)
async def send_message(
    request: Request,
    message: MessageCreate,
    conversation: Conversation = Depends(get_open_conversation_for_user),
    current_user: User = Depends(require_authenticated_user),
    message_service: MessageService = Depends(get_message_service),
    idempotency_key: str = Depends(get_idempotency_key),
    redis_client: Redis = Depends(get_redis_client),
) -> MessageGet:
    """Отправить новое сообщение в беседе."""
    logger.info("HTTP SEND MESSAGE REQUEST: user=%s conversation=%s idempotency_key=%s", current_user.id, conversation.id, idempotency_key)
    if idempotency_key:
        idempotency = IdempotencyKey(redis_client)
        storage_key = "idempotency:message:" + hashlib.sha256(
            f"{current_user.id}:{conversation.id}:{idempotency_key}".encode()
        ).hexdigest()
        fingerprint = hashlib.sha256(
            json.dumps(message.model_dump(), sort_keys=True).encode()
        ).hexdigest()
        cached = idempotency.get_state(storage_key)
        if cached is not None:
            if cached.get("fingerprint") != fingerprint:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Idempotency-Key уже использован с другим сообщением.",
                )
            if cached.get("status") == "completed":
                return MessageGet.model_validate(cached["response"])
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Запрос с этим Idempotency-Key уже выполняется.",
            )
        if not idempotency.reserve(storage_key, fingerprint):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Запрос с этим Idempotency-Key уже выполняется.",
            )

    logger.info("HTTP SEND MESSAGE: user=%s conversation=%s", current_user.id, conversation.id)
    try:
        new_message: Message = await message_service.create_message(
            conversation_id=conversation.id,
            sender_type="user",
            sender_id=current_user.id,
            content=message.content,
            is_auto_reply=False,
        )
        response = MessageGet.model_validate(new_message)
        if idempotency_key:
            idempotency.store_response(
                storage_key,
                fingerprint,
                response.model_dump(mode="json"),
            )
    except Exception:
        if idempotency_key:
            idempotency.delete(storage_key)
        raise
    logger.info("HTTP SEND MESSAGE PERSISTED: message_id=%s conversation=%s", new_message.id, conversation.id)

    try:
        task = process_llm_task.delay(conversation_id=conversation.id)
        logger.info("CELERY ENQUEUED: task_id=%s conversation_id=%s", task.id, conversation.id)
    except Exception:
        logger.exception("CELERY ENQUEUE FAILED: conversation_id=%s", conversation.id)

    return response


@router.get(
    "/{conversation_id}/messages",
    response_model=list[MessageGet],
    summary="Получить все сообщения в беседе",
)
async def get_messages(
    conversation: Conversation = Depends(get_open_conversation_for_user),
    current_user: User = Depends(require_authenticated_user),
    message_service: MessageService = Depends(get_message_service),
) -> list[MessageGet]:
    """Получить все сообщения в беседе."""
    logger.info("HTTP GET MESSAGES: user=%s conversation=%s", current_user.id, conversation.id)
    messages = await message_service.get_messages_by_conversation(conversation.id)
    logger.info("HTTP GET MESSAGES OK: user=%s conversation=%s count=%s", current_user.id, conversation.id, len(messages))
    return messages
