"""Роутер для работы с сообщениями."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.services.message_service import MessageService
from app.services.conversation_service import ConversationService
from app.services_init import get_message_service, get_conversation_service
from app.core.dependencies import get_current_user
from app.schemas.message import MessageCreate, MessageGet
from app.models.conversation import Conversation
from app.models.user import User
from app.models.message import Message


router = APIRouter(
    prefix="/conversations",
    tags=["messages"]
)


@router.post("/{conversation_id}/messages", response_model=MessageGet, status_code=status.HTTP_201_CREATED, summary="Создать новое сообщение в беседе")
async def send_message(
    conversation_id: int,
    message: MessageCreate,
    current_user: User = Depends(get_current_user),
) -> MessageGet:
    """Отправить новое сообщение в беседе."""
    
    conversation_service: ConversationService = await get_conversation_service()
    message_service: MessageService = await get_message_service()
    
    # Проверяем, что беседа существует
    conversation: Conversation = await conversation_service.get_conversation_by_id(conversation_id)
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Беседа не найдена")
    
    # Проверка, что текущий пользователь является участником беседы
    if current_user.id not in [conversation.user_id, conversation.operator_id]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не являетесь участником этой беседы")
    
    # Создаем новое сообщение
    new_message: Message = await message_service.create_message(
        conversation_id=conversation_id,
        sender_type="user",
        sender_id=current_user.id,
        content=message.content,
        is_auto_reply=False
    )
    
    return MessageGet.model_dump(new_message)


@router.get("/{conversation_id}/messages", response_model=list[MessageGet], summary="Получить все сообщения в беседе")
async def get_messages(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
) -> list[MessageGet]:
    """Получить все сообщения в беседе."""
    
    conversation_service: ConversationService = await get_conversation_service()
    message_service: MessageService = await get_message_service()
    
    # Проверяем, что беседа существует
    conversation: Conversation = await conversation_service.get_conversation_by_id(conversation_id)
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Беседа не найдена")
    
    # Проверка, что текущий пользователь является участником беседы
    if current_user.id not in [conversation.user_id, conversation.operator_id]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не являетесь участником этой беседы")
    
    # Получаем все сообщения для данной беседы
    messages: list[Message] = await message_service.get_messages_by_conversation(conversation_id)
    
    return [MessageGet.model_dump(message) for message in messages]
