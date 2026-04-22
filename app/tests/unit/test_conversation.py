"""Базовые тесты для conversation репозитория, сервиса и роутера."""

import pytest
from sqlalchemy import select
import asyncio

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
        
        # Обновляем статусы диалогов для их добавления в активную очередь
        await repo.update_conversation_status(low.id, Status.ESCALATED)
        await repo.update_conversation_status(medium.id, Status.ESCALATED)
        await repo.update_conversation_status(high.id, Status.ESCALATED)
        
        # Закрываем один диалог - он не должен появиться в очереди
        await repo.update_conversation_status(low.id, Status.CLOSED)

        queue = await repo.get_active_queue()
        assert [conv.id for conv in queue] == [high.id, medium.id]


class TestConversationRouter:
    def test_create_get_close_and_410(self, client, create_test_user):
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

        closed = client.post(f"/api/conversations/{conversation_id}/close", headers=headers)
        assert closed.status_code == 200
        assert closed.json()["status"] == "closed"

        loaded_after_close = client.get(f"/api/conversations/{conversation_id}", headers=headers)
        assert loaded_after_close.status_code == 410

    def test_get_conversations_filters_and_pagination(self, client, create_test_user):
        create_test_user(email="conv_list_owner@example.com", password="TestPass123!", nickname="convlistowner")

        login_response = client.post(
            "/api/auth/login",
            json={"email": "conv_list_owner@example.com", "password": "TestPass123!"},
        )
        headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

        client.post("/api/conversations/", headers=headers, json={"priority": "high", "channel": "api"})
        client.post("/api/conversations/", headers=headers, json={"priority": "low", "channel": "web"})

        response = client.get("/api/conversations/?page=1&size=1&priority=high", headers=headers)
        assert response.status_code == 200
        payload = response.json()
        assert payload["page"] == 1
        assert payload["size"] == 1
        assert payload["total"] >= 1
        assert len(payload["items"]) == 1
        assert payload["items"][0]["priority"] == "high"

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

    def test_active_queue_forbidden_for_regular_user(self, authenticated_client):
        queue_response = authenticated_client.get("/api/conversations/queue/active")
        assert queue_response.status_code == 403

    def test_active_queue_for_admin(self, admin_client, create_test_user, client, async_session):
        from app.models.user import User
        from app.repositories.conversation_repo import ConversationRepository
        from sqlalchemy import select

        create_test_user(email="queue_owner@example.com", password="TestPass123!", nickname="queueowner")

        owner_login = client.post(
            "/api/auth/login",
            json={"email": "queue_owner@example.com", "password": "TestPass123!"},
        )
        owner_headers = {"Authorization": f"Bearer {owner_login.json()['access_token']}"}

        client.post(
            "/api/conversations/",
            headers=owner_headers,
            json={"priority": "low", "channel": "api"},
        )
        client.post(
            "/api/conversations/",
            headers=owner_headers,
            json={"priority": "high", "channel": "api"},
        )
        
        # Получаем user_id по email
        async def get_and_update():
            result = await async_session.execute(
                select(User).where(User.email == "queue_owner@example.com")
            )
            owner_user = result.scalar_one()
            
            repo = ConversationRepository(async_session)
            convs = await repo.list_conversations(user_id_filter=owner_user.id, limit=10, offset=0)
            for conv in convs:
                await repo.update_conversation_status(conv.id, Status.ESCALATED)
        
        asyncio.run(get_and_update())

        queue_response = admin_client.get("/api/conversations/queue/active")
        assert queue_response.status_code == 200
        assert len(queue_response.json()) >= 2


    @pytest.mark.asyncio
    async def test_repo_assign_operator_respects_max_load(self, async_session):
        from app.models.user import User
        from app.repositories.conversation_repo import ConversationRepository

        user = User(email="owner_max@test.com", nickname="owner_max", fullname="Owner Max", hashed_password="hash")
        overloaded_operator = User(
            email="op_max@test.com",
            nickname="op_max",
            fullname="Op Max",
            hashed_password="hash",
            role=UserRole.OPERATOR,
            active_conversations_count=5,
        )
        async_session.add_all([user, overloaded_operator])
        await async_session.commit()
        await async_session.refresh(user)

        repo = ConversationRepository(async_session)
        conv = await repo.create_conversation(user.id, Priority.HIGH, Channel.API)
        await repo.update_conversation_status(conv.id, Status.ESCALATED)

        assigned = await repo.assign_operator(conv.id, overloaded_operator.id)
        assert assigned is None

    @pytest.mark.asyncio
    async def test_close_conversation_decrements_operator_load(self, async_session):
        from app.models.user import User
        from app.repositories.conversation_repo import ConversationRepository

        user = User(email="owner_dec@test.com", nickname="owner_dec", fullname="Owner Dec", hashed_password="hash")
        operator = User(
            email="op_dec@test.com",
            nickname="op_dec",
            fullname="Op Dec",
            hashed_password="hash",
            role=UserRole.OPERATOR,
        )
        async_session.add_all([user, operator])
        await async_session.commit()
        await async_session.refresh(user)
        await async_session.refresh(operator)

        repo = ConversationRepository(async_session)
        conv = await repo.create_conversation(user.id, Priority.HIGH, Channel.API)
        await repo.update_conversation_status(conv.id, Status.ESCALATED)
        await repo.assign_operator(conv.id, operator.id)
        await async_session.refresh(operator)
        assert operator.active_conversations_count == 1

        await repo.close_conversation(conv.id)
        await async_session.refresh(operator)
        assert operator.active_conversations_count == 0
