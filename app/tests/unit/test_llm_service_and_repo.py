"""Unit-тесты для LLMService и LLMRepository."""

from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.config import settings
from app.core.exceptions import LLMResponseFailed
from app.repositories.llm_repo import LLMRepository
from app.schemas.llm import LLMResponse
from app.services.llm_service import LLMService


class _FakeScalars:
    def __init__(self, values):
        self._values = values

    def all(self):
        return self._values


class _FakeResult:
    def __init__(self, values):
        self._values = values

    def scalars(self):
        return _FakeScalars(self._values)


class TestLLMService:
    @pytest.mark.asyncio
    async def test_generate_response_delegates_to_repo(self):
        expected = LLMResponse(answer="ok", confidence=0.9, topic="billing")
        repo = MagicMock()

        async def async_get_llm_response(*args, **kwargs):
            return expected

        repo.get_llm_response = async_get_llm_response
        service = LLMService(repo)

        actual = await service.generate_response(conversation_id=42, session=MagicMock())

        assert actual == expected


class TestLLMRepositoryHelpers:
    @patch("app.repositories.llm_repo.AsyncOpenAI")
    def test_uses_configured_llm_endpoint(self, openai_mock):
        LLMRepository(api_key="x", model="test-model")
        openai_mock.assert_called_once_with(
            base_url=settings.LLM_BASE_URL,
            api_key="x",
        )

    @patch("app.repositories.llm_repo.AsyncOpenAI")
    def test_generate_system_prompt_contains_simple_json_contract(self, _openai_mock):
        repo = LLMRepository(api_key="x", model="test-model")
        prompt = repo._generate_system_prompt()

        assert "exactly one JSON object" in prompt
        assert "answer" in prompt
        assert "confidence" in prompt
        assert "topic" in prompt
        assert "Do not return a JSON Schema" in prompt
        assert "Assistant:" not in prompt

    @patch("app.repositories.llm_repo.AsyncOpenAI")
    def test_generate_messages_history_uses_correct_roles_and_order(self, _openai_mock):
        repo = LLMRepository(api_key="x", model="test-model")
        history = [
            SimpleNamespace(sender_type="user", content="hello"),
            SimpleNamespace(sender_type="ai", content="previous answer"),
            SimpleNamespace(sender_type="operator", content="operator answer"),
        ]

        messages = repo._generate_messages_history(history)

        assert messages[0]["role"] == "system"
        assert messages[1] == {"role": "user", "content": "hello"}
        assert messages[2] == {"role": "assistant", "content": "previous answer"}
        assert messages[3] == {"role": "assistant", "content": "operator answer"}

    @pytest.mark.asyncio
    @patch("app.repositories.llm_repo.AsyncOpenAI")
    async def test_generate_prompt_takes_last_five_in_chronological_order(self, _openai_mock):
        repo = LLMRepository(api_key="x", model="test-model")
        now = datetime.utcnow()
        messages = [
            SimpleNamespace(
                content=f"msg_{i}", sender_type="user", created_at=now - timedelta(minutes=i)
            )
            for i in range(6, -1, -1)
        ]

        session = MagicMock()
        session.execute = AsyncMock(return_value=_FakeResult(messages))

        prompt_messages = await repo._generate_prompt(conversation_id=1, session=session)

        assert len(prompt_messages) == 6
        user_contents = [m["content"] for m in prompt_messages if m["role"] == "user"]
        assert user_contents == ["msg_0", "msg_1", "msg_2", "msg_3", "msg_4"]
        session.execute.assert_awaited_once()


class TestLLMRepositoryResponses:
    @pytest.mark.asyncio
    @patch("app.repositories.llm_repo.AsyncOpenAI")
    async def test_generate_response_parses_valid_json(self, openai_mock):
        repo = LLMRepository(api_key="x", model="test-model")
        content = '{"answer": "A", "confidence": 0.77, "topic": "support"}'
        repo.client.chat.completions.create = AsyncMock(
            return_value=SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
            )
        )

        with patch.object(
            repo,
            "_generate_prompt",
            new=AsyncMock(return_value=[
                {"role": "system", "content": "prompt"},
                {"role": "user", "content": "Q"},
            ]),
        ):
            result = await repo._generate_response(conversation_id=9, session=MagicMock())

        assert result == LLMResponse(answer="A", confidence=0.77, topic="support")
        call_kwargs = repo.client.chat.completions.create.call_args.kwargs
        assert call_kwargs["response_format"] == {"type": "json_object"}
        repo.client.chat.completions.create.assert_awaited_once()
        assert openai_mock.called

    @pytest.mark.asyncio
    @patch("app.repositories.llm_repo.AsyncOpenAI")
    async def test_generate_response_on_invalid_json_raises(self, _openai_mock):
        repo = LLMRepository(api_key="x", model="test-model")
        repo.client.chat.completions.create = AsyncMock(
            return_value=SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="Assistant"))]
            )
        )

        with patch.object(
            repo,
            "_generate_prompt",
            new=AsyncMock(return_value=[
                {"role": "system", "content": "prompt"},
                {"role": "user", "content": "Q"},
            ]),
        ):
            with pytest.raises(LLMResponseFailed, match="invalid JSON"):
                await repo._generate_response(conversation_id=9, session=MagicMock())

        repo.client.chat.completions.create.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("app.repositories.llm_repo.AsyncOpenAI")
    async def test_generate_response_on_schema_error_raises(self, _openai_mock):
        repo = LLMRepository(api_key="x", model="test-model")
        bad_schema_json = '{"answer": "A", "topic": "support"}'
        repo.client.chat.completions.create = AsyncMock(
            return_value=SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content=bad_schema_json))]
            )
        )

        with patch.object(
            repo,
            "_generate_prompt",
            new=AsyncMock(return_value=[
                {"role": "system", "content": "prompt"},
                {"role": "user", "content": "Q"},
            ]),
        ):
            with pytest.raises(LLMResponseFailed, match="validation failed"):
                await repo._generate_response(conversation_id=9, session=MagicMock())

    @pytest.mark.asyncio
    @patch("app.repositories.llm_repo.AsyncOpenAI")
    async def test_generate_response_rejects_json_schema_echo(self, _openai_mock):
        repo = LLMRepository(api_key="x", model="test-model")
        schema_echo = '{"type":"object","properties":{"answer":{"type":"string"}}}'
        repo.client.chat.completions.create = AsyncMock(
            return_value=SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content=schema_echo))]
            )
        )

        with patch.object(
            repo,
            "_generate_prompt",
            new=AsyncMock(return_value=[
                {"role": "system", "content": "prompt"},
                {"role": "user", "content": "Q"},
            ]),
        ):
            with pytest.raises(LLMResponseFailed, match="validation failed"):
                await repo._generate_response(conversation_id=9, session=MagicMock())

    @pytest.mark.asyncio
    @patch("app.repositories.llm_repo.AsyncOpenAI")
    async def test_get_llm_response_makes_only_one_attempt(self, _openai_mock):
        repo = LLMRepository(api_key="x", model="test-model")
        generate_response = AsyncMock(side_effect=LLMResponseFailed("boom"))

        with patch.object(repo, "_generate_response", new=generate_response):
            with pytest.raises(LLMResponseFailed, match="boom"):
                await repo.get_llm_response(conversation_id=5, session=MagicMock())

        generate_response.assert_awaited_once()
