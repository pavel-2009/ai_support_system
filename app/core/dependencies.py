"""Базовые зависимости для приложения."""

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_async_session
from app.core.security import verify_access_token
from app.repositories.user_repo import UserRepository
from app.models.user import User


# === Зависимость для получения текущего пользователя ===
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer

oauth = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_current_user(
    token: str = Depends(oauth),
    session: AsyncSession = Depends(get_async_session)
) -> User:
    """Получить текущего аутентифицированного пользователя."""
    
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный токен доступа."
        )
        
    token = verify_access_token(token)
    
    user_id = token.get("user_id")
    
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный токен доступа."
        )
    
    if not await UserRepository.user_exists(session, user_id=user_id):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден."
        )
        
    user = await UserRepository.get_user_by_id(session, user_id)
    
    return user
