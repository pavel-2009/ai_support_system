"""Репозиторий для работы с пользователями (только доступ к данным)."""

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


class UserRepository:
    """Низкоуровневые операции с таблицей users."""
    
    def __init__(self, session: AsyncSession):
        self.session = session


    async def get_by_id(self, user_id: int) -> User | None:
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()


    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()


    async def list_all(self) -> list[User]:
        result = await self.session.execute(select(User).order_by(User.id.asc()))
        return list(result.scalars().all())


    async def create(self, data: UserCreate, hashed_password: str) -> User:
        user = User(
            email=data.email,
            nickname=data.nickname,
            fullname=data.full_name or data.nickname,
            hashed_password=hashed_password,
        )
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user


    async def update(self, user: User, data: UserUpdate) -> User:
        payload = data.model_dump(exclude_unset=True)
        if "full_name" in payload:
            payload["fullname"] = payload.pop("full_name")

        for key, value in payload.items():
            setattr(user, key, value)

        await self.session.commit()
        await self.session.refresh(user)
        return user


    async def delete(self, user: User) -> None:
        await self.session.execute(delete(User).where(User.id == user.id))
        await self.session.commit()


    async def exists(
        self,
        email: str | None = None,
        user_id: int | None = None,
    ) -> bool:
        query = select(User.id)
        if email is not None:
            query = query.where(User.email == email)
        if user_id is not None:
            query = query.where(User.id == user_id)

        result = await self.session.execute(query)
        return result.scalar_one_or_none() is not None

    # Удобные методы для проверки существования и получения пользователя
    user_exists = exists


    async def get_user_by_email(self, email: str) -> User:
        if not await self.user_exists(email=email):
            raise ValueError("Пользователь с таким email не найден.")
        return await self.get_by_email(email)


    async def get_user_by_id(self, user_id: int) -> User:
        user = await self.get_by_id(user_id)
        if user is None:
            raise ValueError("Пользователь с таким ID не найден.")
        return user

    get_all_users = list_all
