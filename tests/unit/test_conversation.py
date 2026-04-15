"""Базовые тесты для conversation репозитория, сервиса и роутера."""

import pytest

from app.models.conversation import Channel, Priority, Status


class TestConversationRepository:
    @pytest.mark.asyncio
    async def test_repo_create_get_update_assign_close(self, async_session):
        from app.models.user import User
        from app.repositories.conversation_repo import ConversationRepository

        user = User(
            email="conv_repo_user@test.com",
            nickname="conv_repo_user",
            fullname="Conv Repo User",
            hashed_password="hash",
        )
        operator = User(
            email="conv_repo_operator@test.com",
            nickname="conv_repo_operator",
            fullname="Conv Repo Operator",
            hashed_password="hash",
        )
        async_session.add_all([user, operator])
        await async_session.commit()
        await async_session.refresh(user)
        await async_session.refresh(operator)

        repo = ConversationRepository(async_session)
        conv = await repo.create_conversation(user.id, Priority.HIGH, Channel.API)
        assert conv.id is not None
        assert conv.status == Status.OPEN

        fetched = await repo.get_conversation_by_id(conv.id)
        assert fetched is not None
        assert fetched.user_id == user.id

        updated = await repo.update_conversation_status(conv.id, Status.ESCALATED)
        assert updated is not None
        assert updated.status == Status.ESCALATED

        assigned = await repo.assign_operator(conv.id, operator.id)
        assert assigned is not None
        assert assigned.operator_id == operator.id

        closed = await repo.close_conversation(conv.id)
        assert closed is not None
        assert closed.status == Status.CLOSED


class TestConversationService:
    @pytest.mark.asyncio
    async def test_service_create_and_get(self, async_session):
        from app.models.user import User
        from app.services.conversation_service import ConversationService

        user = User(
            email="conv_service_user@test.com",
            nickname="conv_service_user",
            fullname="Conv Service User",
            hashed_password="hash",
        )
        async_session.add(user)
        await async_session.commit()
        await async_session.refresh(user)

        service = ConversationService(async_session)
        created = await service.create_conversation(user.id, Priority.LOW, Channel.WEB)
        assert created.user_id == user.id

        loaded = await service.get_conversation_by_id(created.id)
        assert loaded is not None
        assert loaded.id == created.id


class TestConversationRouter:
    def test_create_and_get_conversation(self, client, create_test_user):
        create_test_user(email="conv_api_owner@example.com", password="TestPass123!", nickname="convowner")

        login_response = client.post(
            "/api/auth/login",
            json={"email": "conv_api_owner@example.com", "password": "TestPass123!"},
        )
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        created = client.post(
            "/api/conversations/",
            headers=headers,
            json={"priority": "high", "channel": "api"},
        )
        assert created.status_code == 201
        conversation_id = created.json()["id"]

        loaded = client.get(f"/api/conversations/{conversation_id}", headers=headers)
        assert loaded.status_code == 200
        assert loaded.json()["id"] == conversation_id

    def test_forbidden_access_to_foreign_conversation(self, client, create_test_user):
        create_test_user(email="conv_owner@example.com", password="TestPass123!", nickname="convowner2")
        create_test_user(email="conv_other@example.com", password="TestPass123!", nickname="convother")

        owner_login = client.post(
            "/api/auth/login",
            json={"email": "conv_owner@example.com", "password": "TestPass123!"},
        )
        owner_headers = {"Authorization": f"Bearer {owner_login.json()['access_token']}"}

        created = client.post(
            "/api/conversations/",
            headers=owner_headers,
            json={"priority": "medium", "channel": "web"},
        )
        conversation_id = created.json()["id"]

        other_login = client.post(
            "/api/auth/login",
            json={"email": "conv_other@example.com", "password": "TestPass123!"},
        )
        other_headers = {"Authorization": f"Bearer {other_login.json()['access_token']}"}

        forbidden = client.get(f"/api/conversations/{conversation_id}", headers=other_headers)
        assert forbidden.status_code == 403
