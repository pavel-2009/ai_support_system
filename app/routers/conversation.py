"""Роутер для работы с диалогами."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.conversation_service import ConversationService
from app.db import get_async_session
from app.core.dependencies import (
    get_conversation_service,
    get_user_service,
    get_current_user,
    get_async_session
)

from app.schemas.conversation import ConversationCreate, ConversationGet, ConversationUpdate
from app.models.user import User


router = APIRouter(
    prefix="/conversations",
    tags=["conversations"],
)


@router.post("/", response_model=ConversationGet, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    conversation_data: ConversationCreate,
    current_user: User = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service),
):
    conversation = await conversation_service.create_conversation(
        current_user.id, conversation_data
    )
    return conversation


@router.get("/{conversation_id}", response_model=ConversationGet)
async def get_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service),
):
    conversation = await conversation_service.get_conversation_by_id(conversation_id)
    
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Диалог не найден.")
    
    if conversation.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет доступа к этому диалогу.")
    
    return conversation
