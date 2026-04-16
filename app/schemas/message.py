"""Pydantic схемы для сообщений."""

from pydantic import BaseModel, Field


class MessageBase(BaseModel):
    """Базовая схема для сообщений."""
    
    conversation_id: int = Field(..., description="ID беседы, к которой относится сообщение")
    sender_type: str = Field(..., description="Тип отправителя (например, 'user' или 'agent')")
    sender_id: int = Field(..., description="ID отправителя")
    content: str = Field(..., description="Содержимое сообщения")
    is_auto_reply: bool = Field(False, description="Флаг, указывающий, является ли сообщение автоматическим ответом")
    confidence: float = Field(None, description="Уровень уверенности для автоматических ответов")
    needs_review: bool = Field(False, description="Флаг, указывающий, требует ли сообщение проверки")


class MessageGet(MessageBase):
    """Схема для получения сообщений."""
    
    id: int = Field(..., description="ID сообщения")
    created_at: str = Field(..., description="Дата и время создания сообщения")
    
    class Config:
        orm_mode = True
        
        
class MessageCreate(MessageBase):
    """Схема для создания сообщений."""
    pass
