"""Схема для валидации выходящих данных при работе с LLM моделью."""

from pydantic import BaseModel


class LLMResponse(BaseModel):
    """Схема для валидации выходящих данных при работе с LLM моделью."""

    answer: str
    confidence: float
    topic: str
