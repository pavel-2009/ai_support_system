"""Роутеры пользователей и аутентификации."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db import get_async_session
from app.models.user import User
from app.schemas.token import Token
from app.schemas.user import UserCreate, UserGet, UserLogin, UserUpdate
from app.services.user_service import UserService

users_router = APIRouter(prefix="/users", tags=["users"])
auth_router = APIRouter(prefix="/auth", tags=["auth"])


@users_router.get("/", response_model=list[UserGet], summary="Получить список пользователей")
async def get_all_users(
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> list[UserGet]:
    if current_user.role.value != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав.")

    return await UserService.get_all_users(session)


@users_router.get("/me", response_model=UserGet, summary="Текущий пользователь")
async def get_me(current_user: User = Depends(get_current_user)) -> UserGet:
    return current_user


@users_router.get("/{user_id}", response_model=UserGet, summary="Получить пользователя по ID")
async def get_user_by_id(
    user_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> UserGet:
    if current_user.role.value != "admin" and current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав.")

    try:
        return await UserService.get_user_by_id(session, user_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@users_router.post("/", response_model=UserGet, status_code=status.HTTP_201_CREATED, summary="Создать пользователя")
async def create_user(
    data: UserCreate,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> UserGet:
    try:
        return await UserService.create_user_by_admin(session, data, current_user)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@users_router.patch("/{user_id}", response_model=UserGet, summary="Обновить пользователя")
async def update_user(
    user_id: int,
    data: UserUpdate,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> UserGet:
    try:
        return await UserService.update_user(session, user_id, data, current_user)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@users_router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Удалить пользователя")
async def delete_user(
    user_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> None:
    try:
        await UserService.delete_user(session, user_id, current_user)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@auth_router.post("/register", response_model=UserGet, status_code=status.HTTP_201_CREATED, summary="Регистрация")
async def register_user(
    data: UserCreate,
    session: AsyncSession = Depends(get_async_session),
) -> UserGet:
    try:
        return await UserService.register_user(session, data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@auth_router.post("/login", response_model=Token, summary="Логин")
async def login_user(
    data: UserLogin,
    session: AsyncSession = Depends(get_async_session),
) -> Token:
    try:
        return await UserService.login_user(session, data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


@auth_router.post("/refresh", response_model=Token, summary="Обновить токен")
async def refresh_token(current_user: User = Depends(get_current_user)) -> Token:
    return await UserService.refresh_token(current_user)
