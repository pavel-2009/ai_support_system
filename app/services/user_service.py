"""Сервис для работы с пользователями."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.user_repo import UserRepository
from app.schemas.token import Token


class UserService:
    """Сервис для работы с пользователями."""

    @staticmethod
    async def get_user_by_id(
        session: AsyncSession,
        user_id: int
    ) -> User:
        """Получить пользователя по ID."""
        
        return await UserRepository.get_user_by_id(session, user_id)
    
    
    @staticmethod
    async def register(
        session: AsyncSession,
        name: str,
        email: str,
        password: str
    ) -> User:
        """Зарегистрировать нового пользователя."""
        
        return await UserRepository.register_user(session, name, email, password)


    @staticmethod
    async def create_user(
        session: AsyncSession,
        name: str,
        email: str,
        current_user: User | None = None
    ) -> User:
        """Создать нового пользователя."""
        
        return await UserRepository.create_user_by_admin(session, name, email, current_user)


    @staticmethod
    async def update_user(
        session: AsyncSession,
        user_id: int,
        name: str = None,
        email: str = None,
        current_user: User | None = None
    ):
        """Обновить данные пользователя."""
        
        await UserRepository.update_user(session, user_id, name, email, current_user)


    @staticmethod
    async def delete_user(
        session: AsyncSession,
        user_id: int
    ):
        """Удалить пользователя."""
        
        await UserRepository.delete_user(session, user_id)
        
        
    @staticmethod
    async def authenticate_user(
        session: AsyncSession,
        email: str
    ) -> dict:
        """Аутентифицировать пользователя и вернуть токен."""
        
        return await UserRepository.create_tokens_for_user(session, email)
    
    
    @staticmethod
    async def get_all_users(
        session: AsyncSession,
    ) -> list[User]:
        """Получить список всех пользователей с пагинацией."""
        
        return await UserRepository.get_all_users(session)
    
    
    @staticmethod
    async def login_user(
        session: AsyncSession,
        email: str
    ) -> Token:
        """Аутентифицировать пользователя и вернуть токен."""
        
        return await UserRepository.create_tokens_for_user(session, email)
    