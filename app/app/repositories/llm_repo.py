"""Репозиторий для работы с облачной LLM моделью для генерации ответов на вопросы пользователей."""

from typing import List
from openai import OpenAI

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import asyncio
import inspect

import json

from ..core.config import settings
from ..core.exceptions import LLMResponseFailed

from ..schemas.llm import LLMResponse
from ..models.message import Message


class LLMRepository:
    """Репозиторий для работы с облачной LLM моделью для генерации ответов на вопросы пользователей."""

    def __init__(
        self,
        api_key: str = settings.LLM_API_KEY,
        model: str = settings.LLM_MODEL,
        ):
        
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )
        self.model = model

    async def _generate_response(self, conversation_id: int, session: AsyncSession) -> LLMResponse:
        """Генерирует ответ на заданный вопрос с помощью LLM модели."""
        messages = await self._generate_prompt(conversation_id, session)
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=settings.LLM_TOKEN_LIMIT,
            temperature=settings.LLM_TEMPERATURE,
            timeout=settings.LLM_TIMEOUT,
        )
        
        try:
            return LLMResponse(**json.loads(response.choices[0].message.content))
        except json.JSONDecodeError:
            return LLMResponse(
                answer='У меня нет ответа на этот вопрос.',
                confidence=0.1,
                topic="unknown",
            )  
        except Exception as e:
            raise LLMResponseFailed(f"Error parsing LLM response: {str(e)}") 

    def _generate_messages_history(
        self,
        conversation_history: List[str]
    ) -> List[dict]:
        """Генерирует список сообщений для отправки в LLM модель на основе истории разговора и текущего вопроса."""
        
        messages = []
        
        for msg in conversation_history:
            messages.append({"role": "user", "content": msg})
            
        messages.append({"role": "system", "content": self._generate_system_prompt(conversation_history)})
        
        return messages
    
    
    def _generate_system_prompt(self, conversation_history: List[str]) -> str:
        """Генерирует системный промпт для LLM модели на основе истории разговора."""
        
        if not conversation_history:
            return "You are a helpful assistant."
        
        last_message = conversation_history[-1]
        return f"You are a helpful assistant. The last message from the user was: '{last_message}'"
    
    
    async def _generate_prompt(
        self,
        conversation_id: int,
        session: AsyncSession
        ) -> List[dict]:
        """Генерирует промпт для LLM модели на основе истории разговора."""
        
        # Получаем историю сообщений для данного conversation_id
        exec_result = session.execute(select(Message).where(Message.conversation_id == conversation_id))
        if inspect.isawaitable(exec_result):
            result = await exec_result
        else:
            result = exec_result

        last_messages: List[Message] = sorted(result.scalars().all(), key=lambda x: x.created_at, reverse=True)[:5]  # Берем последние 5 сообщений
        
        conversation_history = [msg.content for msg in last_messages]
        
        return self._generate_messages_history(conversation_history)
        
        
    # Основной метод для получения ответа от LLM модели
    async def get_llm_response(
        self,
        conversation_id: int,
        session: AsyncSession
    ) -> LLMResponse:
        """Получает ответ от LLM модели на основе истории разговора."""
        last_error: Exception | None = None
        for _ in range(settings.LLM_RETRY_ATTEMPTS):
            try:
                await asyncio.sleep(10)
                return await self._generate_response(conversation_id, session)
            except Exception as e:
                last_error = e
                print(f"LLM response generation failed: {str(e)}. Retrying...") # print пока заглушка для логирования
                continue

        raise LLMResponseFailed(
            f"Failed to get response from LLM model: {str(last_error) if last_error else 'Unknown error'}"
        )
