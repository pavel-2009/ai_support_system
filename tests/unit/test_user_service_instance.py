"""Тесты instance-based API UserService."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest


@pytest.mark.asyncio
async def test_create_user_by_admin_rejects_non_admin():
    from app.models.user import UserRole
    from app.services.user_service import UserService

    service = UserService(session=AsyncMock())
    non_admin = SimpleNamespace(role=UserRole.USER)

    with pytest.raises(ValueError, match="Только администратор"):
        await service.create_user_by_admin(data=SimpleNamespace(), current_user=non_admin)


@pytest.mark.asyncio
async def test_update_user_rejects_other_user_without_admin_rights(monkeypatch):
    from app.models.user import UserRole
    from app.services.user_service import UserService

    service = UserService(session=AsyncMock())
    monkeypatch.setattr(service, "get_user_by_id", AsyncMock(return_value=SimpleNamespace(id=99)))

    with pytest.raises(ValueError, match="только свои данные"):
        await service.update_user(
            user_id=99,
            data=SimpleNamespace(),
            current_user=SimpleNamespace(id=1, role=UserRole.USER),
        )


@pytest.mark.asyncio
async def test_login_user_returns_tokens(monkeypatch):
    from app.models.user import UserRole
    from app.services.user_service import UserService

    service = UserService(session=AsyncMock())
    service.user_repo.get_by_email = AsyncMock(
        return_value=SimpleNamespace(
            id=1,
            email="u@test.com",
            role=UserRole.USER,
            hashed_password="hashed",
        )
    )

    monkeypatch.setattr("app.services.user_service.verify_password", lambda raw, hashed: True)
    monkeypatch.setattr("app.services.user_service.create_tokens", lambda data: {"access": "ok", "payload": data})

    result = await service.login_user(SimpleNamespace(email="u@test.com", password="p"))

    assert result["access"] == "ok"
    assert result["payload"]["email"] == "u@test.com"


@pytest.mark.asyncio
async def test_login_user_rejects_invalid_credentials(monkeypatch):
    from app.services.user_service import UserService

    service = UserService(session=AsyncMock())
    service.user_repo.get_by_email = AsyncMock(return_value=None)
    monkeypatch.setattr("app.services.user_service.verify_password", lambda raw, hashed: False)

    with pytest.raises(ValueError, match="Неверные учетные данные"):
        await service.login_user(SimpleNamespace(email="u@test.com", password="wrong"))
