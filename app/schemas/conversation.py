"""Pydantic схемы для модели диалога."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.conversation import Channel, Priority, Status


class ConversationBase(BaseModel):
    """Базовая схема для диалога."""

    user_id: int = Field(..., description="Идентификатор владельца диалога")
    operator_id: int | None = Field(None, description="Идентификатор оператора")
    priority: Priority = Field(..., description="Приоритет диалога")
    channel: Channel = Field(..., description="Канал диалога")


class ConversationGet(ConversationBase):
    """Схема для получения информации о диалоге."""

    id: int = Field(..., description="Уникальный идентификатор диалога")
    ai_confidence: float = Field(..., description="Уверенность ИИ в ответе")
    status: Status = Field(..., description="Статус диалога")
    created_at: datetime = Field(..., description="Дата и время создания")
    updated_at: datetime = Field(..., description="Дата и время обновления")
    closed_at: datetime | None = Field(None, description="Дата закрытия диалога")

    model_config = ConfigDict(from_attributes=True)


class ConversationCreate(BaseModel):
    """Схема для создания нового диалога."""

    priority: Priority = Field(default=Priority.MEDIUM)
    channel: Channel = Field(default=Channel.API)


class ConversationUpdate(BaseModel):
    """Схема для обновления информации о диалоге."""

    status: Status | None = Field(None, description="Новый статус")
    operator_id: int | None = Field(None, description="Новый оператор")


class ConversationListResponse(BaseModel):
    """Ответ со списком диалогов и базовой пагинацией."""

    items: list[ConversationGet] = Field(default_factory=list)
    total: int = Field(..., ge=0)
    page: int = Field(..., ge=1)
    size: int = Field(..., ge=1)
