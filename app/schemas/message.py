"""Pydantic схемы для сообщений."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MessageCreate(BaseModel):
    """Схема для создания сообщений."""

    content: str = Field(..., min_length=1, description="Содержимое сообщения")


class MessageGet(BaseModel):
    """Схема для получения сообщений."""

    id: int = Field(..., description="ID сообщения")
    conversation_id: int = Field(..., description="ID беседы, к которой относится сообщение")
    sender_type: str = Field(..., description="Тип отправителя (например, 'user' или 'agent')")
    sender_id: int = Field(..., description="ID отправителя")
    content: str = Field(..., description="Содержимое сообщения")
    is_auto_reply: bool = Field(..., description="Флаг автоматического ответа")
    confidence: float | None = Field(None, description="Уровень уверенности для автоответов")
    needs_review: bool = Field(..., description="Требуется ли проверка")
    created_at: datetime = Field(..., description="Дата и время создания сообщения")

    model_config = ConfigDict(from_attributes=True)
