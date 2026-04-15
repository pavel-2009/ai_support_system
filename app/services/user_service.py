"""Сервисный слой пользователей: бизнес-правила и orchestration."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_tokens, hash_password, verify_password
from app.models.user import User, UserRole
from app.repositories.user_repo import UserRepository
from app.schemas.token import Token
from app.schemas.user import UserCreate, UserLogin, UserUpdate


class UserService:
    """Бизнес-логика пользователей."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)


    async def get_user_by_id(self, user_id: int) -> User:
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise ValueError("Пользователь с таким ID не найден.")
        return user


    async def get_user_by_email(self, email: str) -> User:
        user = await self.user_repo.get_by_email(email)
        if not user:
            raise ValueError("Пользователь с таким email не найден.")
        return user


    async def get_all_users(self) -> list[User]:
        return await self.user_repo.list_all()


    async def register_user(self, data: UserCreate) -> User:
        if await self.user_repo.exists(email=data.email):
            raise ValueError("Пользователь с таким email уже существует.")

        hashed_password = hash_password(data.password)
        return await self.user_repo.create(data, hashed_password)


    async def create_user_by_admin(
        self,
        data: UserCreate,
        current_user: User,
    ) -> User:
        if current_user.role != UserRole.ADMIN:
            raise ValueError("Только администратор может создавать новых пользователей.")

        return await self.register_user(data)


    async def update_user(
        self,
        user_id: int,
        data: UserUpdate,
        current_user: User,
    ) -> User:
        user = await self.get_user_by_id(user_id)

        if current_user.role != UserRole.ADMIN and current_user.id != user.id:
            raise ValueError("Пользователь может обновлять только свои данные.")

        return await self.user_repo.update(user, data)


    async def delete_user(self, user_id: int, current_user: User) -> None:
        if current_user.role != UserRole.ADMIN:
            raise ValueError("Только администратор может удалять пользователей.")

        user = await self.get_user_by_id(user_id)
        await self.user_repo.delete(user)


    async def login_user(self, data: UserLogin) -> Token:
        user = await self.user_repo.get_by_email(data.email)
        if not user or not verify_password(data.password, user.hashed_password):
            raise ValueError("Неверные учетные данные.")

        return create_tokens({"user_id": user.id, "email": user.email, "role": user.role.value})


    async def refresh_token(self, current_user: User) -> Token:
        return create_tokens(
            {"user_id": current_user.id, "email": current_user.email, "role": current_user.role.value}
        )
