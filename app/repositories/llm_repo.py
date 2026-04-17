"""Репозиторий для работы с облачной LLM моделью для генерации ответов на вопросы пользователей."""

from typing import List
from openai import OpenAI
import asyncio

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

import json

from app.core.config import settings
from app.core.exceptions import LLMResponseFailed

from app.schemas.llm import LLMResponse
from app.models.message import Message


class LLMRepository:
    """Репозиторий для работы с облачной LLM моделью для генерации ответов на вопросы пользователей."""

    def __init__(
        self,
        api_key: str = settings.LLM_API_KEY,
        model: str = settings.LLM_MODEL,
        ):
        
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def _generate_response(self, conversation_id: int, session: AsyncSession) -> LLMResponse:
        """Генерирует ответ на заданный вопрос с помощью LLM модели."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": self._generate_prompt(conversation_id, session)}],
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
    
    
    def _generate_prompt(
        self,
        conversation_id: int,
        session: AsyncSession
        ) -> str:
        """Генерирует промпт для LLM модели на основе истории разговора."""
        
        # Получаем историю сообщений для данного conversation_id
        result = asyncio.run(session.execute(select(Message).where(Message.conversation_id == conversation_id)))
        last_messages: List[Message] = sorted(result.scalars().all(), key=lambda x: x.created_at, reverse=True)[:5]  # Берем последние 5 сообщений
        
        conversation_history = {msg.sender_type: msg.content for msg in last_messages}
        
        return self._generate_messages_history(conversation_history)
        
        
    # Основной метод для получения ответа от LLM модели
    def get_llm_response(
        self,
        conversation_id: int,
        session: AsyncSession
    ) -> LLMResponse:
        """Получает ответ от LLM модели на основе истории разговора."""
        
        for _ in range(settings.LLM_RETRY_ATTEMPTS):
            try:
                return self._generate_response(conversation_id, session)
            except Exception as e:
                print(f"LLM response generation failed: {str(e)}. Retrying...") # print пока заглушка для логирования
                continue
                
        raise LLMResponseFailed(f"Failed to get response from LLM model: {str(e)}")
