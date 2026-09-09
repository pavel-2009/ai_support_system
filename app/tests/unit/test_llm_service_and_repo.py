"""Unit-тесты для LLMService и LLMRepository."""

from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

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
    @patch("app.repositories.llm_repo.OpenAI")
    def test_uses_configured_llm_endpoint(self, openai_mock):
        LLMRepository(api_key="x", model="test-model")
        openai_mock.assert_called_once_with(
            base_url=settings.LLM_BASE_URL,
            api_key="x",
        )

    @patch("app.repositories.llm_repo.OpenAI")
    def test_generate_system_prompt_contains_json_contract(self, _openai_mock):
        repo = LLMRepository(api_key="x", model="test-model")
        prompt = repo._generate_system_prompt()

        assert "valid JSON object" in prompt
        assert "answer" in prompt
        assert "confidence" in prompt
        assert "topic" in prompt
        assert "Assistant:" in prompt

    @patch("app.repositories.llm_repo.OpenAI")
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
    @patch("app.repositories.llm_repo.OpenAI")
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
        session.execute = MagicMock(return_value=_FakeResult(messages))

        prompt_messages = await repo._generate_prompt(conversation_id=1, session=session)

        assert len(prompt_messages) == 6
        user_contents = [m["content"] for m in prompt_messages if m["role"] == "user"]
        assert user_contents == ["msg_0", "msg_1", "msg_2", "msg_3", "msg_4"]


class TestLLMRepositoryResponses:
    @pytest.mark.asyncio
    @patch("app.repositories.llm_repo.OpenAI")
    async def test_generate_response_parses_valid_json(self, openai_mock):
        repo = LLMRepository(api_key="x", model="test-model")
        content = '{"answer": "A", "confidence": 0.77, "topic": "support"}'
        repo.client.chat.completions.create.return_value = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
        )

        async def mock_prompt(*args, **kwargs):
            return [{"role": "user", "content": "Q"}]

        with patch.object(repo, "_generate_prompt", side_effect=mock_prompt):
            result = await repo._generate_response(conversation_id=9, session=MagicMock())

        assert result == LLMResponse(answer="A", confidence=0.77, topic="support")
        call_kwargs = repo.client.chat.completions.create.call_args.kwargs
        assert call_kwargs["response_format"] == {"type": "json_object"}
        assert openai_mock.called

    @pytest.mark.asyncio
    @patch("app.repositories.llm_repo.OpenAI")
    async def test_generate_response_on_invalid_json_returns_fallback(self, _openai_mock):
        repo = LLMRepository(api_key="x", model="test-model")
        repo.client.chat.completions.create.return_value = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="Assistant"))]
        )

        async def mock_prompt(*args, **kwargs):
            return [{"role": "user", "content": "Q"}]

        with patch.object(repo, "_generate_prompt", side_effect=mock_prompt):
            result = await repo._generate_response(conversation_id=9, session=MagicMock())

        assert result.answer == "У меня нет ответа на этот вопрос."
        assert result.confidence == pytest.approx(0.1)
        assert result.topic == "unknown"

    @pytest.mark.asyncio
    @patch("app.repositories.llm_repo.OpenAI")
    async def test_generate_response_on_schema_error_raises_llm_failed(self, _openai_mock):
        repo = LLMRepository(api_key="x", model="test-model")
        bad_schema_json = '{"answer": "A", "topic": "support"}'
        repo.client.chat.completions.create.return_value = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=bad_schema_json))]
        )

        async def mock_prompt(*args, **kwargs):
            return [{"role": "user", "content": "Q"}]

        with patch.object(repo, "_generate_prompt", side_effect=mock_prompt):
            with pytest.raises(LLMResponseFailed):
                await repo._generate_response(conversation_id=9, session=MagicMock())

    @pytest.mark.asyncio
    @patch("app.repositories.llm_repo.OpenAI")
    async def test_get_llm_response_retries_and_then_success(self, _openai_mock):
        repo = LLMRepository(api_key="x", model="test-model")
        ok = LLMResponse(answer="done", confidence=0.8, topic="topic")

        async def async_gen_response(*args, **kwargs):
            if async_gen_response.call_count == 0:
                async_gen_response.call_count += 1
                raise RuntimeError("boom")
            return ok

        async_gen_response.call_count = 0

        with patch.object(repo, "_generate_response", side_effect=async_gen_response):
            result = await repo.get_llm_response(conversation_id=5, session=MagicMock())

        assert result == ok

    @pytest.mark.asyncio
    @patch("app.repositories.llm_repo.OpenAI")
    async def test_get_llm_response_raises_after_all_retries(self, _openai_mock):
        repo = LLMRepository(api_key="x", model="test-model")

        async def async_failing_response(*args, **kwargs):
            raise RuntimeError("boom")

        with patch.object(repo, "_generate_response", side_effect=async_failing_response):
            with pytest.raises(LLMResponseFailed) as exc:
                await repo.get_llm_response(conversation_id=5, session=MagicMock())

        assert "Failed to get response from LLM model" in str(exc.value)
        assert "boom" in str(exc.value)
