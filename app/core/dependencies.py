"""Базовые зависимости для приложения."""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_access_token
from app.db import get_async_session
from app.models.user import User
from app.services.conversation_service import ConversationService
from app.services.user_service import UserService

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
        return await UserService(session).get_user_by_id(int(user_id))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь из токена не найден.",
        ) from exc


async def get_user_service(
    session: AsyncSession = Depends(get_async_session),
) -> UserService:
    """Зависимость для получения сервиса работы с пользователями."""
    return UserService(session)


async def get_conversation_service(
    session: AsyncSession = Depends(get_async_session),
) -> ConversationService:
    """Зависимость для получения сервиса работы с диалогами."""
    return ConversationService(session)
