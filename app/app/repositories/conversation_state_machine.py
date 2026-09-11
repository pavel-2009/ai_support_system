"""Repository-like state machine for conversation lifecycle transitions."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.conversation import (
    AuditLog,
    Conversation,
    ConversationOperatorLink,
    Status,
)
from app.models.message import Message
from app.models.user import User


STATE_GRAPH = {
    Status.OPEN: [Status.PENDING_AI, Status.ESCALATED, Status.CLOSED],
    Status.PENDING_AI: [Status.OPEN, Status.ESCALATED, Status.CLOSED],
    Status.ESCALATED: [Status.WAITING_FOR_OPERATOR, Status.CLOSED],
    Status.WAITING_FOR_OPERATOR: [Status.WAITING_FOR_USER, Status.OPEN, Status.CLOSED],
    Status.WAITING_FOR_USER: [Status.WAITING_FOR_OPERATOR, Status.PENDING_AI, Status.CLOSED],
    Status.CLOSED: [],
}


class ConversationStateMachine:
    """Own conversation status transitions and persist their results.

    This is intentionally the only persistence boundary allowed to mutate
    conversation status. It is created by UnitOfWork and uses the UnitOfWork
    session, so transitions participate in the same transaction.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def can_transition(current_state: Status, new_state: Status) -> bool:
        """Return whether a status transition is allowed."""
        return new_state in STATE_GRAPH.get(current_state, [])

    async def _get_conversation(self, conversation_id: int) -> Conversation | None:
        result = await self.session.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        return result.scalar_one_or_none()

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

    async def _transition(
        self,
        conversation: Conversation,
        new_status: Status,
    ) -> Status | None:
        previous_status = conversation.status
        if not self.can_transition(previous_status, new_status):
            return None
        conversation.status = new_status
        await self.session.flush()
        return previous_status

    async def escalate(self, conversation_id: int) -> Conversation | None:
        """Escalate a conversation to the operator queue."""
        conversation = await self._get_conversation(conversation_id)
        if conversation is None:
            return None

        previous_status = await self._transition(conversation, Status.ESCALATED)
        if previous_status is None:
            return None

        await self._create_audit_log(
            conversation_id=conversation.id,
            action="status_changed",
            from_status=previous_status,
            to_status=Status.ESCALATED,
        )
        await self.session.refresh(conversation)
        return conversation

    async def assign_operator(
        self,
        conversation_id: int,
        operator_id: int,
    ) -> Conversation | None:
        """Assign an operator and move the conversation to operator handling."""
        conversation = await self._get_conversation(conversation_id)
        if conversation is None:
            return None

        if conversation.status != Status.ESCALATED and conversation.operator_id is not None:
            return None

        operator = (
            await self.session.execute(select(User).where(User.id == operator_id))
        ).scalar_one_or_none()
        if operator is None:
            return None
        if operator.active_conversations_count >= settings.MAX_OPERATOR_ACTIVE_CONVERSATIONS:
            return None

        previous_operator_id = conversation.operator_id
        previous_status = await self._transition(
            conversation,
            Status.WAITING_FOR_OPERATOR,
        )
        if previous_status is None:
            return None

        conversation.operator_id = operator_id

        if previous_operator_id is not None and previous_operator_id != operator_id:
            previous_operator = (
                await self.session.execute(
                    select(User).where(User.id == previous_operator_id)
                )
            ).scalar_one_or_none()
            if previous_operator is not None and previous_operator.active_conversations_count > 0:
                previous_operator.active_conversations_count -= 1

        operator.active_conversations_count += 1
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
        await self.session.flush()
        await self.session.refresh(conversation)
        return conversation

    async def close(self, conversation_id: int) -> Conversation | None:
        """Close a conversation and release its active operator slot."""
        conversation = await self._get_conversation(conversation_id)
        if conversation is None:
            return None

        current_operator_id = conversation.operator_id
        previous_status = await self._transition(conversation, Status.CLOSED)
        if previous_status is None:
            return None
        conversation.closed_at = datetime.utcnow()

        if current_operator_id is not None:
            operator = (
                await self.session.execute(select(User).where(User.id == current_operator_id))
            ).scalar_one_or_none()
            if operator is not None and operator.active_conversations_count > 0:
                operator.active_conversations_count -= 1

        await self._create_audit_log(
            conversation_id=conversation.id,
            action="conversation_closed",
            from_status=previous_status,
            to_status=Status.CLOSED,
        )
        await self.session.flush()
        await self.session.refresh(conversation)
        return conversation

    async def back_to_ai(self, conversation_id: int) -> Conversation | None:
        """Return an operator conversation to AI after an operator message."""
        conversation = await self._get_conversation(conversation_id)
        if conversation is None:
            return None

        if conversation.status != Status.WAITING_FOR_OPERATOR or conversation.operator_id is None:
            return None

        last_message = (
            await self.session.execute(
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if last_message is None or last_message.sender_type != "operator":
            return None

        current_operator_id = conversation.operator_id
        previous_status = await self._transition(conversation, Status.OPEN)
        if previous_status is None:
            return None
        conversation.operator_id = None

        if current_operator_id is not None:
            operator = (
                await self.session.execute(select(User).where(User.id == current_operator_id))
            ).scalar_one_or_none()
            if operator is not None and operator.active_conversations_count > 0:
                operator.active_conversations_count -= 1

        await self._create_audit_log(
            conversation_id=conversation.id,
            action="back_to_ai",
            from_status=previous_status,
            to_status=Status.OPEN,
        )
        await self.session.flush()
        await self.session.refresh(conversation)
        return conversation

    async def mark_for_review(self, conversation_id: int) -> Conversation | None:
        """Escalate a conversation because an AI response needs operator review."""
        conversation = await self._get_conversation(conversation_id)
        if conversation is None:
            return None

        previous_status = await self._transition(conversation, Status.ESCALATED)
        if previous_status is None:
            return None

        await self._create_audit_log(
            conversation_id=conversation.id,
            action="conversation_marked_for_review",
            from_status=previous_status,
            to_status=Status.ESCALATED,
        )
        await self.session.refresh(conversation)
        return conversation
