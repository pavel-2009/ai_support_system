"""Pydantic схемы для сообщений."""

from datetime import datetime

import bleach
from pydantic import BaseModel, ConfigDict, Field, field_validator


class MessageCreate(BaseModel):
    """Схема для создания сообщений."""

    content: str = Field(
        ...,
        min_length=1,
        max_length=10_000,
        description="Содержимое сообщения",
    )

    @field_validator("content")
    @classmethod
    def sanitize_content(cls, value: str) -> str:
        """Удалить HTML-теги и потенциально опасную разметку из сообщения."""
        sanitized = bleach.clean(
            value,
            tags=[],
            attributes={},
            protocols=[],
            strip=True,
        )
        if not sanitized.strip():
            raise ValueError("Содержимое сообщения не может быть пустым")
        return sanitized


class MessageGet(BaseModel):
    """Схема для получения сообщений."""

    id: int = Field(..., description="ID сообщения")
    conversation_id: int = Field(..., description="ID беседы, к которой относится сообщение")
    sender_type: str = Field(..., description="Тип отправителя (например, 'user' или 'agent')")
    sender_id: int | None = Field(None, description="ID отправителя; отсутствует для AI-сообщений")
    content: str = Field(..., description="Содержимое сообщения")
    is_auto_reply: bool = Field(..., description="Флаг автоматического ответа")
    confidence: float | None = Field(None, description="Уровень уверенности для автоответов")
    needs_review: bool = Field(..., description="Требуется ли проверка")
    created_at: datetime = Field(..., description="Дата и время создания сообщения")

    model_config = ConfigDict(from_attributes=True)
