import asyncio

from app.services.user_service import UserService


class DummySession:
    pass


def test_get_user_by_id_delegates_to_repository(monkeypatch) -> None:
    async def fake_get_user_by_id(session, user_id):
        return {"id": user_id, "email": "user@example.com"}

    monkeypatch.setattr("app.repositories.user_repo.UserRepository.get_user_by_id", fake_get_user_by_id)

    result = asyncio.run(UserService.get_user_by_id(DummySession(), 11))

    assert result["id"] == 11


def test_create_user_delegates_to_admin_create(monkeypatch) -> None:
    async def fake_create_user_by_admin(session, name, email, current_user=None):
        return {"id": 1, "name": name, "email": email, "role": current_user.role}

    monkeypatch.setattr("app.repositories.user_repo.UserRepository.create_user_by_admin", fake_create_user_by_admin)

    current_user = type("U", (), {"role": "admin"})()
    result = asyncio.run(UserService.create_user(DummySession(), "Nick", "n@example.com", current_user))

    assert result["email"] == "n@example.com"
    assert result["role"] == "admin"


def test_update_user_delegates_to_repository(monkeypatch) -> None:
    called = {}

    async def fake_update_user(session, user_id, name=None, email=None, current_user=None):
        called.update({"user_id": user_id, "name": name, "email": email, "current_user": current_user})

    monkeypatch.setattr("app.repositories.user_repo.UserRepository.update_user", fake_update_user)

    asyncio.run(UserService.update_user(DummySession(), 5, name="Name", email="e@example.com"))

    assert called["user_id"] == 5
    assert called["name"] == "Name"


def test_authenticate_user_returns_tokens(monkeypatch) -> None:
    async def fake_create_tokens_for_user(session, email):
        return {"access_token": "a", "refresh_token": "r", "token_type": "bearer", "expires_in": 1800}

    monkeypatch.setattr("app.repositories.user_repo.UserRepository.create_tokens_for_user", fake_create_tokens_for_user)

    result = asyncio.run(UserService.authenticate_user(DummySession(), "mail@example.com"))

    assert result["token_type"] == "bearer"
