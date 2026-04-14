"""Minimal tests for app/repositories/user_repo.py"""
import pytest
from uuid import uuid4
from app.models.user import UserRole
from app.schemas.user import UserCreate, UserUpdate
from app.core.security import hash_password


def unique_email(prefix: str) -> str:
    """Generate unique email for tests."""
    return f"{prefix}_{uuid4().hex[:8]}@test.com"


def unique_nick(prefix: str) -> str:
    """Generate unique nickname for tests."""
    return f"{prefix}_{uuid4().hex[:8]}"


class TestUserRepository:
    """Basic tests for UserRepository."""

    @pytest.mark.asyncio
    async def test_get_by_id_returns_user(self, async_session):
        """Test getting user by ID."""
        from app.repositories.user_repo import UserRepository
        from app.models.user import User
        
        # Create user directly
        user = User(
            email=unique_email("test1"),
            nickname=unique_nick("test1"),
            fullname="Test User 1",
            hashed_password=hash_password("Pass123!")
        )
        async_session.add(user)
        await async_session.commit()
        await async_session.refresh(user)
        
        result = await UserRepository.get_by_id(async_session, user.id)
        assert result is not None
        assert result.id == user.id
        assert result.email == user.email

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, async_session):
        """Test getting non-existent user returns None."""
        from app.repositories.user_repo import UserRepository
        result = await UserRepository.get_by_id(async_session, 99999)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_email_returns_user(self, async_session):
        """Test getting user by email."""
        from app.repositories.user_repo import UserRepository
        from app.models.user import User
        
        email = unique_email("test2")
        user = User(
            email=email,
            nickname=unique_nick("test2"),
            fullname="Test User 2",
            hashed_password=hash_password("Pass123!")
        )
        async_session.add(user)
        await async_session.commit()
        
        result = await UserRepository.get_by_email(async_session, email)
        assert result is not None
        assert result.email == email

    @pytest.mark.asyncio
    async def test_get_by_email_not_found(self, async_session):
        """Test getting non-existent email returns None."""
        from app.repositories.user_repo import UserRepository
        result = await UserRepository.get_by_email(async_session, unique_email("nonexistent"))
        assert result is None

    @pytest.mark.asyncio
    async def test_list_all_returns_list(self, async_session):
        """Test listing all users."""
        from app.repositories.user_repo import UserRepository
        from app.models.user import User
        
        user1 = User(
            email=unique_email("user1"),
            nickname=unique_nick("user1"),
            fullname="User 1",
            hashed_password=hash_password("Pass123!")
        )
        user2 = User(
            email=unique_email("user2"),
            nickname=unique_nick("user2"),
            fullname="User 2",
            hashed_password=hash_password("Pass123!")
        )
        async_session.add(user1)
        async_session.add(user2)
        await async_session.commit()
        
        result = await UserRepository.list_all(async_session)
        assert isinstance(result, list)
        assert len(result) >= 2

    @pytest.mark.asyncio
    async def test_create_user(self, async_session):
        """Test creating a new user."""
        from app.repositories.user_repo import UserRepository
        
        data = UserCreate(
            email=unique_email("newuser"),
            nickname=unique_nick("newuser"),
            full_name="New User",
            password="Pass123!"
        )
        hashed_pw = hash_password(data.password)
        user = await UserRepository.create(async_session, data, hashed_pw)
        assert user.id is not None
        assert user.email == data.email
        assert user.nickname == data.nickname

    @pytest.mark.asyncio
    async def test_update_user(self, async_session):
        """Test updating user data."""
        from app.repositories.user_repo import UserRepository
        from app.models.user import User
        
        user = User(
            email=unique_email("update_test"),
            nickname=unique_nick("oldnick"),
            fullname="Update Test",
            hashed_password=hash_password("Pass123!")
        )
        async_session.add(user)
        await async_session.commit()
        await async_session.refresh(user)
        
        update_data = UserUpdate(nickname=unique_nick("updated_nick"))
        updated = await UserRepository.update(async_session, user, update_data)
        assert updated.nickname == update_data.nickname

    @pytest.mark.asyncio
    async def test_delete_user(self, async_session):
        """Test deleting a user."""
        from app.repositories.user_repo import UserRepository
        from app.models.user import User
        
        user = User(
            email=unique_email("delete_test"),
            nickname=unique_nick("deluser"),
            fullname="Delete Test",
            hashed_password=hash_password("Pass123!")
        )
        async_session.add(user)
        await async_session.commit()
        await async_session.refresh(user)
        user_id = user.id
        
        await UserRepository.delete(async_session, user)
        result = await UserRepository.get_by_id(async_session, user_id)
        assert result is None

    @pytest.mark.asyncio
    async def test_exists_with_email_found(self, async_session):
        """Test checking if user exists by email."""
        from app.repositories.user_repo import UserRepository
        from app.models.user import User
        
        email = unique_email("exists_test")
        user = User(
            email=email,
            nickname=unique_nick("existuser"),
            fullname="Exists Test",
            hashed_password=hash_password("Pass123!")
        )
        async_session.add(user)
        await async_session.commit()
        
        result = await UserRepository.exists(async_session, email=email)
        assert result is True

    @pytest.mark.asyncio
    async def test_exists_with_email_not_found(self, async_session):
        """Test checking if non-existent email exists."""
        from app.repositories.user_repo import UserRepository
        result = await UserRepository.exists(async_session, email=unique_email("notexists"))
        assert result is False

    @pytest.mark.asyncio
    async def test_exists_with_user_id_found(self, async_session):
        """Test checking if user exists by ID."""
        from app.repositories.user_repo import UserRepository
        from app.models.user import User
        
        user = User(
            email=unique_email("exists_id_test"),
            nickname=unique_nick("existiduser"),
            fullname="Exists ID Test",
            hashed_password=hash_password("Pass123!")
        )
        async_session.add(user)
        await async_session.commit()
        await async_session.refresh(user)
        
        result = await UserRepository.exists(async_session, user_id=user.id)
        assert result is True

    @pytest.mark.asyncio
    async def test_exists_with_user_id_not_found(self, async_session):
        """Test checking if non-existent user ID exists."""
        from app.repositories.user_repo import UserRepository
        result = await UserRepository.exists(async_session, user_id=99999)
        assert result is False
