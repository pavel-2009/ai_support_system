"""Minimal tests for app/core/dependencies.py"""
import pytest
from fastapi import HTTPException
from unittest.mock import AsyncMock, patch


class TestGetCurrentUser:
    """Tests for get_current_user dependency."""

    @pytest.mark.asyncio
    async def test_get_current_user_success(self):
        """Test getting current user with valid token."""
        from app.core.dependencies import get_current_user
        from app.core.security import create_access_token
        
        user_data = {"user_id": 1, "email": "test@example.com", "role": "user"}
        token = create_access_token(user_data)
        
        mock_session = AsyncMock()
        mock_user = AsyncMock()
        mock_user.id = 1
        mock_user.email = "test@example.com"
        
        with patch("app.services.user_service.UserService.get_user_by_id", return_value=mock_user):
            result = await get_current_user(token=token, session=mock_session)
            assert result.id == 1
            assert result.email == "test@example.com"

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self):
        """Test getting current user with invalid token."""
        from app.core.dependencies import get_current_user
        
        mock_session = AsyncMock()
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token="invalid.token", session=mock_session)
        
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_user_user_not_found(self):
        """Test getting current user when user doesn't exist."""
        from app.core.dependencies import get_current_user
        from app.core.security import create_access_token
        
        user_data = {"user_id": 99999, "email": "notfound@example.com", "role": "user"}
        token = create_access_token(user_data)
        
        mock_session = AsyncMock()
        
        with patch("app.services.user_service.UserService.get_user_by_id", side_effect=ValueError("Not found")):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(token=token, session=mock_session)
            
            assert exc_info.value.status_code == 401

    def test_oauth2_scheme_exists(self):
        """Test OAuth2 scheme is configured."""
        from app.core.dependencies import oauth2_scheme
        assert oauth2_scheme is not None
