"""Сервис для работы с диалогами."""

from typing import Any

from app.core.uow import UnitOfWork
from app.core.cache import Cache
from app.domain.events import (
    ConversationClosed,
    ConversationCreated,
    ConversationEscalated,
    ConversationMarkedForReview,
    ConversationReturnedToAI,
    OperatorAssigned,
)
from app.models.conversation import Channel, Conversation, Priority, Status
from app.schemas.conversation import ConversationGet


class ConversationService:
    """Сервис для работы с диалогами."""

    CACHE_TTL_SECONDS = 60
    CONVERSATION_CACHE_PREFIX = "conversations:item:"
    ACTIVE_QUEUE_CACHE_KEY = "conversations:active_queue"

    def __init__(self, uow: UnitOfWork, cache: Cache):
        self.uow = uow
        self.cache = cache

    async def create_conversation(
        self,
        user_id: int,
        priority: Priority,
        channel: Channel,
    ) -> Conversation:
        conversation = await self.uow.conversation.create_conversation(user_id, priority, channel)
        self.uow.add_event(ConversationCreated(str(conversation.id)))
        return conversation

    async def get_conversation_by_id(self, conversation_id: int) -> Conversation | None:
        async def load_conversation() -> dict[str, Any] | None:
            conversation = await self.uow.conversation.get_conversation_by_id(conversation_id)
            if conversation is None:
                return None
            return ConversationGet.model_validate(conversation).model_dump(mode="json")

        cached = await self.cache.get_or_set(
            self._conversation_cache_key(conversation_id),
            load_conversation,
            self.CACHE_TTL_SECONDS,
        )
        if cached is None:
            return None
        return self._conversation_from_cache(cached)

    async def list_conversations(
        self,
        limit: int,
        offset: int,
        status_filter: Status | None = None,
        priority_filter: Priority | None = None,
        channel_filter: Channel | None = None,
        user_id_filter: int | None = None,
        operator_id_filter: int | None = None,
        participant_id: int | None = None,
    ) -> list[Conversation]:
        """Получить список диалогов по фильтрам и пагинации."""
        return await self.uow.conversation.list_conversations(
            limit=limit,
            offset=offset,
            status_filter=status_filter,
            priority_filter=priority_filter,
            channel_filter=channel_filter,
            user_id_filter=user_id_filter,
            operator_id_filter=operator_id_filter,
            participant_id=participant_id,
        )

    async def count_conversations(
        self,
        status_filter: Status | None = None,
        priority_filter: Priority | None = None,
        channel_filter: Channel | None = None,
        user_id_filter: int | None = None,
        operator_id_filter: int | None = None,
        participant_id: int | None = None,
    ) -> int:
        """Посчитать количество диалогов по фильтрам."""
        return await self.uow.conversation.count_conversations(
            status_filter=status_filter,
            priority_filter=priority_filter,
            channel_filter=channel_filter,
            user_id_filter=user_id_filter,
            operator_id_filter=operator_id_filter,
            participant_id=participant_id,
        )

    async def get_active_queue(self) -> list[Conversation]:
        async def load_queue() -> list[dict[str, Any]]:
            conversations = await self.uow.conversation.get_active_queue()
            return [
                ConversationGet.model_validate(conversation).model_dump(mode="json")
                for conversation in conversations
            ]

        cached = await self.cache.get_or_set(
            self.ACTIVE_QUEUE_CACHE_KEY,
            load_queue,
            self.CACHE_TTL_SECONDS,
        )
        return [self._conversation_from_cache(item) for item in cached]

    async def escalate(self, conversation_id: int) -> Conversation | None:
        """Escalate a conversation through the state machine."""
        conversation = await self.uow.state_machine.escalate(conversation_id)
        if conversation is not None:
            await self._invalidate_conversation_cache(conversation_id)
            self.uow.add_event(ConversationEscalated(str(conversation.id)))
        return conversation

    async def assign_operator(self, conversation_id: int, operator_id: int) -> Conversation | None:
        conversation = await self.uow.state_machine.assign_operator(conversation_id, operator_id)
        if conversation is not None:
            await self._invalidate_conversation_cache(conversation_id)
            self.uow.add_event(OperatorAssigned(str(conversation.id), str(operator_id)))
        return conversation

    async def close(self, conversation_id: int) -> Conversation | None:
        conversation = await self.uow.state_machine.close(conversation_id)
        if conversation is not None:
            await self._invalidate_conversation_cache(conversation_id)
            self.uow.add_event(ConversationClosed(str(conversation.id)))
        return conversation

    async def back_to_ai(self, conversation_id: int) -> Conversation | None:
        conversation_before = await self.uow.conversation.get_conversation_by_id(conversation_id)
        if conversation_before is None:
            return None

        previous_operator_id = conversation_before.operator_id
        conversation = await self.uow.state_machine.back_to_ai(conversation_id)
        if conversation is not None:
            await self._invalidate_conversation_cache(conversation_id)
            self.uow.add_event(
                ConversationReturnedToAI(
                    str(conversation.id),
                    str(previous_operator_id) if previous_operator_id is not None else "",
                )
            )
        return conversation

    async def mark_conversation_for_review(self, conversation_id: int) -> Conversation | None:
        conversation = await self.uow.state_machine.mark_for_review(conversation_id)
        if conversation is not None:
            await self._invalidate_conversation_cache(conversation_id)
            self.uow.add_event(ConversationMarkedForReview(str(conversation.id)))
            self.uow.add_event(ConversationEscalated(str(conversation.id)))
        return conversation

    async def _invalidate_conversation_cache(self, conversation_id: int) -> None:
        await self.cache.delete(self._conversation_cache_key(conversation_id))
        await self.cache.delete(self.ACTIVE_QUEUE_CACHE_KEY)

    @classmethod
    def _conversation_cache_key(cls, conversation_id: int) -> str:
        return f"{cls.CONVERSATION_CACHE_PREFIX}{conversation_id}"

    @staticmethod
    def _conversation_from_cache(data: dict[str, Any]) -> Conversation:
        validated = ConversationGet.model_validate(data)
        return Conversation(**validated.model_dump())
