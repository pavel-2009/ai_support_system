"""Расширенные тесты для сервисов и роутеров для увеличения покрытия."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.models.conversation import Channel, Priority, Status
from app.models.user import UserRole
from app.schemas.user import UserCreate, UserLogin, UserUpdate


class TestUserServiceExtended:
    @pytest.mark.asyncio
    async def test_get_user_by_email_success_and_not_found(self):
        from app.services.user_service import UserService

        service = UserService(AsyncMock())
        mock_user = MagicMock(id=10, email="user10@example.com")

        with patch.object(service.user_repo, "get_by_email", AsyncMock(return_value=mock_user)):
            result = await service.get_user_by_email("user10@example.com")
            assert result.id == 10

        with patch.object(service.user_repo, "get_by_email", AsyncMock(return_value=None)):
            with pytest.raises(ValueError):
                await service.get_user_by_email("missing@example.com")

    @pytest.mark.asyncio
    async def test_get_all_users_and_admin_create_user(self):
        from app.services.user_service import UserService

        service = UserService(AsyncMock())
        users = [MagicMock(id=1), MagicMock(id=2)]
        admin = MagicMock(role=UserRole.ADMIN)
        non_admin = MagicMock(role=UserRole.USER)
        data = UserCreate(email="created@example.com", password="Pass123!", nickname="created")

        with patch.object(service.user_repo, "list_all", AsyncMock(return_value=users)):
            listed = await service.get_all_users()
            assert len(listed) == 2

        with patch.object(service, "register_user", AsyncMock(return_value=MagicMock(id=99))):
            created = await service.create_user_by_admin(data, admin)
            assert created.id == 99

        with pytest.raises(ValueError):
            await service.create_user_by_admin(data, non_admin)

    @pytest.mark.asyncio
    async def test_update_user_permissions_and_delete_non_admin(self):
        from app.services.user_service import UserService

        service = UserService(AsyncMock())
        target_user = MagicMock(id=10)
        admin = MagicMock(id=1, role=UserRole.ADMIN)
        foreign_user = MagicMock(id=2, role=UserRole.USER)

        with patch.object(service, "get_user_by_id", AsyncMock(return_value=target_user)), patch.object(
            service.user_repo, "update", AsyncMock(return_value=MagicMock(id=10, nickname="newnick"))
        ):
            updated = await service.update_user(10, UserUpdate(nickname="newnick"), admin)
            assert updated.nickname == "newnick"

        with patch.object(service, "get_user_by_id", AsyncMock(return_value=target_user)):
            with pytest.raises(ValueError):
                await service.update_user(10, UserUpdate(nickname="forbidden"), foreign_user)

        with pytest.raises(ValueError):
            await service.delete_user(10, foreign_user)

    @pytest.mark.asyncio
    async def test_login_user_invalid_credentials(self):
        from app.services.user_service import UserService

        service = UserService(AsyncMock())
        data = UserLogin(email="missing@example.com", password="Pass123!")

        with patch.object(service.user_repo, "get_by_email", AsyncMock(return_value=None)):
            with pytest.raises(ValueError):
                await service.login_user(data)

        user = MagicMock(hashed_password="hash")
        with patch.object(service.user_repo, "get_by_email", AsyncMock(return_value=user)), patch(
            "app.services.user_service.verify_password", return_value=False
        ):
            with pytest.raises(ValueError):
                await service.login_user(data)


class TestConversationServiceExtended:
    @pytest.mark.asyncio
    async def test_service_update_assign_close_methods(self, async_session):
        from app.models.user import User
        from app.services.conversation_service import ConversationService

        owner = User(
            email=f"svc_owner_{uuid4().hex[:8]}@example.com",
            nickname=f"svc_owner_{uuid4().hex[:8]}",
            fullname="Svc Owner",
            hashed_password="hash",
        )
        operator = User(
            email=f"svc_operator_{uuid4().hex[:8]}@example.com",
            nickname=f"svc_operator_{uuid4().hex[:8]}",
            fullname="Svc Operator",
            hashed_password="hash",
            role=UserRole.OPERATOR,
        )
        async_session.add_all([owner, operator])
        await async_session.commit()
        await async_session.refresh(owner)
        await async_session.refresh(operator)

        service = ConversationService(async_session)
        conv = await service.create_conversation(owner.id, Priority.MEDIUM, Channel.WEB)

        escalated = await service.update_conversation_status(conv.id, Status.ESCALATED)
        assert escalated is not None
        assert escalated.status == Status.ESCALATED

        assigned = await service.assign_operator(conv.id, operator.id)
        assert assigned is not None
        assert assigned.operator_id == operator.id

        closed = await service.close(conv.id)
        assert closed is not None
        assert closed.status == Status.CLOSED


class TestRouterExtended:
    def test_conversation_not_found_returns_404(self, client, authenticated_client):
        response = authenticated_client.get("/api/conversations/999999")
        assert response.status_code == 404
        assert response.json()["detail"] == "Диалог не найден."

    def test_admin_can_read_foreign_conversation(self, client, create_test_user):
        owner_email = f"owner_{uuid4().hex[:8]}@example.com"
        create_test_user(email=owner_email, password="TestPass123!", nickname=f"owner_{uuid4().hex[:8]}")

        owner_login = client.post("/api/auth/login", json={"email": owner_email, "password": "TestPass123!"})
        owner_headers = {"Authorization": f"Bearer {owner_login.json()['access_token']}"}

        created = client.post(
            "/api/conversations/",
            headers=owner_headers,
            json={"priority": "low", "channel": "web"},
        )
        conversation_id = created.json()["id"]

        admin_email = f"admin_{uuid4().hex[:8]}@example.com"
        create_test_user(
            email=admin_email,
            password="AdminPass123!",
            nickname=f"admin_{uuid4().hex[:8]}",
            role=UserRole.ADMIN,
        )
        admin_login = client.post("/api/auth/login", json={"email": admin_email, "password": "AdminPass123!"})
        admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}

        loaded = client.get(f"/api/conversations/{conversation_id}", headers=admin_headers)
        assert loaded.status_code == 200
        assert loaded.json()["id"] == conversation_id

    def test_user_router_error_paths(self, client, create_test_user):
        user_email = f"user_{uuid4().hex[:8]}@example.com"
        create_test_user(email=user_email, password="TestPass123!", nickname=f"user_{uuid4().hex[:8]}")
        login = client.post("/api/auth/login", json={"email": user_email, "password": "TestPass123!"})
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        # Не админ не может получить список пользователей
        get_all = client.get("/api/users/", headers=headers)
        assert get_all.status_code == 403

        # Нельзя читать чужого пользователя по ID
        create_test_user(email=f"other_{uuid4().hex[:8]}@example.com", nickname=f"other_{uuid4().hex[:8]}")
        foreign = client.get("/api/users/999999", headers=headers)
        assert foreign.status_code in (403, 404)

        # Ошибка логина конвертируется в 401
        bad_login = client.post("/api/auth/login", json={"email": user_email, "password": "WrongPass123!"})
        assert bad_login.status_code == 401

        # Некорректный refresh-token конвертируется в 401
        bad_refresh = client.post("/api/auth/refresh", json={"refresh_token": "invalid.refresh.token"})
        assert bad_refresh.status_code == 401


    def test_admin_user_router_success_paths(self, admin_client):
        users = admin_client.get("/api/users/")
        assert users.status_code == 200

        created = admin_client.post(
            "/api/users/",
            json={
                "email": f"created_{uuid4().hex[:8]}@example.com",
                "password": "Pass123!",
                "nickname": f"created_{uuid4().hex[:8]}",
            },
        )
        assert created.status_code == 201

        user_id = created.json()["id"]
        by_id = admin_client.get(f"/api/users/{user_id}")
        assert by_id.status_code == 200

        patched = admin_client.patch(f"/api/users/{user_id}", json={"nickname": f"patched_{uuid4().hex[:8]}"})
        assert patched.status_code == 200

        deleted = admin_client.delete(f"/api/users/{user_id}")
        assert deleted.status_code == 204
