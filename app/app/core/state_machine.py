"""Class for state machine."""

from app.models.conversation import Status


STATE_GRAPH = {
    Status.OPEN: [Status.PENDING_AI, Status.ESCALATED],
    Status.PENDING_AI: [Status.OPEN, Status.ESCALATED],
    Status.ESCALATED: [Status.WAITING_FOR_OPERATOR],
    Status.WAITING_FOR_OPERATOR: [Status.WAITING_FOR_USER, Status.OPEN],
    Status.WAITING_FOR_USER: [Status.WAITING_FOR_OPERATOR, Status.PENDING_AI],
    Status.CLOSED: [],
}


class ConversationStateMachine:
    """State machine for conversation status transitions."""

    def __init__(self, initial_state: Status):
        self.current_state = initial_state

    def _build_transitions(self):
        """Build a dictionary of valid transitions based on the state graph."""
        return STATE_GRAPH

    def _can_transition_to(self, new_state: Status) -> bool:
        """Check if a transition to the new state is valid."""
        valid_transitions = self._build_transitions().get(self.current_state, [])
        return new_state in valid_transitions

    def transition(self, new_state: Status) -> bool:
        """Attempt to transition to a new state. Returns True if successful, False otherwise."""
        if self._can_transition_to(new_state):
            self.current_state = new_state
            return True
        return False

    # Convenient methods for specific transitions
    def open(self) -> bool:
        return self.transition(Status.OPEN)

    def escalate(self) -> bool:
        return self.transition(Status.ESCALATED)

    def assign_to_operator(self) -> bool:
        return self.transition(Status.WAITING_FOR_OPERATOR)

    def operator_replied(self) -> bool:
        return self.transition(Status.WAITING_FOR_USER)

    def user_replied(self) -> bool:
        return self.transition(Status.PENDING_AI)

    def back_to_ai(self) -> bool:
        return self.transition(Status.PENDING_AI)

    def close(self) -> bool:
        return self.transition(Status.CLOSED)