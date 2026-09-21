"""Дополнительное покрытие message service, message router/repository и state machine."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.conversation import (
    AuditLog,
    Channel,
    ConversationOperatorLink,
    Priority,
    Status,
)
from app.models.message import Message
from app.models.user import User, UserRole
from app.repositories.conversation_repo import ConversationRepository
from app.repositories.conversation_state_machine import ConversationStateMachine
from app.repositories.message_repo import MessageRepository
from app.domain.events import MessageSent


async def _user(session, role=UserRole.USER):
    suffix = uuid4().hex[:10]
    user = User(
        email=f"coverage_{suffix}@example.com",
        nickname=f"coverage_{suffix}",
        fullname=f"Coverage {suffix}",
        hashed_password="hash",
        role=role,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def _conversation(session, owner, status=Status.OPEN, operator_id=None):
    conversation = await ConversationRepository(session).create_conversation(
        user_id=owner.id,
        priority=Priority.MEDIUM,
        channel=Channel.API,
    )
    conversation.status = status
    conversation.operator_id = operator_id
    await session.flush()
    await session.refresh(conversation)
    return conversation


class TestMessageRepositoryCoverage:
    @pytest.mark.asyncio
    async def test_create_message_rejects_missing_conversation(self, async_session):
        repo = MessageRepository(async_session)

        result = await repo.create_message(
            conversation_id=999999,
            sender_type="user",
            sender_id=1,
            content="missing",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_create_message_rejects_user_in_wrong_status(self, async_session):
        owner = await _user(async_session)
        conversation = await _conversation(async_session, owner, Status.PENDING_AI)
        repo = MessageRepository(async_session)

        result = await repo.create_message(
            conversation_id=conversation.id,
            sender_type="user",
            sender_id=owner.id,
            content="not allowed",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_create_message_rejects_ai_when_not_pending(self, async_session):
        owner = await _user(async_session)
        conversation = await _conversation(async_session, owner, Status.OPEN)
        repo = MessageRepository(async_session)

        result = await repo.create_message(
            conversation_id=conversation.id,
            sender_type="ai",
            sender_id=None,
            content="late ai reply",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_create_message_rejects_unassigned_or_wrong_operator(self, async_session):
        owner = await _user(async_session)
        operator = await _user(async_session, UserRole.OPERATOR)
        conversation = await _conversation(
            async_session,
            owner,
            Status.WAITING_FOR_OPERATOR,
            operator_id=operator.id,
        )
        repo = MessageRepository(async_session)

        wrong_operator = await _user(async_session, UserRole.OPERATOR)
        assert (
            await repo.create_message(
                conversation_id=conversation.id,
                sender_type=UserRole.OPERATOR.value,
                sender_id=wrong_operator.id,
                content="wrong",
            )
            is None
        )

        conversation.operator_id = None
        await async_session.flush()
        assert (
            await repo.create_message(
                conversation_id=conversation.id,
                sender_type=UserRole.OPERATOR.value,
                sender_id=operator.id,
                content="unassigned",
            )
            is None
        )

    @pytest.mark.asyncio
    async def test_create_message_accepts_ai_and_operator_in_valid_states(self, async_session):
        owner = await _user(async_session)
        operator = await _user(async_session, UserRole.OPERATOR)
        repo = MessageRepository(async_session)

        pending = await _conversation(async_session, owner, Status.PENDING_AI)
        ai_message = await repo.create_message(
            conversation_id=pending.id,
            sender_type="ai",
            sender_id=None,
            content="AI answer",
            is_auto_reply=True,
            confidence=0.91,
        )
        assert ai_message is not None
        assert ai_message.confidence == 0.91

        operator_conversation = await _conversation(
            async_session,
            owner,
            Status.WAITING_FOR_OPERATOR,
            operator_id=operator.id,
        )
        operator_message = await repo.create_message(
            conversation_id=operator_conversation.id,
            sender_type=UserRole.OPERATOR.value,
            sender_id=operator.id,
            content="Operator answer",
        )
        assert operator_message is not None


class TestMessageServiceCoverage:
    @pytest.mark.asyncio
    async def test_create_message_returns_none_when_repository_rejects(self):
        from app.services.message_service import MessageService

        uow = SimpleNamespace(
            message=AsyncMock(),
            state_machine=AsyncMock(),
            add_event=MagicMock(),
        )
        uow.message.create_message.return_value = None

        result = await MessageService(uow).create_message(
            1, "user", 2, "hello"
        )

        assert result is None
        uow.add_event.assert_not_called()
        uow.state_machine.user_replied.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_create_message_handles_operator_and_user_state_updates(self):
        from app.services.message_service import MessageService

        for sender_type, sender_id, state_method in [
            (UserRole.OPERATOR.value, 7, "operator_replied"),
            (UserRole.USER.value, 3, "user_replied"),
        ]:
            message = SimpleNamespace(id=10)
            uow = SimpleNamespace(
                message=AsyncMock(),
                state_machine=AsyncMock(),
                add_event=MagicMock(),
            )
            uow.message.create_message.return_value = message
            getattr(uow.state_machine, state_method).return_value = SimpleNamespace(id=1)

            result = await MessageService(uow).create_message(
                conversation_id=5,
                sender_type=sender_type,
                sender_id=sender_id,
                content="hello",
            )

            assert result is message
            getattr(uow.state_machine, state_method).assert_awaited_once()
            uow.add_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_message_rejects_when_operator_state_update_fails(self):
        from app.services.message_service import MessageService

        uow = SimpleNamespace(
            message=AsyncMock(),
            state_machine=AsyncMock(),
            add_event=MagicMock(),
        )
        uow.message.create_message.return_value = SimpleNamespace(id=11)
        uow.state_machine.operator_replied.return_value = None

        result = await MessageService(uow).create_message(
            5,
            UserRole.OPERATOR.value,
            7,
            "operator reply",
        )

        assert result is None
        uow.add_event.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_message_rejects_when_user_state_update_fails(self):
        from app.services.message_service import MessageService

        uow = SimpleNamespace(
            message=AsyncMock(),
            state_machine=AsyncMock(),
            add_event=MagicMock(),
        )
        uow.message.create_message.return_value = SimpleNamespace(id=12)
        uow.state_machine.user_replied.return_value = None

        result = await MessageService(uow).create_message(5, "user", 7, "user reply")

        assert result is None
        uow.add_event.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_message_ai_state_update_and_failure(self):
        from app.services.message_service import MessageService

        uow = SimpleNamespace(
            message=AsyncMock(),
            state_machine=AsyncMock(),
            add_event=MagicMock(),
        )
        uow.message.create_message.return_value = SimpleNamespace(id=13)
        uow.state_machine.ai_replied.return_value = SimpleNamespace(id=5)

        result = await MessageService(uow).create_message(
            5, "ai", None, "AI reply", needs_review=False
        )
        assert result.id == 13
        uow.state_machine.ai_replied.assert_awaited_once_with(5)
        assert uow.add_event.call_count == 1

        uow.add_event.reset_mock()
        uow.state_machine.ai_replied.reset_mock()
        uow.state_machine.ai_replied.return_value = None

        result = await MessageService(uow).create_message(
            5, "ai", None, "stale AI reply", needs_review=False
        )
        assert result is None
        uow.add_event.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_message_review_does_not_add_review_event_when_transition_fails(self):
        from app.services.message_service import MessageService

        uow = SimpleNamespace(
            message=AsyncMock(),
            state_machine=AsyncMock(),
            add_event=MagicMock(),
        )
        uow.message.create_message.return_value = SimpleNamespace(id=14)
        uow.state_machine.mark_for_review.return_value = None

        result = await MessageService(uow).create_message(
            5, "user", 7, "needs review", needs_review=True
        )

        assert result.id == 14
        assert uow.add_event.call_count == 1
        assert isinstance(uow.add_event.call_args.args[0], MessageSent)

    @pytest.mark.asyncio
    async def test_get_messages_by_conversation_delegates(self):
        from app.services.message_service import MessageService

        messages = [SimpleNamespace(id=1), SimpleNamespace(id=2)]
        uow = SimpleNamespace(message=AsyncMock())
        uow.message.get_messages_by_conversation.return_value = messages

        result = await MessageService(uow).get_messages_by_conversation(42)

        assert result == messages
        uow.message.get_messages_by_conversation.assert_awaited_once_with(42)


class TestConversationStateMachineCoverage:
    @pytest.mark.parametrize(
        ("current", "target", "allowed"),
        [
            (Status.OPEN, Status.PENDING_AI, True),
            (Status.OPEN, Status.WAITING_FOR_OPERATOR, False),
            (Status.CLOSED, Status.OPEN, False),
            (Status.WAITING_FOR_USER, Status.PENDING_AI, True),
        ],
    )
    def test_can_transition(self, current, target, allowed):
        assert ConversationStateMachine.can_transition(current, target) is allowed

    @pytest.mark.asyncio
    async def test_escalate_missing_and_invalid(self, async_session):
        machine = ConversationStateMachine(async_session)

        assert await machine.escalate(999999) is None

        owner = await _user(async_session)
        conversation = await _conversation(async_session, owner, Status.CLOSED)
        assert await machine.escalate(conversation.id) is None

    @pytest.mark.asyncio
    async def test_assign_operator_rejects_missing_conversation_operator_and_capacity(self, async_session, monkeypatch):
        from app.core.config import settings

        machine = ConversationStateMachine(async_session)
        assert await machine.assign_operator(999999, 1) is None

        owner = await _user(async_session)
        operator = await _user(async_session, UserRole.OPERATOR)

        owned = await _conversation(
            async_session,
            owner,
            Status.WAITING_FOR_OPERATOR,
            operator_id=operator.id,
        )
        assert await machine.assign_operator(owned.id, operator.id) is None

        escalated = await _conversation(async_session, owner, Status.ESCALATED)
        assert await machine.assign_operator(escalated.id, 999999) is None

        operator.active_conversations_count = settings.MAX_OPERATOR_ACTIVE_CONVERSATIONS
        await async_session.flush()
        assert await machine.assign_operator(escalated.id, operator.id) is None

    @pytest.mark.asyncio
    async def test_assign_operator_reassigns_active_operator_and_link(self, async_session):
        old_operator = await _user(async_session, UserRole.OPERATOR)
        new_operator = await _user(async_session, UserRole.OPERATOR)
        owner = await _user(async_session)

        old_operator.active_conversations_count = 1
        conversation = await _conversation(
            async_session,
            owner,
            Status.ESCALATED,
            operator_id=old_operator.id,
        )
        old_link = ConversationOperatorLink(
            conversation_id=conversation.id,
            operator_id=old_operator.id,
            is_active=True,
        )
        async_session.add(old_link)
        await async_session.flush()

        machine = ConversationStateMachine(async_session)
        result = await machine.assign_operator(conversation.id, new_operator.id)

        assert result is not None
        assert result.status == Status.WAITING_FOR_OPERATOR
        assert result.operator_id == new_operator.id
        assert old_operator.active_conversations_count == 0
        assert new_operator.active_conversations_count == 1
        assert old_link.is_active is False
        assert old_link.unassigned_at is not None

        audits = (
            await async_session.execute(
                select(AuditLog).where(AuditLog.conversation_id == conversation.id)
            )
        ).scalars().all()
        assert {audit.action for audit in audits} >= {
            "operator_assigned",
            "operator_unassigned",
        }

    @pytest.mark.asyncio
    async def test_operator_replied_success_and_rejects_invalid_calls(self, async_session):
        owner = await _user(async_session)
        operator = await _user(async_session, UserRole.OPERATOR)
        machine = ConversationStateMachine(async_session)

        assert await machine.operator_replied(999999, operator.id) is None

        conversation = await _conversation(
            async_session,
            owner,
            Status.WAITING_FOR_OPERATOR,
            operator_id=operator.id,
        )
        assert await machine.operator_replied(conversation.id, 999999) is None

        result = await machine.operator_replied(conversation.id, operator.id)
        assert result is not None
        assert result.status == Status.WAITING_FOR_USER

        result_again = await machine.operator_replied(conversation.id, operator.id)
        assert result_again is not None
        assert result_again.status == Status.WAITING_FOR_USER

        closed = await _conversation(async_session, owner, Status.CLOSED, operator.id)
        assert await machine.operator_replied(closed.id, operator.id) is None

    @pytest.mark.asyncio
    async def test_user_replied_all_paths(self, async_session):
        owner = await _user(async_session)
        operator = await _user(async_session, UserRole.OPERATOR)
        machine = ConversationStateMachine(async_session)

        assert await machine.user_replied(999999) is None

        open_conversation = await _conversation(async_session, owner, Status.OPEN)
        result = await machine.user_replied(open_conversation.id)
        assert result.status == Status.PENDING_AI

        waiting = await _conversation(
            async_session,
            owner,
            Status.WAITING_FOR_USER,
            operator_id=operator.id,
        )
        result = await machine.user_replied(waiting.id)
        assert result.status == Status.WAITING_FOR_OPERATOR

        invalid = await _conversation(async_session, owner, Status.WAITING_FOR_USER)
        assert await machine.user_replied(invalid.id) is None

    @pytest.mark.asyncio
    async def test_ai_replied_missing_and_success(self, async_session):
        owner = await _user(async_session)
        machine = ConversationStateMachine(async_session)

        assert await machine.ai_replied(999999) is None

        pending = await _conversation(async_session, owner, Status.PENDING_AI)
        result = await machine.ai_replied(pending.id)
        assert result is not None
        assert result.status == Status.OPEN

        closed = await _conversation(async_session, owner, Status.CLOSED)
        assert await machine.ai_replied(closed.id) is None

    @pytest.mark.asyncio
    async def test_close_releases_operator_slot(self, async_session):
        owner = await _user(async_session)
        operator = await _user(async_session, UserRole.OPERATOR)
        operator.active_conversations_count = 1
        conversation = await _conversation(
            async_session,
            owner,
            Status.WAITING_FOR_OPERATOR,
            operator.id,
        )
        await async_session.flush()

        machine = ConversationStateMachine(async_session)
        result = await machine.close(conversation.id)

        assert result is not None
        assert result.status == Status.CLOSED
        assert result.closed_at is not None
        assert operator.active_conversations_count == 0

        assert await machine.close(conversation.id) is None
        assert await machine.close(999999) is None

    @pytest.mark.asyncio
    async def test_back_to_ai_rejects_invalid_states_and_non_operator_message(self, async_session):
        owner = await _user(async_session)
        operator = await _user(async_session, UserRole.OPERATOR)
        machine = ConversationStateMachine(async_session)

        assert await machine.back_to_ai(999999) is None

        closed = await _conversation(
            async_session, owner, Status.CLOSED, operator.id
        )
        assert await machine.back_to_ai(closed.id) is None

        no_operator = await _conversation(async_session, owner, Status.WAITING_FOR_USER)
        assert await machine.back_to_ai(no_operator.id) is None

        no_message = await _conversation(
            async_session, owner, Status.WAITING_FOR_OPERATOR, operator.id
        )
        assert await machine.back_to_ai(no_message.id) is None

        wrong_message = Message(
            conversation_id=no_message.id,
            sender_type="user",
            sender_id=owner.id,
            content="user message",
        )
        async_session.add(wrong_message)
        await async_session.flush()
        assert await machine.back_to_ai(no_message.id) is None

    @pytest.mark.asyncio
    async def test_back_to_ai_success_releases_operator(self, async_session):
        owner = await _user(async_session)
        operator = await _user(async_session, UserRole.OPERATOR)
        operator.active_conversations_count = 1
        conversation = await _conversation(
            async_session,
            owner,
            Status.WAITING_FOR_USER,
            operator.id,
        )
        async_session.add(
            Message(
                conversation_id=conversation.id,
                sender_type="operator",
                sender_id=operator.id,
                content="final operator answer",
            )
        )
        await async_session.flush()

        result = await ConversationStateMachine(async_session).back_to_ai(conversation.id)

        assert result is not None
        assert result.status == Status.OPEN
        assert result.operator_id is None
        assert operator.active_conversations_count == 0

        audit = (
            await async_session.execute(
                select(AuditLog).where(
                    AuditLog.conversation_id == conversation.id,
                    AuditLog.action == "back_to_ai",
                )
            )
        ).scalar_one()
        assert audit.from_status == Status.WAITING_FOR_USER
        assert audit.to_status == Status.OPEN


class TestMessageRouterIdempotencyCoverage:
    def _install_fake_idempotency(self, monkeypatch):
        import app.routers.users.message as message_router

        class FakeIdempotency:
            store = {}

            def __init__(self, _redis):
                pass

            def get(self, key):
                return self.store.get(key)

            def reserve(self, key, fingerprint):
                if key in self.store:
                    return False
                self.store[key] = {
                    "fingerprint": fingerprint,
                    "status": "processing",
                }
                return True

            def complete(self, key, fingerprint, response):
                self.store[key] = {
                    "fingerprint": fingerprint,
                    "status": "completed",
                    "response": response,
                }

            def delete(self, key):
                self.store.pop(key, None)

        FakeIdempotency.store = {}
        monkeypatch.setattr(message_router, "IdempotencyKey", FakeIdempotency)
        return FakeIdempotency

    def _headers(self, client, email, password="TestPass123!"):
        login = client.post(
            "/api/auth/login",
            json={"email": email, "password": password},
        )
        return {"Authorization": f"Bearer {login.json()['access_token']}"}

    def test_same_idempotency_key_returns_cached_response(
        self, client, create_test_user, monkeypatch
    ):
        self._install_fake_idempotency(monkeypatch)
        email = f"idempotent_{uuid4().hex[:8]}@example.com"
        create_test_user(email=email, nickname=f"idempotent_{uuid4().hex[:8]}")
        headers = self._headers(client, email)

        conversation = client.post(
            "/api/conversations/",
            headers=headers,
            json={"priority": "low", "channel": "web"},
        )
        conversation_id = conversation.json()["id"]

        first = client.post(
            f"/api/conversations/{conversation_id}/messages",
            headers={**headers, "Idempotency-Key": "same-key"},
            json={"content": "одинаковый запрос"},
        )
        second = client.post(
            f"/api/conversations/{conversation_id}/messages",
            headers={**headers, "Idempotency-Key": "same-key"},
            json={"content": "одинаковый запрос"},
        )

        assert first.status_code == 201
        assert second.status_code == 201
        assert second.json()["id"] == first.json()["id"]

    def test_reusing_idempotency_key_with_different_message_returns_409(
        self, client, create_test_user, monkeypatch
    ):
        self._install_fake_idempotency(monkeypatch)
        email = f"idempotent_conflict_{uuid4().hex[:8]}@example.com"
        create_test_user(email=email, nickname=f"idempotent_conflict_{uuid4().hex[:8]}")
        headers = self._headers(client, email)

        conversation = client.post(
            "/api/conversations/",
            headers=headers,
            json={"priority": "medium", "channel": "api"},
        )
        conversation_id = conversation.json()["id"]

        first = client.post(
            f"/api/conversations/{conversation_id}/messages",
            headers={**headers, "Idempotency-Key": "conflict-key"},
            json={"content": "первый"},
        )
        second = client.post(
            f"/api/conversations/{conversation_id}/messages",
            headers={**headers, "Idempotency-Key": "conflict-key"},
            json={"content": "другой"},
        )

        assert first.status_code == 201
        assert second.status_code == 409
        assert "уже использован" in second.json()["detail"]

    def test_processing_idempotency_key_returns_409(
        self, client, create_test_user, monkeypatch
    ):
        fake = self._install_fake_idempotency(monkeypatch)
        email = f"idempotent_processing_{uuid4().hex[:8]}@example.com"
        create_test_user(email=email, nickname=f"idempotent_processing_{uuid4().hex[:8]}")
        headers = self._headers(client, email)

        conversation = client.post(
            "/api/conversations/",
            headers=headers,
            json={"priority": "low", "channel": "api"},
        )
        conversation_id = conversation.json()["id"]

        from app.routers.users.message import make_fingerprint, make_idempotency_key

        from app.schemas.message import MessageCreate

        message = MessageCreate(content="уже выполняется")
        key = make_idempotency_key(
            int(conversation.json()["user_id"]),
            conversation_id,
            "processing-key",
        )
        fake.store[key] = {
            "fingerprint": make_fingerprint(message),
            "status": "processing",
        }

        response = client.post(
            f"/api/conversations/{conversation_id}/messages",
            headers={**headers, "Idempotency-Key": "processing-key"},
            json={"content": "уже выполняется"},
        )

        assert response.status_code == 409
        assert "уже выполняется" in response.json()["detail"]

    def test_reserve_race_returns_completed_response(self, client, create_test_user, monkeypatch):
        fake = self._install_fake_idempotency(monkeypatch)
        email = f"idempotent_race_{uuid4().hex[:8]}@example.com"
        create_test_user(email=email, nickname=f"idempotent_race_{uuid4().hex[:8]}")
        headers = self._headers(client, email)

        conversation = client.post(
            "/api/conversations/",
            headers=headers,
            json={"priority": "low", "channel": "api"},
        )
        conversation_id = conversation.json()["id"]

        from app.routers.users.message import make_fingerprint, make_idempotency_key
        from app.schemas.message import MessageCreate

        message = MessageCreate(content="гонка")
        key = make_idempotency_key(
            int(conversation.json()["user_id"]),
            conversation_id,
            "race-key",
        )
        fake.store[key] = {
            "fingerprint": make_fingerprint(message),
            "status": "completed",
            "response": {
                "id": 777,
                "conversation_id": conversation_id,
                "sender_type": "user",
                "sender_id": int(conversation.json()["user_id"]),
                "content": "гонка",
                "is_auto_reply": False,
                "confidence": None,
                "needs_review": False,
                "created_at": "2026-09-21T00:00:00",
            },
        }

        original_get = fake.get
        first_get = True

        def get_after_race(key_to_read):
            nonlocal first_get
            if first_get:
                first_get = False
                return None
            return original_get(key_to_read)

        fake.get = get_after_race
        fake.reserve = lambda _key, _fingerprint: False

        response = client.post(
            f"/api/conversations/{conversation_id}/messages",
            headers={**headers, "Idempotency-Key": "race-key"},
            json={"content": "гонка"},
        )

        assert response.status_code == 201
        assert response.json()["id"] == 777

    def test_message_service_failure_clears_idempotency_key(
        self, client, create_test_user, monkeypatch
    ):
        fake = self._install_fake_idempotency(monkeypatch)
        email = f"idempotent_error_{uuid4().hex[:8]}@example.com"
        create_test_user(email=email, nickname=f"idempotent_error_{uuid4().hex[:8]}")
        headers = self._headers(client, email)

        conversation = client.post(
            "/api/conversations/",
            headers=headers,
            json={"priority": "low", "channel": "web"},
        )
        conversation_id = conversation.json()["id"]

        with patch(
            "app.routers.users.message.MessageService.create_message",
            new=AsyncMock(side_effect=RuntimeError("service failed")),
        ):
            with pytest.raises(RuntimeError, match="service failed"):
                client.post(
                    f"/api/conversations/{conversation_id}/messages",
                    headers={**headers, "Idempotency-Key": "error-key"},
                    json={"content": "сломаться"},
                )

        assert fake.store == {}
