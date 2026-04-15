"""Репозиторий для работы с пользователями (только доступ к данным)."""

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


class UserRepository:
    """Низкоуровневые операции с таблицей users."""

    @staticmethod
    async def get_by_id(session: AsyncSession, user_id: int) -> User | None:
        result = await session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_email(session: AsyncSession, email: str) -> User | None:
        result = await session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    @staticmethod
    async def list_all(session: AsyncSession) -> list[User]:
        result = await session.execute(select(User).order_by(User.id.asc()))
        return list(result.scalars().all())

    @staticmethod
    async def create(session: AsyncSession, data: UserCreate, hashed_password: str) -> User:
        user = User(
            email=data.email,
            nickname=data.nickname,
            fullname=data.full_name or data.nickname,
            hashed_password=hashed_password,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user

    @staticmethod
    async def update(session: AsyncSession, user: User, data: UserUpdate) -> User:
        payload = data.model_dump(exclude_unset=True)
        if "full_name" in payload:
            payload["fullname"] = payload.pop("full_name")

        for key, value in payload.items():
            setattr(user, key, value)

        await session.commit()
        await session.refresh(user)
        return user

    @staticmethod
    async def delete(session: AsyncSession, user: User) -> None:
        await session.execute(delete(User).where(User.id == user.id))
        await session.commit()

    @staticmethod
    async def exists(
        session: AsyncSession,
        *,
        email: str | None = None,
        user_id: int | None = None,
    ) -> bool:
        query = select(User.id)
        if email is not None:
            query = query.where(User.email == email)
        if user_id is not None:
            query = query.where(User.id == user_id)

        result = await session.execute(query)
        return result.scalar_one_or_none() is not None

    # Backward-compatible aliases for existing tests/callers.
    user_exists = exists

    @staticmethod
    async def get_user_by_email(session: AsyncSession, email: str) -> User:
        if not await UserRepository.user_exists(session, email=email):
            raise ValueError("Пользователь с таким email не найден.")
        return await UserRepository.get_by_email(session, email)

    @staticmethod
    async def get_user_by_id(session: AsyncSession, user_id: int) -> User:
        user = await UserRepository.get_by_id(session, user_id)
        if user is None:
            raise ValueError("Пользователь с таким ID не найден.")
        return user

    get_all_users = list_all
