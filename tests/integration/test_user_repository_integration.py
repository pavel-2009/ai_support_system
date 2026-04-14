import asyncio
import sys
import types
from types import SimpleNamespace

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models.user import User, UserRole

# Подменяем app.schemas.user, чтобы не тянуть email-validator в тестовом окружении.
fake_schemas_user = types.ModuleType("app.schemas.user")


class FakeUserCreate:  # pragma: no cover - контейнер для импорта
    pass


class FakeUserUpdate:
    def __init__(self, nickname=None, full_name=None):
        self.nickname = nickname
        self.full_name = full_name

    def model_dump(self, exclude_unset=True):
        result = {}
        if self.nickname is not None:
            result["nickname"] = self.nickname
        if self.full_name is not None:
            result["full_name"] = self.full_name
        return result


fake_schemas_user.UserCreate = FakeUserCreate
fake_schemas_user.UserUpdate = FakeUserUpdate
sys.modules["app.schemas.user"] = fake_schemas_user

from app.repositories.user_repo import UserRepository  # noqa: E402


@pytest.fixture()
def sqlite_session_factory(tmp_path):
    db_path = tmp_path / "integration_users.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def _init():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_init())

    try:
        yield SessionLocal
    finally:
        asyncio.run(engine.dispose())


def test_user_exists_get_update_delete_flow(sqlite_session_factory) -> None:
    async def scenario():
        async with sqlite_session_factory() as session:
            user = User(
                nickname="alpha",
                fullname="Alpha User",
                email="alpha@example.com",
                hashed_password="hashed",
                role=UserRole.USER,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            user_id = user.id

            assert await UserRepository.user_exists(session, user_id=user_id) is True

            fetched = await UserRepository.get_user_by_email(session, "alpha@example.com")
            assert fetched.id == user_id

            admin = SimpleNamespace(id=999, role="admin")
            with pytest.raises(Exception):
                await UserRepository.update_user(
                    session,
                    user_id,
                    FakeUserUpdate(nickname="alpha_new"),
                    current_user=admin,
                )

            db_user = (await session.execute(select(User).where(User.id == user_id))).scalar_one()
            assert db_user.nickname == "alpha"

            await UserRepository.delete_user(session, user_id)
            assert await UserRepository.user_exists(session, user_id=user_id) is False

    asyncio.run(scenario())


def test_create_tokens_for_user_raises_with_invalid_payload_type(sqlite_session_factory) -> None:
    async def scenario():
        async with sqlite_session_factory() as session:
            user = User(
                nickname="delta",
                fullname="Delta User",
                email="delta@example.com",
                hashed_password="hashed",
                role=UserRole.USER,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

            with pytest.raises(Exception):
                await UserRepository.create_tokens_for_user(session, user.id)

    asyncio.run(scenario())
