"""Minimal tests for app/core/security.py"""
import pytest
from datetime import timedelta


class TestPasswordHashing:
    """Tests for password hashing functions."""

    def test_hash_password_returns_string(self):
        """Test hash_password returns a string."""
        from app.core.security import hash_password
        hashed = hash_password("password123")
        assert isinstance(hashed, str)
        assert len(hashed) > 0

    def test_hash_password_different_each_time(self):
        """Test hash_password produces different hashes."""
        from app.core.security import hash_password
        hash1 = hash_password("password123")
        hash2 = hash_password("password123")
        assert hash1 != hash2

    def test_verify_password_success(self):
        """Test verify_password returns True for correct password."""
        from app.core.security import hash_password, verify_password
        password = "TestPass123!"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_verify_password_failure(self):
        """Test verify_password returns False for wrong password."""
        from app.core.security import hash_password, verify_password
        hashed = hash_password("TestPass123!")
        assert verify_password("WrongPass123!", hashed) is False


class TestAccessToken:
    """Tests for access token operations."""

    def test_create_access_token_returns_string(self):
        """Test create_access_token returns a token string."""
        from app.core.security import create_access_token
        token = create_access_token({"user_id": 1})
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_has_exp(self):
        """Test access token has expiration claim."""
        from app.core.security import create_access_token, verify_access_token
        token = create_access_token({"user_id": 1})
        payload = verify_access_token(token)
        assert payload is not None
        assert "exp" in payload

    def test_verify_access_token_returns_payload(self):
        """Test verify_access_token returns token payload."""
        from app.core.security import create_access_token, verify_access_token
        data = {"user_id": 42, "email": "test@example.com"}
        token = create_access_token(data)
        payload = verify_access_token(token)
        assert payload is not None
        assert payload.get("user_id") == 42
        assert payload.get("email") == "test@example.com"

    def test_verify_invalid_token_returns_none(self):
        """Test verify_access_token returns None for invalid token."""
        from app.core.security import verify_access_token
        result = verify_access_token("invalid.token.here")
        assert result is None


class TestRefreshToken:
    """Tests for refresh token operations."""

    def test_create_refresh_token_returns_string(self):
        """Test create_refresh_token returns a token string."""
        from app.core.security import create_refresh_token
        token = create_refresh_token({"user_id": 1})
        assert isinstance(token, str)
        assert len(token) > 0

    def test_verify_refresh_token_returns_payload(self):
        """Test verify_refresh_token returns token payload."""
        from app.core.security import create_refresh_token, verify_refresh_token
        data = {"user_id": 42}
        token = create_refresh_token(data)
        payload = verify_refresh_token(token)
        assert payload is not None
        assert payload.get("user_id") == 42

    def test_verify_invalid_refresh_token_returns_none(self):
        """Test verify_refresh_token returns None for invalid token."""
        from app.core.security import verify_refresh_token
        result = verify_refresh_token("invalid.token.here")
        assert result is None


class TestTokenPair:
    """Tests for token pair creation."""

    def test_create_tokens_returns_token_object(self):
        """Test create_tokens returns Token object."""
        from app.core.security import create_tokens
        tokens = create_tokens({"user_id": 1})
        assert tokens is not None
        assert hasattr(tokens, "access_token")
        assert hasattr(tokens, "refresh_token")
        assert hasattr(tokens, "token_type")
        assert tokens.token_type == "bearer"

    def test_create_tokens_has_both_tokens(self):
        """Test create_tokens creates both access and refresh tokens."""
        from app.core.security import create_tokens
        tokens = create_tokens({"user_id": 1})
        assert isinstance(tokens.access_token, str)
        assert isinstance(tokens.refresh_token, str)
        assert len(tokens.access_token) > 0
        assert len(tokens.refresh_token) > 0

    def test_update_access_token_with_refresh_token_success(self):
        """Test updating access token with refresh token."""
        from app.core.security import create_tokens, update_access_token_with_refresh_token
        original_tokens = create_tokens({"user_id": 1, "email": "test@example.com"})
        new_access_token = update_access_token_with_refresh_token(original_tokens.refresh_token)
        assert new_access_token is not None
        assert isinstance(new_access_token, str)
        assert len(new_access_token) > 0

    def test_update_access_token_with_invalid_refresh_returns_none(self):
        """Test updating with invalid refresh token returns None."""
        from app.core.security import update_access_token_with_refresh_token
        result = update_access_token_with_refresh_token("invalid.token")
        assert result is None
