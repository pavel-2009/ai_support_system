"""Tests for token service behavior with an in-memory Redis mock."""
import pytest


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


class TestTokenService:
    def test_issue_pair_creates_session(self, mock_redis):
        from app.services.token_service import TokenService

        service = TokenService(mock_redis)
        access_token, refresh_token = service.issue_pair({"user_id": 1})

        assert access_token
        assert refresh_token
        sessions = service.list_user_sessions(1)
        assert len(sessions) == 1
        assert sessions[0]["family_id"]

    def test_rotate_replaces_refresh_token(self, mock_redis):
        from app.services.token_service import RefreshTokenReused, TokenService

        service = TokenService(mock_redis)
        _, old_refresh = service.issue_pair({"user_id": 1})
        _, new_refresh = service.rotate(old_refresh)

        assert new_refresh != old_refresh
        assert len(service.list_user_sessions(1)) == 1
        with pytest.raises(RefreshTokenReused):
            service.rotate(old_refresh)

    def test_revoke_all_for_user_removes_sessions(self, mock_redis):
        from app.services.token_service import TokenService

        service = TokenService(mock_redis)
        service.issue_pair({"user_id": 1})
        service.issue_pair({"user_id": 1})

        assert service.revoke_all_for_user(1) == 2
        assert service.list_user_sessions(1) == []
