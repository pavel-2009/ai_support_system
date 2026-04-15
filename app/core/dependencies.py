"""Базовые зависимости для приложения."""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_access_token
from app.db import get_async_session
from app.models.user import User
from app.services.user_service import UserService
from app.services.conversation_service import ConversationService
from app.services_init import (
    get_conversation_service,
    get_user_service,
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_async_session),
) -> User:
    """Получить текущего пользователя по access JWT."""
    payload = verify_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный токен доступа.",
        )

    user_id = payload.get("user_id")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Некорректный payload токена.",
        )

    try:
        return await UserService.get_user_by_id(session, int(user_id))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь из токена не найден.",
        ) from exc
        
        
async def get_async_session() -> AsyncSession:
    """Зависимость для получения асинхронной сессии базы данных."""
    return await get_async_session()
        

async def get_conversation_service() -> ConversationService:
    """Зависимость для получения сервиса работы с диалогами."""
    return await get_conversation_service()


async def get_user_service() -> UserService:
    """Зависимость для получения сервиса работы с пользователями."""
    return await get_user_service()