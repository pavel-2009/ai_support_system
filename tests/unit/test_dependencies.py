"""Minimal tests for app/core/dependencies.py"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException


class TestGetCurrentUser:
    @pytest.mark.asyncio
    async def test_get_current_user_success(self):
        from app.core.dependencies import get_current_user
        from app.core.security import create_access_token

        token = create_access_token({"user_id": 1, "email": "test@example.com", "role": "user"})
        mock_session = AsyncMock()
        mock_user = AsyncMock()
        mock_user.id = 1

        with patch("app.services.user_service.UserService.get_user_by_id", AsyncMock(return_value=mock_user)):
            result = await get_current_user(token=token, session=mock_session)
            assert result.id == 1

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self):
        from app.core.dependencies import get_current_user

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token="invalid.token", session=AsyncMock())
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_user_user_not_found(self):
        from app.core.dependencies import get_current_user
        from app.core.security import create_access_token

        token = create_access_token({"user_id": 99999, "email": "notfound@example.com", "role": "user"})

        with patch("app.services.user_service.UserService.get_user_by_id", AsyncMock(side_effect=ValueError("Not found"))):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(token=token, session=AsyncMock())
            assert exc_info.value.status_code == 401

    def test_oauth2_scheme_exists(self):
        from app.core.dependencies import oauth2_scheme

        assert oauth2_scheme is not None
