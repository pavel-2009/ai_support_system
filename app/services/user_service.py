"""Сервисный слой пользователей: бизнес-правила и orchestration."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_tokens, hash_password, verify_password
from app.models.user import User, UserRole
from app.repositories.user_repo import UserRepository
from app.schemas.token import Token
from app.schemas.user import UserCreate, UserLogin, UserUpdate


class UserService:
    """Бизнес-логика пользователей."""

    @staticmethod
    async def get_user_by_id(session: AsyncSession, user_id: int) -> User:
        user = await UserRepository.get_by_id(session, user_id)
        if not user:
            raise ValueError("Пользователь с таким ID не найден.")
        return user

    @staticmethod
    async def get_user_by_email(session: AsyncSession, email: str) -> User:
        user = await UserRepository.get_by_email(session, email)
        if not user:
            raise ValueError("Пользователь с таким email не найден.")
        return user

    @staticmethod
    async def get_all_users(session: AsyncSession) -> list[User]:
        return await UserRepository.list_all(session)

    @staticmethod
    async def register_user(session: AsyncSession, data: UserCreate) -> User:
        if await UserRepository.exists(session, email=data.email):
            raise ValueError("Пользователь с таким email уже существует.")

        hashed_password = hash_password(data.password)
        return await UserRepository.create(session, data, hashed_password)

    @staticmethod
    async def create_user_by_admin(
        session: AsyncSession,
        data: UserCreate,
        current_user: User,
    ) -> User:
        if current_user.role != UserRole.ADMIN:
            raise ValueError("Только администратор может создавать новых пользователей.")

        return await UserService.register_user(session, data)

    @staticmethod
    async def update_user(
        session: AsyncSession,
        user_id: int,
        data: UserUpdate,
        current_user: User,
    ) -> User:
        user = await UserService.get_user_by_id(session, user_id)

        if current_user.role != UserRole.ADMIN and current_user.id != user.id:
            raise ValueError("Пользователь может обновлять только свои данные.")

        return await UserRepository.update(session, user, data)

    @staticmethod
    async def delete_user(session: AsyncSession, user_id: int, current_user: User) -> None:
        if current_user.role != UserRole.ADMIN:
            raise ValueError("Только администратор может удалять пользователей.")

        user = await UserService.get_user_by_id(session, user_id)
        await UserRepository.delete(session, user)

    @staticmethod
    async def login_user(session: AsyncSession, data: UserLogin) -> Token:
        user = await UserRepository.get_by_email(session, data.email)
        if not user or not verify_password(data.password, user.hashed_password):
            raise ValueError("Неверные учетные данные.")

        return create_tokens({"user_id": user.id, "email": user.email, "role": user.role.value})

    @staticmethod
    async def refresh_token(current_user: User) -> Token:
        return create_tokens(
            {"user_id": current_user.id, "email": current_user.email, "role": current_user.role.value}
        )
