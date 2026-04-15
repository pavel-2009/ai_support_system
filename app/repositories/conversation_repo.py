"""Репозиторий для работы с диалогами."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Channel, Conversation, Priority, Status


class ConversationRepository:
    """Репозиторий для работы с диалогами."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_conversation(
        self,
        user_id: int,
        priority: Priority,
        channel: Channel,
    ) -> Conversation:
        new_conversation = Conversation(
            user_id=user_id,
            priority=priority,
            channel=channel,
            status=Status.OPEN,
        )
        self.session.add(new_conversation)
        await self.session.commit()
        await self.session.refresh(new_conversation)
        return new_conversation

    async def get_conversation_by_id(self, conversation_id: int) -> Conversation | None:
        result = await self.session.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        return result.scalar_one_or_none()

    async def update_conversation_status(
        self,
        conversation_id: int,
        new_status: Status,
    ) -> Conversation | None:
        conversation = await self.get_conversation_by_id(conversation_id)
        if conversation is None:
            return None

        conversation.status = new_status
        await self.session.commit()
        await self.session.refresh(conversation)
        return conversation

    async def assign_operator(self, conversation_id: int, operator_id: int) -> Conversation | None:
        conversation = await self.get_conversation_by_id(conversation_id)
        if conversation is None:
            return None

        conversation.operator_id = operator_id
        conversation.status = Status.WAITING_FOR_OPERATOR
        await self.session.commit()
        await self.session.refresh(conversation)
        return conversation

    async def close_conversation(self, conversation_id: int) -> Conversation | None:
        conversation = await self.get_conversation_by_id(conversation_id)
        if conversation is None:
            return None

        conversation.status = Status.CLOSED
        await self.session.commit()
        await self.session.refresh(conversation)
        return conversation
