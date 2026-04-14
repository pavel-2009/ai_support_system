"""Роутер для работы с пользователями."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.user_service import UserService
from app.db import get_async_session
from app.schemas.user import UserGet, UserCreate, UserUpdate
from app.core.dependencies import get_current_user
from app.models.user import User


router = APIRouter(
    prefix="/users",
    tags=["users"]
)


@router.get("/{user_id}", response_model=UserGet, status_code=status.HTTP_200_OK, summary="Получить пользователя по ID")
async def get_user(
    user_id: int,
    session: AsyncSession = Depends(get_async_session)
) -> UserGet:
    """Получить пользователя по ID."""
    
    try:
        user = await UserService.get_user_by_id(session, user_id)
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь с таким ID не найден."
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при получении пользователя: {str(e)}"
        )
        
        
@router.post("/", response_model=UserGet, status_code=status.HTTP_201_CREATED, summary="Создать нового пользователя")
async def create_user(
    user_data: UserCreate,
    session: AsyncSession = Depends(get_async_session),
    current_user: UserGet = Depends(get_current_user)
) -> UserGet:
    """Создать нового пользователя."""
    
    try:
        new_user = await UserService.create_user(session, user_data.name, user_data.email, current_user)
        return new_user
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Невалидные данные пользователя: {str(e)}"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при создании пользователя: {str(e)}"
        )
        
        
@router.put("/{user_id}", response_model=UserGet, status_code=status.HTTP_200_OK, summary="Обновить данные пользователя")
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    session: AsyncSession = Depends(get_async_session)
) -> UserGet:
    """Обновить данные пользователя."""
    
    try:
        updated_user = await UserService.update_user(session, user_id, user_data.name, user_data.email)
        return updated_user
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Невалидные данные для обновления пользователя: {str(e)}"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при обновлении пользователя: {str(e)}"
        )
        
        
@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Удалить пользователя")
async def delete_user(
    user_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """Удалить пользователя."""
    
    try:
        await UserService.delete_user(session, user_id)
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Пользователь с таким ID не найден: {str(e)}"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при удалении пользователя: {str(e)}"
        )
