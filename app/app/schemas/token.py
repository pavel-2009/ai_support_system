"""Схемы для токенов аутентификации и авторизации."""

from pydantic import BaseModel


class Token(BaseModel):
    """Базовая схема для токенов."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequest(BaseModel):
    """Запрос на отзыв или ротацию refresh-токена."""
    refresh_token: str


class SessionInfo(BaseModel):
    """Активная сессия пользователя."""
    family_id: str
    jti: str
    expires_at: str
