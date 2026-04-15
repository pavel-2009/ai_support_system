"""Pydantic схемы для модели диалога."""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# === ДИАЛОГ === 
class ConversationBase(BaseModel):
    """Базовая схема для диалога."""
    user_id: int = Field(..., description="Идентификатор пользователя, которому принадлежит диалог")
    operator_id: Optional[int] = Field(None, description="Идентификатор оператора, если диалог с оператором")
    priority: str = Field(..., description="Приоритет диалога")
    channel: str = Field(..., description="Канал, через который ведется диалог")  # Пока просто заглушка, в MVP только API, в будущем может быть расширено до email, sms и т.д.
    
    
class ConversationGet(ConversationBase):
    """Схема для получения информации о диалоге."""
    id: int = Field(..., description="Уникальный идентификатор диалога")
    ai_confidence: float = Field(..., description="Уверенность ИИ в ответе")
    status: str = Field(..., description="Статус диалога")
    created_at: datetime = Field(..., description="Дата и время создания диалога")
    updated_at: datetime = Field(..., description="Дата и время последнего обновления диалога")
    closed_at: Optional[datetime] = Field(None, description="Дата и время закрытия диалога, если он закрыт")    


class ConversationCreate(BaseModel):
    """Схема для создания нового диалога."""
    pass


class ConversationUpdate(BaseModel):
    """Схема для обновления информации о диалоге."""
    status: Optional[str] = Field(None, description="Новый статус диалога")
    operator_id: Optional[int] = Field(None, description="Новый идентификатор оператора, если нужно переназначить диалог")
