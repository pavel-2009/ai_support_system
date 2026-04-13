"""Схемы для токенов аутентификации и авторизации."""

from pydantic import BaseModel


class Token(BaseModel):
    """Базовая схема для токенов."""
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
