"""Class for state machine."""

from app.models.conversation import Status


STATE_GRAPH = {
    Status.OPEN: [Status.PENDING_AI, Status.ESCALATED, Status.CLOSED],
    Status.PENDING_AI: [Status.OPEN, Status.ESCALATED, Status.CLOSED],
    Status.ESCALATED: [Status.WAITING_FOR_OPERATOR, Status.CLOSED],
    Status.WAITING_FOR_OPERATOR: [Status.WAITING_FOR_USER, Status.OPEN, Status.CLOSED],
    Status.WAITING_FOR_USER: [Status.WAITING_FOR_OPERATOR, Status.PENDING_AI, Status.CLOSED],
    Status.CLOSED: [],
}


class ConversationStateMachine:
    """Validate conversation transitions without owning conversation state."""

    @staticmethod
    def can_transition(current_state: Status, new_state: Status) -> bool:
        """Return whether the requested transition is allowed."""
        return new_state in STATE_GRAPH.get(current_state, [])