"""Minimal tests for app/repositories/user_repo.py"""

from uuid import uuid4

import pytest

from app.core.security import hash_password
from app.schemas.user import UserCreate, UserUpdate


def unique_email(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:8]}@test.com"


def unique_nick(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:8]}"


class TestUserRepository:
    @pytest.mark.asyncio
    async def test_get_by_id_returns_user(self, async_session):
        from app.models.user import User
        from app.repositories.user_repo import UserRepository

        repo = UserRepository(async_session)
        user = User(
            email=unique_email("test1"),
            nickname=unique_nick("test1"),
            fullname="Test User 1",
            hashed_password=hash_password("Pass123!"),
        )
        async_session.add(user)
        await async_session.commit()
        await async_session.refresh(user)

        result = await repo.get_by_id(user.id)
        assert result is not None
        assert result.id == user.id

    @pytest.mark.asyncio
    async def test_get_by_email_returns_user(self, async_session):
        from app.models.user import User
        from app.repositories.user_repo import UserRepository

        repo = UserRepository(async_session)
        email = unique_email("test2")
        user = User(
            email=email,
            nickname=unique_nick("test2"),
            fullname="Test User 2",
            hashed_password=hash_password("Pass123!"),
        )
        async_session.add(user)
        await async_session.commit()

        result = await repo.get_by_email(email)
        assert result is not None
        assert result.email == email

    @pytest.mark.asyncio
    async def test_list_all_create_update_delete_and_exists(self, async_session):
        from app.models.user import User
        from app.repositories.user_repo import UserRepository

        repo = UserRepository(async_session)
        data = UserCreate(
            email=unique_email("newuser"),
            nickname=unique_nick("newuser"),
            full_name="New User",
            password="Pass123!",
        )
        created = await repo.create(data, hash_password(data.password))
        assert created.id is not None

        listed = await repo.list_all()
        assert any(u.id == created.id for u in listed)

        updated = await repo.update(created, UserUpdate(nickname=unique_nick("updated")))
        assert updated.nickname.startswith("updated_")

        assert await repo.exists(email=created.email) is True
        assert await repo.exists(user_id=created.id) is True
        assert await repo.exists(email=unique_email("missing")) is False

        user_by_email = await repo.get_user_by_email(created.email)
        assert user_by_email.id == created.id

        await repo.delete(created)
        assert await repo.get_by_id(created.id) is None

        with pytest.raises(ValueError):
            await repo.get_user_by_id(99999)

        # Проверка, что уникальные ограничения не ломают другие тесты
        extra = User(
            email=unique_email("extra"),
            nickname=unique_nick("extra"),
            fullname="Extra User",
            hashed_password=hash_password("Pass123!"),
        )
        async_session.add(extra)
        await async_session.commit()
