"""Репозиторий для работы с диалогами."""

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import AuditLog, Channel, Conversation, Priority, Status


class ConversationRepository:
    """Репозиторий для CRUD и query-операций с диалогами."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_conversation(
        self,
        user_id: int,
        priority: Priority,
        channel: Channel,
    ) -> Conversation:
        """Создать новый диалог."""
        new_conversation = Conversation(
            user_id=user_id,
            priority=priority,
            channel=channel,
            status=Status.OPEN,
        )
        self.session.add(new_conversation)
        await self.session.flush()
        self.session.add(
            AuditLog(
                conversation_id=new_conversation.id,
                action="conversation_created",
                actor_id=user_id,
                to_status=Status.OPEN,
            )
        )
        await self.session.refresh(new_conversation)
        return new_conversation

    async def get_conversation_by_id(self, conversation_id: int) -> Conversation | None:
        """Получить диалог по ID."""
        result = await self.session.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        return result.scalar_one_or_none()

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
        """Получить список диалогов с фильтрами и пагинацией."""
        query = select(Conversation)

        if participant_id is not None:
            query = query.where(
                (Conversation.user_id == participant_id)
                | (Conversation.operator_id == participant_id)
            )
        if status_filter is not None:
            query = query.where(Conversation.status == status_filter)
        if priority_filter is not None:
            query = query.where(Conversation.priority == priority_filter)
        if channel_filter is not None:
            query = query.where(Conversation.channel == channel_filter)
        if user_id_filter is not None:
            query = query.where(Conversation.user_id == user_id_filter)
        if operator_id_filter is not None:
            query = query.where(Conversation.operator_id == operator_id_filter)

        result = await self.session.execute(
            query.order_by(Conversation.created_at.desc()).limit(limit).offset(offset)
        )
        return list(result.scalars().all())

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
        query = select(func.count(Conversation.id))

        if participant_id is not None:
            query = query.where(
                (Conversation.user_id == participant_id)
                | (Conversation.operator_id == participant_id)
            )
        if status_filter is not None:
            query = query.where(Conversation.status == status_filter)
        if priority_filter is not None:
            query = query.where(Conversation.priority == priority_filter)
        if channel_filter is not None:
            query = query.where(Conversation.channel == channel_filter)
        if user_id_filter is not None:
            query = query.where(Conversation.user_id == user_id_filter)
        if operator_id_filter is not None:
            query = query.where(Conversation.operator_id == operator_id_filter)

        result = await self.session.execute(query)
        return int(result.scalar_one())

    async def get_active_queue(self) -> list[Conversation]:
        """Получить очередь эскалированных диалогов."""
        priority_order = case(
            (Conversation.priority == Priority.HIGH, 3),
            (Conversation.priority == Priority.MEDIUM, 2),
            else_=1,
        )
        result = await self.session.execute(
            select(Conversation)
            .where(Conversation.status.in_([Status.ESCALATED]))
            .order_by(priority_order.desc(), Conversation.created_at.asc())
        )
        return list(result.scalars().all())
