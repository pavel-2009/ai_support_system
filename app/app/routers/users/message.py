"""Пользовательский роутер для работы с сообщениями."""

from fastapi import APIRouter, Depends, status

from app.core.dependencies import (
    get_message_service,
    get_open_conversation_for_user,
    require_authenticated_user,
)
from app.core.logging import get_logger
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.user import User
from app.schemas.message import MessageCreate, MessageGet
from app.services.message_service import MessageService
from app.celery.tasks.llm_tasks import process_llm_task

router = APIRouter(
    prefix="/conversations",
    tags=["messages"],
)
logger = get_logger(__name__)


@router.post(
    "/{conversation_id}/messages",
    response_model=MessageGet,
    status_code=status.HTTP_201_CREATED,
    summary="Создать новое сообщение в беседе",
)
async def send_message(
    message: MessageCreate,
    conversation: Conversation = Depends(get_open_conversation_for_user),
    current_user: User = Depends(require_authenticated_user),
    message_service: MessageService = Depends(get_message_service),
) -> MessageGet:
    """Отправить новое сообщение в беседе."""
    logger.info(
        "Пользователь %s отправляет сообщение в диалог %s.",
        current_user.id,
        conversation.id,
    )
    new_message: Message = await message_service.create_message(
        conversation_id=conversation.id,
        sender_type="user",
        sender_id=current_user.id,
        content=message.content,
        is_auto_reply=False,
    )

    try:
        process_llm_task.delay(
            conversation_id=conversation.id,
        )
    except Exception:
        logger.exception(
            "Не удалось поставить LLM-задачу в очередь для диалога %s.",
            conversation.id,
        )

    return new_message


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
    logger.info(
        "Пользователь %s запрашивает сообщения диалога %s.",
        current_user.id,
        conversation.id,
    )
    return await message_service.get_messages_by_conversation(conversation.id)
