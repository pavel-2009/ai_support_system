"""Репозиторий для работы с LLM-моделью для генерации ответов на вопросы пользователей."""

import asyncio
import inspect
import json
from typing import List

from openai import OpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..core.exceptions import LLMResponseFailed
from ..core.logging import get_logger
from ..models.message import Message
from ..schemas.llm import LLMResponse


logger = get_logger(__name__)


class LLMRepository:
    """Репозиторий для работы с LLM-моделью через OpenAI-совместимый API."""

    def __init__(
        self,
        api_key: str = settings.LLM_API_KEY,
        model: str = settings.LLM_MODEL,
    ):
        self.client = OpenAI(
            base_url=settings.LLM_BASE_URL,
            api_key=api_key,
        )
        self.model = model

    async def _generate_response(
        self,
        conversation_id: int,
        session: AsyncSession,
    ) -> LLMResponse:
        """Генерирует структурированный ответ на вопрос пользователя."""
        messages = await self._generate_prompt(conversation_id, session)

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=settings.LLM_TOKEN_LIMIT,
            temperature=settings.LLM_TEMPERATURE,
            timeout=settings.LLM_TIMEOUT,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content or ""
        logger.debug("Raw LLM response: %r", content)

        try:
            payload = json.loads(content)
        except json.JSONDecodeError:
            logger.error("LLM response is not valid JSON: %r", content)
            return LLMResponse(
                answer="У меня нет ответа на этот вопрос.",
                confidence=0.1,
                topic="unknown",
            )

        try:
            return LLMResponse.model_validate(payload)
        except Exception as exc:
            raise LLMResponseFailed(f"Error validating LLM response: {exc}") from exc

    def _generate_messages_history(
        self,
        conversation_history: List[Message],
    ) -> List[dict]:
        """Преобразует историю сообщений в корректный chat-completions prompt."""
        messages = [{"role": "system", "content": self._generate_system_prompt()}]

        for msg in conversation_history:
            if msg.sender_type == "user":
                role = "user"
            elif msg.sender_type in {"ai", "operator"}:
                role = "assistant"
            else:
                logger.warning("Unknown sender_type=%r; treating it as assistant", msg.sender_type)
                role = "assistant"

            messages.append({"role": role, "content": msg.content})

        return messages

    def _generate_system_prompt(self) -> str:
        """Возвращает строгую инструкцию для Ollama/OpenAI-compatible chat API."""
        schema = json.dumps(
            LLMResponse.model_json_schema(),
            ensure_ascii=False,
            separators=(",", ":"),
        )
        return (
            "You are an AI customer support assistant. "
            "Use the conversation history and answer the latest user message. "
            "Your response is consumed by a program, not directly by the user. "
            "Return ONLY one valid JSON object matching this schema: "
            f"{schema} "
            "The JSON object must contain exactly the fields answer, confidence, and topic. "
            "answer must be a string. confidence must be a number from 0 to 1. "
            "topic must be a short string. "
            "Do not output Markdown, code fences, explanations, prefixes, labels, "
            "or text such as 'Assistant:' before or after the JSON."
        )

    async def _generate_prompt(
        self,
        conversation_id: int,
        session: AsyncSession,
    ) -> List[dict]:
        """Получает последние сообщения беседы в хронологическом порядке."""
        exec_result = session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(5)
        )
        if inspect.isawaitable(exec_result):
            result = await exec_result
        else:
            result = exec_result

        messages = list(reversed(result.scalars().all()))[:5]
        return self._generate_messages_history(messages)

    async def get_llm_response(
        self,
        conversation_id: int,
        session: AsyncSession,
    ) -> LLMResponse:
        """Получает ответ от LLM модели на основе истории разговора."""
        last_error: Exception | None = None
        for attempt in range(settings.LLM_RETRY_ATTEMPTS):
            try:
                return await self._generate_response(conversation_id, session)
            except Exception as exc:
                last_error = exc
                logger.exception(
                    "LLM response generation failed on attempt %s/%s; retrying",
                    attempt + 1,
                    settings.LLM_RETRY_ATTEMPTS,
                )
                await asyncio.sleep(2**attempt)

        raise LLMResponseFailed(
            "Failed to get response from LLM model: "
            f"{last_error if last_error else 'Unknown error'}"
        )
