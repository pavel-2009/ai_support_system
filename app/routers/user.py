"""Роутер для работы с пользователями."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.user_service import UserService
from app.db import get_async_session
from app.schemas.user import UserGet, UserCreate, UserUpdate
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.user import UserLogin


router = APIRouter(
    prefix="/users",
    tags=["users"]
)


@router.get("/", response_model=list[UserGet], status_code=status.HTTP_200_OK, summary="Получить всех пользователей")
async def get_all_users(
    session: AsyncSession = Depends(get_async_session)
) -> list[UserGet]:
    """Получить всех пользователей."""
    
    try:
        users = await UserService.get_all_users(session)
        return users
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при получении пользователей: {str(e)}"
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
        
        
@router.post("/auth/login", summary="Аутентифицировать пользователя и получить токен доступа")
async def login_user(
    login_data: UserLogin,
    session: AsyncSession = Depends(get_async_session)
):
    """Аутентифицировать пользователя и получить токен доступа."""
    
    try:
        token = await UserService.login_user(session, login_data.email, login_data.password)
        return {"access_token": token.access_token, "token_type": "bearer"}
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Неверные учетные данные пользователя: {str(e)}"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при аутентификации пользователя: {str(e)}"
        )
        
        
@router.post("/auth/refresh", summary="Обновить токен доступа")
async def refresh_token(
    session: AsyncSession = Depends(get_async_session),
    current_user: UserGet = Depends(get_current_user)
):
    """Обновить токен доступа."""
    
    try:
        new_token = await UserService.refresh_token(session, current_user.id)
        return {"access_token": new_token.access_token, "token_type": "bearer"}
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Невозможно обновить токен доступа: {str(e)}"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при обновлении токена доступа: {str(e)}"
        )
        

@router.post("/auth/register", response_model=UserGet, status_code=status.HTTP_201_CREATED, summary="Зарегистрировать нового пользователя")
async def register(
    user_data: UserCreate,
    session: AsyncSession = Depends(get_async_session)
) -> UserGet:
    """Зарегистрировать нового пользователя."""
    
    try:
        new_user = await UserService.register_user(session, user_data.name, user_data.email, user_data.password)
        return new_user
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Невалидные данные для регистрации пользователя: {str(e)}"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при регистрации пользователя: {str(e)}"
)
