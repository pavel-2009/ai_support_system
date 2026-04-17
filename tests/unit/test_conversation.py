"""Базовые тесты для conversation репозитория, сервиса и роутера."""

import pytest
from sqlalchemy import select

from app.models.conversation import AuditLog, Channel, ConversationOperatorLink, Priority, Status
from app.models.user import UserRole


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
        assert assigned.status == Status.WAITING_FOR_OPERATOR

        links = (
            await async_session.execute(
                select(ConversationOperatorLink).where(
                    ConversationOperatorLink.conversation_id == conv.id
                )
            )
        ).scalars().all()
        assert len(links) == 1
        assert links[0].operator_id == operator.id
        assert links[0].is_active is True

        closed = await repo.close_conversation(conv.id)
        assert closed is not None
        assert closed.status == Status.CLOSED

        logs = (
            await async_session.execute(select(AuditLog).where(AuditLog.conversation_id == conv.id))
        ).scalars().all()
        actions = {log.action for log in logs}
        assert "conversation_created" in actions
        assert "operator_assigned" in actions
        assert "conversation_closed" in actions

    @pytest.mark.asyncio
    async def test_repo_active_queue_sorted_by_priority(self, async_session):
        from app.models.user import User
        from app.repositories.conversation_repo import ConversationRepository

        user = User(
            email="conv_queue_user@test.com",
            nickname="conv_queue_user",
            fullname="Conv Queue User",
            hashed_password="hash",
        )
        async_session.add(user)
        await async_session.commit()
        await async_session.refresh(user)

        repo = ConversationRepository(async_session)
        low = await repo.create_conversation(user.id, Priority.LOW, Channel.WEB)
        medium = await repo.create_conversation(user.id, Priority.MEDIUM, Channel.API)
        high = await repo.create_conversation(user.id, Priority.HIGH, Channel.EMAIL)
        await repo.update_conversation_status(low.id, Status.CLOSED)

        queue = await repo.get_active_queue()
        assert [conv.id for conv in queue] == [high.id, medium.id]


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

    @pytest.mark.asyncio
    async def test_service_get_active_queue(self, async_session):
        from app.models.user import User
        from app.services.conversation_service import ConversationService

        user = User(
            email="svc_queue_user@test.com",
            nickname="svc_queue_user",
            fullname="Svc Queue User",
            hashed_password="hash",
        )
        async_session.add(user)
        await async_session.commit()
        await async_session.refresh(user)

        service = ConversationService(async_session)
        low = await service.create_conversation(user.id, Priority.LOW, Channel.API)
        high = await service.create_conversation(user.id, Priority.HIGH, Channel.API)
        await service.update_conversation_status(low.id, Status.CLOSED)

        queue = await service.get_active_queue()
        queue_ids = [conversation.id for conversation in queue]
        assert high.id in queue_ids
        assert low.id not in queue_ids


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

    def test_active_queue_for_operator_sorted_by_priority(self, client, create_test_user):
        create_test_user(
            email="queue_owner@example.com",
            password="TestPass123!",
            nickname="queueowner",
        )
        create_test_user(
            email="queue_operator@example.com",
            password="OperatorPass123!",
            nickname="queueoperator",
            role=UserRole.OPERATOR,
        )

        owner_login = client.post(
            "/api/auth/login",
            json={"email": "queue_owner@example.com", "password": "TestPass123!"},
        )
        owner_headers = {"Authorization": f"Bearer {owner_login.json()['access_token']}"}

        conv_low = client.post(
            "/api/conversations/",
            headers=owner_headers,
            json={"priority": "low", "channel": "api"},
        ).json()
        conv_high = client.post(
            "/api/conversations/",
            headers=owner_headers,
            json={"priority": "high", "channel": "api"},
        ).json()

        operator_login = client.post(
            "/api/auth/login",
            json={"email": "queue_operator@example.com", "password": "OperatorPass123!"},
        )
        operator_headers = {"Authorization": f"Bearer {operator_login.json()['access_token']}"}

        queue_response = client.get("/api/conversations/queue/active", headers=operator_headers)
        assert queue_response.status_code == 200
        ids = [item["id"] for item in queue_response.json()]
        assert conv_high["id"] in ids
        assert conv_low["id"] in ids
        assert ids.index(conv_high["id"]) < ids.index(conv_low["id"])

    def test_active_queue_forbidden_for_regular_user(self, authenticated_client):
        queue_response = authenticated_client.get("/api/conversations/queue/active")
        assert queue_response.status_code == 403
