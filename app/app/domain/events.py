"""Классы событий, которые могут происходить в системе."""

class DomainEvent:
    """Базовый класс для всех событий в доменной модели."""
    pass


class ConversationCreated(DomainEvent):
    """Событие, которое возникает при создании нового разговора."""
    def __init__(self, conversation_id: str):
        self.conversation_id = conversation_id

class MessageSent(DomainEvent):
    """Событие, которое возникает при отправке нового сообщения."""
    def __init__(self, message_id: str, conversation_id: str):
        self.message_id = message_id
        self.conversation_id = conversation_id

class ConversationEscalated(DomainEvent):
    """Событие, которое возникает при эскалации разговора."""
    def __init__(self, conversation_id: str):
        self.conversation_id = conversation_id

class ConversationClosed(DomainEvent):
    """Событие, которое возникает при закрытии разговора."""
    def __init__(self, conversation_id: str):
        self.conversation_id = conversation_id

class OperatorAssigned(DomainEvent):
    """Событие, которое возникает при назначении оператора на разговор."""
    def __init__(self, conversation_id: str, operator_id: str):
        self.conversation_id = conversation_id
        self.operator_id = operator_id
