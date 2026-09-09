"""Схема для валидации выходящих данных при работе с LLM моделью."""

from pydantic import BaseModel, ConfigDict, Field


class LLMResponse(BaseModel):
    """Строгий контракт ответа LLM."""

    model_config = ConfigDict(extra="forbid")

    answer: str
    confidence: float = Field(ge=0.0, le=1.0)
    topic: str
