"""Репозиторий для работы с LLM-моделью для генерации ответов пользователей."""

import json
from collections.abc import Sequence

from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..core.exceptions import LLMResponseFailed
from ..core.logging import get_logger
from ..models.message import Message
from ..schemas.llm import LLMResponse


logger = get_logger(__name__)


class LLMRepository:
    """Репозиторий для работы с LLM через OpenAI-совместимый API."""

    def __init__(
        self,
        api_key: str = settings.LLM_API_KEY,
        model: str = settings.LLM_MODEL,
    ):
        self.client = AsyncOpenAI(
            base_url=settings.LLM_BASE_URL,
            api_key=api_key,
        )
        self.model = model

    async def _generate_response(
        self,
        conversation_id: int,
        session: AsyncSession,
    ) -> LLMResponse:
        """Выполнить один запрос к LLM и строго проверить его результат."""
        messages = await self._generate_prompt(conversation_id, session)
        self._validate_request(messages)

        logger.info(
            "LLM REQUEST: model=%s conversation_id=%s messages=%s",
            self.model,
            conversation_id,
            len(messages),
        )

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=settings.LLM_TOKEN_LIMIT,
                temperature=settings.LLM_TEMPERATURE,
                timeout=settings.LLM_TIMEOUT,
                response_format={"type": "json_object"},
            )
        except Exception as exc:
            raise LLMResponseFailed(f"LLM request failed: {exc}") from exc

        content = self._extract_response_content(response)
        logger.debug("LLM RAW RESPONSE: %r", content)

        try:
            payload = json.loads(content)
        except json.JSONDecodeError as exc:
            raise LLMResponseFailed(
                "LLM returned invalid JSON"
            ) from exc

        try:
            validated = LLMResponse.model_validate(payload)
        except Exception as exc:
            raise LLMResponseFailed(
                f"LLM response validation failed: {exc}"
            ) from exc

        logger.info(
            "LLM RESPONSE VALIDATED: conversation_id=%s topic=%s confidence=%s",
            conversation_id,
            validated.topic,
            validated.confidence,
        )
        return validated

    @staticmethod
    def _validate_request(messages: Sequence[dict]) -> None:
        """Проверить минимальный контракт запроса до обращения к LLM."""
        if not messages:
            raise LLMResponseFailed("LLM request contains no messages")
        if messages[0].get("role") != "system":
            raise LLMResponseFailed("LLM request must start with a system message")
        if not messages[0].get("content"):
            raise LLMResponseFailed("LLM system prompt is empty")

    @staticmethod
    def _extract_response_content(response) -> str:
        """Проверить структуру ответа API и получить текст модели."""
        choices = getattr(response, "choices", None)
        if not choices:
            raise LLMResponseFailed("LLM response contains no choices")

        message = getattr(choices[0], "message", None)
        content = getattr(message, "content", None)
        if not isinstance(content, str) or not content.strip():
            raise LLMResponseFailed("LLM response contains no message content")

        return content.strip()

    def _generate_messages_history(
        self,
        conversation_history: Sequence[Message],
    ) -> list[dict[str, str]]:
        """Преобразовать историю сообщений в chat-completions prompt."""
        messages: list[dict[str, str]] = [
            {"role": "system", "content": self._generate_system_prompt()}
        ]

        for msg in conversation_history:
            if msg.sender_type == "user":
                role = "user"
            elif msg.sender_type in {"ai", "operator"}:
                role = "assistant"
            else:
                logger.warning(
                    "Unknown sender_type=%r; treating it as assistant",
                    msg.sender_type,
                )
                role = "assistant"

            messages.append({"role": role, "content": msg.content})

        return messages

    def _generate_system_prompt(self) -> str:
        """Возвращает простой контракт, который модель не должна интерпретировать как JSON Schema."""
        return (
            "You are an AI customer support assistant. "
            "Read the conversation history and answer the latest user message. "
            "Your output is parsed by a program. "
            "Return exactly one JSON object and nothing else. "
            "The object must contain exactly these three fields: "
            "answer, confidence, topic. "
            "answer is the final support answer as a string. "
            "confidence is a number from 0 to 1. "
            "topic is a short string describing the request. "
            "Do not return a JSON Schema. "
            "Do not use fields such as type, properties, required, description, or additionalProperties. "
            "Do not use Markdown, code fences, labels, prefixes, or suffixes. "
            "Correct structure example: "
            '{"answer":"Your answer here","confidence":0.9,"topic":"billing"}'
        )

    async def _generate_prompt(
        self,
        conversation_id: int,
        session: AsyncSession,
    ) -> list[dict[str, str]]:
        """Получить последние пять сообщений беседы в хронологическом порядке."""
        result = await session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(5)
        )
        messages = list(reversed(result.scalars().all()))
        return self._generate_messages_history(messages)

    async def get_llm_response(
        self,
        conversation_id: int,
        session: AsyncSession,
    ) -> LLMResponse:
        """Получить и проверить ровно один ответ LLM без повторных запросов."""
        return await self._generate_response(conversation_id, session)
