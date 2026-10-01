"""Пользовательский роутер для работы с сообщениями."""

import hashlib
import json

from fastapi import APIRouter, Depends, HTTPException, Request, status
from redis.asyncio import Redis

from app.celery.tasks.llm_tasks import process_llm_task
from app.core.correlation import get_correlation_id
from app.core.dependencies import (
    get_idempotency_key,
    get_message_service,
    get_open_conversation_for_user,
    get_redis_client,
    require_authenticated_user,
)
from app.core.idempotency import IdempotencyKey
from app.core.logging import get_logger
from app.core.rate_limit import get_user_identifier, limiter, rate_limit
from app.models.conversation import Conversation, Status
from app.models.message import Message
from app.models.user import User
from app.schemas.message import MessageCreate, MessageGet
from app.services.message_service import MessageService

router = APIRouter(prefix="/conversations", tags=["messages"])
logger = get_logger(__name__)


def make_idempotency_key(user_id: int, conversation_id: int, key: str) -> str:
    value = f"{user_id}:{conversation_id}:{key}"
    return "idempotency:message:" + hashlib.sha256(value.encode()).hexdigest()


def make_fingerprint(message: MessageCreate) -> str:
    value = json.dumps(message.model_dump(), sort_keys=True)
    return hashlib.sha256(value.encode()).hexdigest()


@router.post(
    "/{conversation_id}/messages",
    response_model=MessageGet,
    status_code=status.HTTP_201_CREATED,
    summary="Создать новое сообщение в беседе",
)
@limiter.limit(rate_limit("10000/minute"), key_func=get_user_identifier)
async def send_message(
    request: Request,
    message: MessageCreate,
    conversation: Conversation = Depends(get_open_conversation_for_user),
    current_user: User = Depends(require_authenticated_user),
    message_service: MessageService = Depends(get_message_service),
    idempotency_key: str | None = Depends(get_idempotency_key),
    redis_client: Redis = Depends(get_redis_client),
) -> MessageGet:
    """Отправить новое сообщение в беседе."""
    idempotency = IdempotencyKey(redis_client) if idempotency_key else None
    storage_key = None
    fingerprint = None

    if idempotency_key:
        storage_key = make_idempotency_key(
            current_user.id,
            conversation.id,
            idempotency_key,
        )
        fingerprint = make_fingerprint(message)

        state = await idempotency.get(storage_key)
        if state is not None:
            if state["fingerprint"] != fingerprint:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Idempotency-Key уже использован с другим сообщением.",
                )
            if state["status"] == "completed":
                return MessageGet.model_validate(state["response"])
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Запрос с этим Idempotency-Key уже выполняется.",
            )

        if not await idempotency.reserve(storage_key, fingerprint):
            state = await idempotency.get(storage_key)
            if state and state["fingerprint"] == fingerprint and state["status"] == "completed":
                return MessageGet.model_validate(state["response"])
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Запрос с этим Idempotency-Key уже выполняется.",
            )

    should_process_ai = (
        conversation.status == Status.OPEN
        or (
            conversation.status == Status.WAITING_FOR_USER
            and conversation.operator_id is None
        )
    )

    try:
        new_message = await message_service.create_message(
            conversation_id=conversation.id,
            sender_type="user",
            sender_id=current_user.id,
            content=message.content,
            is_auto_reply=False,
        )
        if new_message is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Диалог сейчас не принимает сообщения пользователя.",
            )

        response = MessageGet.model_validate(new_message)

        if idempotency:
            await idempotency.complete(
                storage_key,
                fingerprint,
                response.model_dump(mode="json"),
            )
    except Exception:
        if idempotency:
            await idempotency.delete(storage_key)
        raise

    if should_process_ai:
        try:
            process_llm_task.delay(
                conversation_id=conversation.id,
                correlation_id=get_correlation_id(),
            )
        except Exception:
            logger.exception("Failed to enqueue AI task for conversation %s", conversation.id)

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
    return await message_service.get_messages_by_conversation(conversation.id)
