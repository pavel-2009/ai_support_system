"""Class for state machine."""

from app.models.conversation import Status


STATE_GRAPH = {
    Status.OPEN: [Status.PENDING_AI, Status.ESCALATED],
    Status.PENDING_AI: [Status.OPEN, Status.ESCALATED],
    Status.ESCALATED: [Status.WAITING_FOR_OPERATOR],
    Status.WAITING_FOR_OPERATOR: [Status.WAITING_FOR_USER, Status.OPEN],
    Status.WAITING_FOR_USER: [Status.WAITING_FOR_OPERATOR, Status.PENDING_AI],
}
