"""Тесты роутеров пользователей (бизнес-ветки и ошибки)."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException


@pytest.mark.asyncio
async def test_get_all_users_forbidden_for_non_admin():
    from app.routers.user import get_all_users

    session = AsyncMock()
    current_user = SimpleNamespace(role=SimpleNamespace(value="user"))

    with pytest.raises(HTTPException) as exc:
        await get_all_users(session=session, current_user=current_user)

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_get_all_users_returns_list_for_admin(monkeypatch):
    from app.routers.user import get_all_users

    session = AsyncMock()
    current_user = SimpleNamespace(role=SimpleNamespace(value="admin"))
    expected = [SimpleNamespace(id=1), SimpleNamespace(id=2)]

    service_mock = AsyncMock(return_value=expected)
    monkeypatch.setattr("app.routers.user.UserService.get_all_users", service_mock)

    result = await get_all_users(session=session, current_user=current_user)

    assert result == expected
    service_mock.assert_awaited_once_with(session)


@pytest.mark.asyncio
async def test_get_user_by_id_returns_404_when_service_raises(monkeypatch):
    from app.routers.user import get_user_by_id

    session = AsyncMock()
    current_user = SimpleNamespace(id=1, role=SimpleNamespace(value="admin"))

    service_mock = AsyncMock(side_effect=ValueError("not found"))
    monkeypatch.setattr("app.routers.user.UserService.get_user_by_id", service_mock)

    with pytest.raises(HTTPException) as exc:
        await get_user_by_id(user_id=999, session=session, current_user=current_user)

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_refresh_token_rejects_invalid_refresh(monkeypatch):
    from app.routers.user import RefreshTokenRequest, refresh_token

    monkeypatch.setattr("app.routers.user.verify_refresh_token", lambda token: None)

    with pytest.raises(HTTPException) as exc:
        await refresh_token(RefreshTokenRequest(refresh_token="broken"))

    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token_returns_new_tokens(monkeypatch):
    from app.routers.user import RefreshTokenRequest, refresh_token

    token_pair = {"access_token": "a", "refresh_token": "r", "token_type": "bearer", "expires_in": 900}

    monkeypatch.setattr(
        "app.routers.user.verify_refresh_token",
        lambda _: {"user_id": 1, "email": "u@test.com", "role": "user", "exp": 111},
    )
    monkeypatch.setattr("app.routers.user.create_tokens", lambda user_data: token_pair)

    result = await refresh_token(RefreshTokenRequest(refresh_token="ok"))

    assert result == token_pair
