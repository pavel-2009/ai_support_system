"""Пользовательские роутеры пользователей и аутентификации."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_authenticated_user
from app.core.logging import get_logger
from app.core.security import create_tokens, verify_refresh_token
from app.db import get_async_session
from app.models.user import User
from app.schemas.token import Token
from app.schemas.user import UserCreate, UserGet, UserLogin, UserUpdate
from app.services.user_service import UserService

users_router = APIRouter(prefix="/users", tags=["users"])
auth_router = APIRouter(prefix="/auth", tags=["auth"])
admin_router = APIRouter(prefix="/admin", tags=["admin"])
logger = get_logger(__name__)


class RefreshTokenRequest(BaseModel):
    refresh_token: str


def _http_error(code: int, exc: ValueError) -> HTTPException:
    return HTTPException(status_code=code, detail=str(exc))


@users_router.get("/", response_model=list[UserGet], summary="Получить список пользователей")
async def get_all_users(
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_authenticated_user),
) -> list[UserGet]:
    """Получить список всех пользователей (только для админов)."""
    if current_user.role.value != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав.")

    return await UserService(session).get_all_users()


@users_router.get("/me", response_model=UserGet, summary="Текущий пользователь")
async def get_me(current_user: User = Depends(require_authenticated_user)) -> UserGet:
    """Получение данных текущего пользователя."""
    return current_user


@users_router.get("/{user_id}", response_model=UserGet, summary="Получить пользователя по ID")
async def get_user_by_id(
    user_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_authenticated_user),
) -> UserGet:
    """Получить пользователя по ID."""
    if current_user.role.value != "admin" and current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав.")

    try:
        return await UserService(session).get_user_by_id(user_id)
    except ValueError as exc:
        logger.exception("Ошибка получения пользователя %s.", user_id)
        raise _http_error(status.HTTP_404_NOT_FOUND, exc) from exc


@users_router.post("/", response_model=UserGet, status_code=status.HTTP_201_CREATED, summary="Создать пользователя")
async def create_user(
    data: UserCreate,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_authenticated_user),
) -> UserGet:
    """Создать нового пользователя."""
    if current_user.role.value != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав.")
    try:
        return await UserService(session).create_user_by_admin(data, current_user)
    except ValueError as exc:
        logger.exception("Ошибка создания пользователя администратором %s.", current_user.id)
        raise _http_error(status.HTTP_400_BAD_REQUEST, exc) from exc


@users_router.patch("/{user_id}", response_model=UserGet, summary="Обновить пользователя")
async def update_user(
    user_id: int,
    data: UserUpdate,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_authenticated_user),
) -> UserGet:
    """Изменить данные пользователя."""
    try:
        return await UserService(session).update_user(user_id, data, current_user)
    except ValueError as exc:
        logger.exception("Ошибка обновления пользователя %s.", user_id)
        raise _http_error(status.HTTP_400_BAD_REQUEST, exc) from exc


@users_router.patch("/me", response_model=UserGet, summary="Обновить текущего пользователя")
async def update_me(
    data: UserUpdate,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_authenticated_user),
) -> UserGet:
    """Обновить данные текущего пользователя."""
    return await update_user(current_user.id, data, session, current_user)


@users_router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Удалить пользователя")
async def delete_user(
    user_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_authenticated_user),
) -> None:
    """Удалить пользователя."""
    try:
        await UserService(session).delete_user(user_id, current_user)
    except ValueError as exc:
        logger.exception("Ошибка удаления пользователя %s.", user_id)
        raise _http_error(status.HTTP_400_BAD_REQUEST, exc) from exc


@auth_router.post("/register", response_model=UserGet, status_code=status.HTTP_201_CREATED, summary="Регистрация")
async def register_user(
    data: UserCreate,
    session: AsyncSession = Depends(get_async_session),
) -> UserGet:
    """Регистрация нового пользователя."""
    try:
        return await UserService(session).register_user(data)
    except ValueError as exc:
        logger.exception("Ошибка регистрации пользователя %s.", data.email)
        raise _http_error(status.HTTP_400_BAD_REQUEST, exc) from exc


@auth_router.post("/login", response_model=Token, summary="Логин")
async def login_user(
    data: UserLogin,
    session: AsyncSession = Depends(get_async_session),
) -> Token:
    """Аутентификация пользователя и выдача токенов."""
    try:
        return await UserService(session).login_user(data)
    except ValueError as exc:
        logger.exception("Ошибка входа пользователя %s.", data.email)
        raise _http_error(status.HTTP_401_UNAUTHORIZED, exc) from exc


@auth_router.post("/refresh", response_model=Token, summary="Обновить токен")
async def refresh_token(
    data: RefreshTokenRequest,
) -> Token:
    """Обновить access токен с помощью refresh токена."""
    payload = verify_refresh_token(data.refresh_token)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Недействительный refresh токен.")
    user_data = {k: v for k, v in payload.items() if k not in {"exp", "iat", "nbf", "jti"}}
    return create_tokens(user_data)


@admin_router.get("/users", response_model=list[UserGet], summary="Админ: список пользователей")
async def admin_get_all_users(
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_authenticated_user),
) -> list[UserGet]:
    """Получить список всех пользователей (только для админов)."""
    return await get_all_users(session, current_user)


@admin_router.post("/users", response_model=UserGet, status_code=status.HTTP_201_CREATED, summary="Админ: создать пользователя")
async def admin_create_user(
    data: UserCreate,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_authenticated_user),
) -> UserGet:
    """Создать нового пользователя (только для админов)."""
    return await create_user(data, session, current_user)
