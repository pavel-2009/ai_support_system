import asyncio
import sys
import types
from types import SimpleNamespace

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.security import create_tokens, verify_access_token
from app.db import Base
from app.models.user import User, UserRole

# Подменяем app.schemas.user, чтобы импортировать repository без внешней зависимости email-validator.
fake_schemas_user = types.ModuleType("app.schemas.user")


class FakeUserCreate:
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


def test_e2e_user_update_role_and_token_flow(tmp_path) -> None:
    db_path = tmp_path / "e2e_auth.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def scenario():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with SessionLocal() as session:
            user = User(
                nickname="flow_user",
                fullname="Flow User",
                email="flow@example.com",
                hashed_password="hashed",
                role=UserRole.USER,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            user_id = user.id
            role_value = user.role.value

            admin = SimpleNamespace(id=1, role="admin")
            with pytest.raises(Exception):
                await UserRepository.update_user(
                    session,
                    user_id,
                    FakeUserUpdate(nickname="flow_user_v2"),
                    current_user=admin,
                )

            tokens = create_tokens({"user_id": user_id, "role": role_value})
            decoded = verify_access_token(tokens.access_token)
            assert decoded["user_id"] == user_id
            assert decoded["role"] == "user"

        await engine.dispose()

    asyncio.run(scenario())


def test_e2e_repository_token_helper_currently_errors_on_non_dict_payload(tmp_path) -> None:
    db_path = tmp_path / "e2e_auth_error.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def scenario():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with SessionLocal() as session:
            user = User(
                nickname="broken_token",
                fullname="Broken Token",
                email="broken@example.com",
                hashed_password="hashed",
                role=UserRole.USER,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

            with pytest.raises(Exception):
                await UserRepository.create_tokens_for_user(session, user.id)

        await engine.dispose()

    asyncio.run(scenario())
