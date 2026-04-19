"""Тесты для схем, репозитория, сервиса и роутера сообщений."""

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.models.conversation import Channel, Priority
from app.schemas.message import MessageCreate, MessageGet


class TestMessageSchemas:
    def test_message_create_requires_content(self):
        payload = MessageCreate(content="Привет")
        assert payload.content == "Привет"

        with pytest.raises(ValueError):
            MessageCreate(content="")

    def test_message_get_from_attributes(self):
        source = SimpleNamespace(
            id=7,
            conversation_id=2,
            sender_type="user",
            sender_id=11,
            content="Тест",
            is_auto_reply=False,
            confidence=None,
            needs_review=False,
            created_at=datetime.utcnow(),
        )

        result = MessageGet.model_validate(source)
        assert result.id == 7
        assert result.conversation_id == 2


class TestMessageRepository:
    @pytest.mark.asyncio
    async def test_create_and_get_messages_by_conversation(self, async_session):
        from app.models.user import User
        from app.repositories.conversation_repo import ConversationRepository
        from app.repositories.message_repo import MessageRepository

        owner = User(
            email=f"msg_repo_owner_{uuid4().hex[:8]}@example.com",
            nickname=f"msg_repo_owner_{uuid4().hex[:8]}",
            fullname="Msg Repo Owner",
            hashed_password="hash",
        )
        async_session.add(owner)
        await async_session.commit()
        await async_session.refresh(owner)

        conversation = await ConversationRepository(async_session).create_conversation(
            user_id=owner.id,
            priority=Priority.MEDIUM,
            channel=Channel.WEB,
        )

        repo = MessageRepository(async_session)
        created = await repo.create_message(
            conversation_id=conversation.id,
            sender_type="user",
            sender_id=owner.id,
            content="Первое сообщение",
        )

        assert created.id is not None
        assert created.created_at is not None

        items = await repo.get_messages_by_conversation(conversation.id)
        assert len(items) == 1
        assert items[0].content == "Первое сообщение"

        empty_items = await repo.get_messages_by_conversation(999999)
        assert empty_items == []


class TestMessageService:
    @pytest.mark.asyncio
    async def test_service_delegates_to_repository_with_flags(self):
        from app.services.message_service import MessageService

        service = MessageService(AsyncMock())

        created_obj = SimpleNamespace(id=1, content="Ответ")
        with patch.object(service.message_repo, "create_message", AsyncMock(return_value=created_obj)) as create_mock:
            result = await service.create_message(
                conversation_id=3,
                sender_type="agent",
                sender_id=77,
                content="Ответ",
                is_auto_reply=True,
                confidence=0.87,
                needs_review=True,
            )

        assert result.id == 1
        create_mock.assert_awaited_once_with(
            conversation_id=3,
            sender_type="agent",
            sender_id=77,
            content="Ответ",
            is_auto_reply=True,
            confidence=0.87,
            needs_review=True,
        )


class TestMessageRouter:
    def test_send_and_get_messages_success(self, client, create_test_user):
        email = f"msg_owner_{uuid4().hex[:8]}@example.com"
        create_test_user(email=email, password="TestPass123!", nickname=f"msg_owner_{uuid4().hex[:8]}")

        login = client.post("/api/auth/login", json={"email": email, "password": "TestPass123!"})
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        conversation = client.post(
            "/api/conversations/",
            headers=headers,
            json={"priority": "low", "channel": "web"},
        )
        conversation_id = conversation.json()["id"]

        sent = client.post(
            f"/api/conversations/{conversation_id}/messages",
            headers=headers,
            json={"content": "Новый вопрос"},
        )
        assert sent.status_code == 201
        assert sent.json()["content"] == "Новый вопрос"

        listed = client.get(f"/api/conversations/{conversation_id}/messages", headers=headers)
        assert listed.status_code == 200
        assert len(listed.json()) == 1
        assert listed.json()[0]["sender_id"] > 0


    def test_get_messages_closed_conversation_returns_410(self, client, create_test_user):
        owner_email = f"msg_closed_owner_{uuid4().hex[:8]}@example.com"
        create_test_user(email=owner_email, password="TestPass123!", nickname=f"msg_closed_owner_{uuid4().hex[:8]}")

        owner_login = client.post("/api/auth/login", json={"email": owner_email, "password": "TestPass123!"})
        headers = {"Authorization": f"Bearer {owner_login.json()['access_token']}"}

        created = client.post(
            "/api/conversations/",
            headers=headers,
            json={"priority": "medium", "channel": "api"},
        )
        conversation_id = created.json()["id"]

        client.post(f"/api/conversations/{conversation_id}/close", headers=headers)

        listed = client.get(f"/api/conversations/{conversation_id}/messages", headers=headers)
        assert listed.status_code == 410

    def test_send_message_edge_cases_404_and_403(self, client, create_test_user):
        owner_email = f"msg_owner_{uuid4().hex[:8]}@example.com"
        outsider_email = f"msg_outsider_{uuid4().hex[:8]}@example.com"

        create_test_user(email=owner_email, password="TestPass123!", nickname=f"msg_owner_{uuid4().hex[:8]}")
        create_test_user(email=outsider_email, password="TestPass123!", nickname=f"msg_outsider_{uuid4().hex[:8]}")

        owner_login = client.post("/api/auth/login", json={"email": owner_email, "password": "TestPass123!"})
        owner_headers = {"Authorization": f"Bearer {owner_login.json()['access_token']}"}

        outsider_login = client.post(
            "/api/auth/login",
            json={"email": outsider_email, "password": "TestPass123!"},
        )
        outsider_headers = {"Authorization": f"Bearer {outsider_login.json()['access_token']}"}

        missing = client.post(
            "/api/conversations/999999/messages",
            headers=owner_headers,
            json={"content": "test"},
        )
        assert missing.status_code == 404

        conversation = client.post(
            "/api/conversations/",
            headers=owner_headers,
            json={"priority": "medium", "channel": "api"},
        )
        conversation_id = conversation.json()["id"]

        forbidden = client.post(
            f"/api/conversations/{conversation_id}/messages",
            headers=outsider_headers,
            json={"content": "чужое"},
        )
        assert forbidden.status_code == 403
