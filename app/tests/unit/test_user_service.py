"""Базовые unit-тесты для сервисов пользователей."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestUserService:
    @pytest.mark.asyncio
    async def test_get_user_by_id_success(self):
        from app.services.user_service import UserService

        service = UserService(AsyncMock())
        mock_user = MagicMock(id=1, email="test@example.com")
        with patch.object(service.user_repo, "get_by_id", AsyncMock(return_value=mock_user)):
            result = await service.get_user_by_id(1)
            assert result.id == 1

    @pytest.mark.asyncio
    async def test_get_user_by_id_not_found(self):
        from app.services.user_service import UserService

        service = UserService(AsyncMock())
        with patch.object(service.user_repo, "get_by_id", AsyncMock(return_value=None)):
            with pytest.raises(ValueError):
                await service.get_user_by_id(999)

    @pytest.mark.asyncio
    async def test_register_login_refresh_and_delete_flows(self):
        from app.models.user import UserRole
        from app.schemas.user import UserCreate, UserLogin
        from app.services.user_service import UserService

        service = UserService(AsyncMock())
        admin = MagicMock(role=UserRole.ADMIN)

        user_data = UserCreate(
            email="newuser@example.com",
            password="Pass123!",
            nickname="newuser",
            full_name="New User",
        )
        created_user = MagicMock(id=1, email=user_data.email, role=UserRole.USER, hashed_password="hash")

        with patch.object(service.user_repo, "exists", AsyncMock(return_value=False)), patch.object(
            service.user_repo, "create", AsyncMock(return_value=created_user)
        ), patch("app.services.user_service.hash_password", return_value="hashed"):
            created = await service.register_user(user_data)
            assert created.id == 1

        with patch.object(service.user_repo, "exists", AsyncMock(return_value=True)):
            with pytest.raises(ValueError):
                await service.register_user(user_data)

        with patch.object(service.user_repo, "get_by_email", AsyncMock(return_value=created_user)), patch(
            "app.services.user_service.verify_password", return_value=True
        ), patch("app.services.user_service.create_tokens", return_value=MagicMock()):
            assert await service.login_user(UserLogin(email=user_data.email, password="Pass123!")) is not None

        with patch("app.services.user_service.create_tokens", return_value=MagicMock()):
            assert await service.refresh_token(created_user) is not None

        with patch.object(service, "get_user_by_id", AsyncMock(return_value=created_user)), patch.object(
            service.user_repo, "delete", AsyncMock(return_value=None)
        ):
            await service.delete_user(1, admin)
