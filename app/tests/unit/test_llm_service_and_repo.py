"""Unit-тесты для LLMService и LLMRepository."""

from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.core.exceptions import LLMResponseFailed
from app.schemas.llm import LLMResponse
from app.services.llm_service import LLMService
from app.repositories.llm_repo import LLMRepository


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
        repo = MagicMock()
        expected = LLMResponse(answer="ok", confidence=0.9, topic="billing")
        repo.get_llm_response = MagicMock(return_value=expected)

        service = LLMService(repo)
        session = MagicMock()

        # Create async mock for get_llm_response
        async def async_get_llm_response(*args, **kwargs):
            return expected
        
        repo.get_llm_response = async_get_llm_response

        actual = await service.generate_response(conversation_id=42, session=session)

        assert actual == expected


class TestLLMRepositoryHelpers:
    @patch("app.repositories.llm_repo.OpenAI")
    def test_generate_system_prompt_empty_and_with_history(self, _openai_mock):
        repo = LLMRepository(api_key="x", model="test-model")

        assert repo._generate_system_prompt([]) == "You are a helpful assistant."

        prompt = repo._generate_system_prompt(["first", "latest question"])
        assert "latest question" in prompt

    @patch("app.repositories.llm_repo.OpenAI")
    def test_generate_messages_history(self, _openai_mock):
        repo = LLMRepository(api_key="x", model="test-model")

        history = ["hello", "need help"]
        messages = repo._generate_messages_history(history)

        assert messages[0] == {"role": "user", "content": "hello"}
        assert messages[1] == {"role": "user", "content": "need help"}
        assert messages[-1]["role"] == "system"

    @pytest.mark.asyncio
    @patch("app.repositories.llm_repo.OpenAI")
    async def test_generate_prompt_takes_last_five_sorted_by_created_at(self, _openai_mock):
        repo = LLMRepository(api_key="x", model="test-model")
        now = datetime.utcnow()
        messages = [
            SimpleNamespace(content=f"msg_{i}", sender_type="user", created_at=now - timedelta(minutes=i))
            for i in range(7)
        ]

        session = MagicMock()
        session.execute = MagicMock(return_value=_FakeResult(messages))

        with patch.object(
            repo, "_generate_messages_history", wraps=repo._generate_messages_history
        ) as wrap_history:
            prompt_messages = await repo._generate_prompt(conversation_id=1, session=session)

        assert len(prompt_messages) == 6  # 5 user messages + 1 system
        user_contents = [m["content"] for m in prompt_messages if m["role"] == "user"]
        assert user_contents == ["msg_0", "msg_1", "msg_2", "msg_3", "msg_4"]
        wrap_history.assert_called_once()


class TestLLMRepositoryResponses:
    @pytest.mark.asyncio
    @patch("app.repositories.llm_repo.OpenAI")
    async def test_generate_response_parses_valid_json(self, openai_mock):
        repo = LLMRepository(api_key="x", model="test-model")
        session = MagicMock()

        content = '{"answer": "A", "confidence": 0.77, "topic": "support"}'
        fake_response = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
        )
        repo.client.chat.completions.create.return_value = fake_response

        async def mock_prompt(*args, **kwargs):
            return [{"role": "user", "content": "Q"}]

        with patch.object(repo, "_generate_prompt", side_effect=mock_prompt):
            result = await repo._generate_response(conversation_id=9, session=session)

        assert isinstance(result, LLMResponse)
        assert result.answer == "A"
        assert result.confidence == pytest.approx(0.77)
        assert result.topic == "support"
        assert openai_mock.called

    @pytest.mark.asyncio
    @patch("app.repositories.llm_repo.OpenAI")
    async def test_generate_response_on_invalid_json_returns_fallback(self, _openai_mock):
        repo = LLMRepository(api_key="x", model="test-model")
        session = MagicMock()

        fake_response = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="not-json"))]
        )
        repo.client.chat.completions.create.return_value = fake_response

        async def mock_prompt(*args, **kwargs):
            return [{"role": "user", "content": "Q"}]

        with patch.object(repo, "_generate_prompt", side_effect=mock_prompt):
            result = await repo._generate_response(conversation_id=9, session=session)

        assert result.answer == "У меня нет ответа на этот вопрос."
        assert result.confidence == pytest.approx(0.1)
        assert result.topic == "unknown"

    @pytest.mark.asyncio
    @patch("app.repositories.llm_repo.OpenAI")
    async def test_generate_response_on_schema_error_raises_llm_failed(self, _openai_mock):
        repo = LLMRepository(api_key="x", model="test-model")
        session = MagicMock()

        # confidence отсутствует, из-за чего pydantic поднимет ошибку валидации
        bad_schema_json = '{"answer": "A", "topic": "support"}'
        fake_response = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=bad_schema_json))]
        )
        repo.client.chat.completions.create.return_value = fake_response

        async def mock_prompt(*args, **kwargs):
            return [{"role": "user", "content": "Q"}]

        with patch.object(repo, "_generate_prompt", side_effect=mock_prompt):
            with pytest.raises(LLMResponseFailed):
                await repo._generate_response(conversation_id=9, session=session)

    @pytest.mark.asyncio
    @patch("app.repositories.llm_repo.OpenAI")
    async def test_get_llm_response_retries_and_then_success(self, _openai_mock):
        repo = LLMRepository(api_key="x", model="test-model")
        session = MagicMock()

        ok = LLMResponse(answer="done", confidence=0.8, topic="topic")
        
        async def mock_response(*args, **kwargs):
            if mock_response.call_count < 1:
                mock_response.call_count += 1
                raise RuntimeError("boom")
            else:
                return ok
        
        mock_response.call_count = 0
        
        with patch.object(
            repo,
            "_generate_response",
            side_effect=[RuntimeError("boom"), ok],
        ) as gen:
            # Create async wrapper for side_effect
            async def async_gen_response(*args, **kwargs):
                if gen.call_count == 1:
                    raise RuntimeError("boom")
                else:
                    return ok
            
            with patch.object(repo, "_generate_response", side_effect=async_gen_response) as gen_async:
                result = await repo.get_llm_response(conversation_id=5, session=session)

        assert result == ok

    @pytest.mark.asyncio
    @patch("app.repositories.llm_repo.OpenAI")
    async def test_get_llm_response_raises_after_all_retries(self, _openai_mock):
        repo = LLMRepository(api_key="x", model="test-model")
        session = MagicMock()

        async def async_failing_response(*args, **kwargs):
            raise RuntimeError("boom")

        with patch.object(repo, "_generate_response", side_effect=async_failing_response):
            with pytest.raises(LLMResponseFailed) as exc:
                await repo.get_llm_response(conversation_id=5, session=session)

        assert "Failed to get response from LLM model" in str(exc.value)
        assert "boom" in str(exc.value)
