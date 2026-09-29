"""Сервис для работы с сообщениями."""

from app.core.logging import get_logger
from app.core.cache import Cache
from app.core.config import settings
from app.core.uow import UnitOfWork
from app.domain.events import ConversationMarkedForReview, MessageSent
from app.models.conversation import Status
from app.models.user import UserRole


logger = get_logger(__name__)


class MessageService:
    """Сервис для работы с сообщениями."""

    def __init__(self, uow: UnitOfWork, cache: Cache | None = None):
        self.uow = uow
        self.cache = cache

    async def get_conversation_status(self, conversation_id: int) -> Status | None:
        conversation = await self.uow.conversation.get_conversation_by_id(conversation_id)
        return conversation.status if conversation is not None else None

    async def _invalidate_conversation_cache(self, conversation_id: int) -> None:
        if self.cache is not None:
            await self.cache.delete(f"{settings.CONVERSATION_CACHE_KEY_PREFIX}{conversation_id}")

    async def create_message(
        self,
        conversation_id: int,
        sender_type: str,
        sender_id: int | None,
        content: str,
        is_auto_reply: bool = False,
        confidence: float | None = None,
        needs_review: bool = False,
    ):
        """Создать новое сообщение."""
        new_message = await self.uow.message.create_message(
            conversation_id=conversation_id,
            sender_type=sender_type,
            sender_id=sender_id,
            content=content,
            is_auto_reply=is_auto_reply,
            confidence=confidence,
            needs_review=needs_review,
        )
        if new_message is None:
            logger.warning(
                "MESSAGE SERVICE CREATE REJECTED: conversation_id=%s sender_type=%s sender_id=%s",
                conversation_id,
                sender_type,
                sender_id,
            )
            return None

        if sender_type == UserRole.OPERATOR.value and sender_id is not None:
            updated_conversation = await self.uow.state_machine.operator_replied(
                conversation_id,
                sender_id,
            )
            if updated_conversation is None:
                logger.warning(
                    "MESSAGE SERVICE OPERATOR REPLY STATE UPDATE REJECTED: "
                    "conversation_id=%s operator_id=%s",
                    conversation_id,
                    sender_id,
                )
                return None
            await self._invalidate_conversation_cache(conversation_id)

        if sender_type == UserRole.USER.value:
            updated_conversation = await self.uow.state_machine.user_replied(conversation_id)
            if updated_conversation is None:
                logger.warning("MESSAGE SERVICE USER REPLY STATE UPDATE REJECTED: conversation_id=%s", conversation_id)
                return None
            await self._invalidate_conversation_cache(conversation_id)

        if sender_type == "ai" and not needs_review:
            updated_conversation = await self.uow.state_machine.ai_replied(conversation_id)
            if updated_conversation is None:
                logger.debug("ai_response_state_update_skipped", conversation_id=conversation_id)
                return None
            await self._invalidate_conversation_cache(conversation_id)

        if needs_review:
            updated_conversation = await self.uow.state_machine.mark_for_review(conversation_id)
            if updated_conversation is not None:
                await self._invalidate_conversation_cache(conversation_id)
                self.uow.add_event(ConversationMarkedForReview(str(conversation_id)))

        self.uow.add_event(MessageSent(str(new_message.id), str(conversation_id)))

        return new_message

    async def get_messages_by_conversation(self, conversation_id: int):
        """Получить все сообщения для заданного conversation_id."""
        return await self.uow.message.get_messages_by_conversation(conversation_id)
