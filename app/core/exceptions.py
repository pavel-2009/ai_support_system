"""Кастомные исключения для приложения."""

from exceptions import Exception


class LLMResponseFailed(Exception):
    """Исключение, возникающее при неудачном получении ответа от LLM модели."""
    pass
