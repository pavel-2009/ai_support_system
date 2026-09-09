"""Сервисный слой пользователей: бизнес-правила и orchestration."""

from app.core.security import create_tokens, hash_password, verify_password
from app.core.uow import UnitOfWork
from app.domain.events import UserDeleted, UserRegistered, UserUpdated
from app.models.user import User, UserRole
from app.schemas.token import Token
from app.schemas.user import UserCreate, UserLogin, UserUpdate


class UserService:
    """Бизнес-логика пользователей."""

    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    def _add_event(self, event) -> None:
        """Queue an event when the UoW supports domain events.

        Lightweight service tests may use a minimal UoW stub without event support;
        the real UnitOfWork always provides ``add_event``.
        """
        add_event = getattr(self.uow, "add_event", None)
        if add_event is not None:
            add_event(event)

    async def get_user_by_id(self, user_id: int) -> User:
        user = await self.uow.users.get_by_id(user_id)
        if not user:
            raise ValueError("Пользователь с таким ID не найден.")
        return user

    async def get_user_by_email(self, email: str) -> User:
        user = await self.uow.users.get_by_email(email)
        if not user:
            raise ValueError("Пользователь с таким email не найден.")
        return user

    async def get_all_users(self) -> list[User]:
        return await self.uow.users.list_all()

    async def register_user(self, data: UserCreate) -> User:
        if await self.uow.users.exists(email=data.email):
            raise ValueError("Пользователь с таким email уже существует.")

        hashed_password = hash_password(data.password)
        user = await self.uow.users.create(data, hashed_password)
        self._add_event(UserRegistered(str(user.id)))
        return user

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

        updated_user = await self.uow.users.update(user, data)
        self._add_event(UserUpdated(str(updated_user.id)))
        return updated_user

    async def delete_user(self, user_id: int, current_user: User) -> None:
        if current_user.role != UserRole.ADMIN:
            raise ValueError("Только администратор может удалять пользователей.")

        user = await self.get_user_by_id(user_id)
        await self.uow.users.delete(user)
        self._add_event(UserDeleted(str(user.id)))

    async def login_user(self, data: UserLogin) -> Token:
        user = await self.uow.users.get_by_email(data.email)
        if not user or not verify_password(data.password, user.hashed_password):
            raise ValueError("Неверные учетные данные.")

        return create_tokens({"user_id": user.id, "email": user.email, "role": user.role.value})

    async def refresh_token(self, current_user: User) -> Token:
        return create_tokens(
            {"user_id": current_user.id, "email": current_user.email, "role": current_user.role.value}
        )
