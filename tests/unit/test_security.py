from datetime import timedelta

from app.core.security import (
    create_access_token,
    create_refresh_token,
    create_tokens,
    hash_password,
    update_access_token_with_refresh_token,
    verify_access_token,
    verify_password,
    verify_refresh_token,
)


def test_password_hash_and_verify_roundtrip() -> None:
    password = "StrongPass123!"
    hashed = hash_password(password)

    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("wrong-password", hashed) is False


def test_access_token_create_and_verify() -> None:
    payload = {"user_id": 42}
    token = create_access_token(payload, expires_delta=timedelta(minutes=5))

    decoded = verify_access_token(token)

    assert decoded is not None
    assert decoded["user_id"] == 42


def test_refresh_token_create_and_verify() -> None:
    payload = {"user_id": 7}
    token = create_refresh_token(payload)

    decoded = verify_refresh_token(token)

    assert decoded is not None
    assert decoded["user_id"] == 7


def test_create_tokens_returns_expected_shape() -> None:
    tokens = create_tokens({"user_id": 100})

    assert tokens.token_type == "bearer"
    assert isinstance(tokens.access_token, str)
    assert isinstance(tokens.refresh_token, str)
    assert tokens.expires_in > 0


def test_update_access_token_with_refresh_token_success() -> None:
    refresh = create_refresh_token({"user_id": 99})

    new_access = update_access_token_with_refresh_token(refresh)

    assert new_access is not None
    assert verify_access_token(new_access)["user_id"] == 99


def test_update_access_token_with_refresh_token_invalid_token() -> None:
    assert update_access_token_with_refresh_token("not-a-token") is None
