"""Роутер для работы с сообщениями."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import (
    get_conversation_service,
    get_current_user,
    get_message_service,
)
from app.models.message import Message
from app.models.user import User
from app.schemas.message import MessageCreate, MessageGet
from app.services.conversation_service import ConversationService
from app.services.message_service import MessageService


router = APIRouter(
    prefix="/conversations",
    tags=["messages"],
)


@router.post(
    "/{conversation_id}/messages",
    response_model=MessageGet,
    status_code=status.HTTP_201_CREATED,
    summary="Создать новое сообщение в беседе",
)
async def send_message(
    conversation_id: int,
    message: MessageCreate,
    current_user: User = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service),
    message_service: MessageService = Depends(get_message_service),
) -> MessageGet:
    """Отправить новое сообщение в беседе."""

    conversation = await conversation_service.get_conversation_by_id(conversation_id)
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Беседа не найдена")

    if current_user.id not in [conversation.user_id, conversation.operator_id]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Вы не являетесь участником этой беседы",
        )

    new_message: Message = await message_service.create_message(
        conversation_id=conversation_id,
        sender_type="user",
        sender_id=current_user.id,
        content=message.content,
        is_auto_reply=False,
    )

    return new_message


@router.get(
    "/{conversation_id}/messages",
    response_model=list[MessageGet],
    summary="Получить все сообщения в беседе",
)
async def get_messages(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service),
    message_service: MessageService = Depends(get_message_service),
) -> list[MessageGet]:
    """Получить все сообщения в беседе."""

    conversation = await conversation_service.get_conversation_by_id(conversation_id)
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Беседа не найдена")

    if current_user.id not in [conversation.user_id, conversation.operator_id]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Вы не являетесь участником этой беседы",
        )

    return await message_service.get_messages_by_conversation(conversation_id)
