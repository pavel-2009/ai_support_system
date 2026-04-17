"""Репозиторий для работы с диалогами."""

from datetime import datetime

from sqlalchemy import case, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import (
    AuditLog,
    Channel,
    Conversation,
    ConversationOperatorLink,
    Priority,
    Status,
)


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
        await self.session.flush()
        await self._create_audit_log(
            conversation_id=new_conversation.id,
            action="conversation_created",
            actor_id=user_id,
            to_status=Status.OPEN,
        )
        await self.session.commit()
        await self.session.refresh(new_conversation)
        return new_conversation

    async def get_conversation_by_id(self, conversation_id: int) -> Conversation | None:
        result = await self.session.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        return result.scalar_one_or_none()

    async def get_active_queue(self) -> list[Conversation]:
        priority_order = case(
            (Conversation.priority == Priority.HIGH, 3),
            (Conversation.priority == Priority.MEDIUM, 2),
            else_=1,
        )
        result = await self.session.execute(
            select(Conversation)
            .where(Conversation.status != Status.CLOSED)
            .order_by(priority_order.desc(), Conversation.created_at.asc())
        )
        return list(result.scalars().all())

    async def _create_audit_log(
        self,
        conversation_id: int,
        action: str,
        actor_id: int | None = None,
        from_status: Status | None = None,
        to_status: Status | None = None,
    ) -> None:
        self.session.add(
            AuditLog(
                conversation_id=conversation_id,
                actor_id=actor_id,
                action=action,
                from_status=from_status,
                to_status=to_status,
            )
        )

    async def update_conversation_status(
        self,
        conversation_id: int,
        new_status: Status,
    ) -> Conversation | None:
        conversation = await self.get_conversation_by_id(conversation_id)
        if conversation is None:
            return None

        old_status = conversation.status
        conversation.status = new_status
        await self._create_audit_log(
            conversation_id=conversation.id,
            action="status_changed",
            from_status=old_status,
            to_status=new_status,
        )
        await self.session.commit()
        await self.session.refresh(conversation)
        return conversation

    async def assign_operator(self, conversation_id: int, operator_id: int) -> Conversation | None:
        conversation = await self.get_conversation_by_id(conversation_id)
        if conversation is None:
            return None

        previous_operator_id = conversation.operator_id
        previous_status = conversation.status

        conversation.operator_id = operator_id
        conversation.status = Status.WAITING_FOR_OPERATOR
        active_links = (
            await self.session.execute(
                select(ConversationOperatorLink).where(
                    ConversationOperatorLink.conversation_id == conversation_id,
                    ConversationOperatorLink.is_active.is_(True),
                )
            )
        ).scalars().all()
        for link in active_links:
            link.is_active = False
            link.unassigned_at = datetime.utcnow()

        self.session.add(
            ConversationOperatorLink(
                conversation_id=conversation_id,
                operator_id=operator_id,
                is_active=True,
            )
        )
        await self._create_audit_log(
            conversation_id=conversation.id,
            actor_id=operator_id,
            action="operator_assigned",
            from_status=previous_status,
            to_status=Status.WAITING_FOR_OPERATOR,
        )
        if previous_operator_id is not None and previous_operator_id != operator_id:
            await self._create_audit_log(
                conversation_id=conversation.id,
                actor_id=previous_operator_id,
                action="operator_unassigned",
            )
        await self.session.commit()
        await self.session.refresh(conversation)
        return conversation

    async def close_conversation(self, conversation_id: int) -> Conversation | None:
        conversation = await self.get_conversation_by_id(conversation_id)
        if conversation is None:
            return None

        old_status = conversation.status
        conversation.status = Status.CLOSED
        conversation.closed_at = datetime.utcnow()
        await self._create_audit_log(
            conversation_id=conversation.id,
            action="conversation_closed",
            from_status=old_status,
            to_status=Status.CLOSED,
        )
        await self.session.commit()
        await self.session.refresh(conversation)
        return conversation
