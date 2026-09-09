"""Доменные события бизнес-логики приложения."""


class DomainEvent:
    """Базовый класс для всех событий доменной модели."""


class ConversationCreated(DomainEvent):
    """Диалог создан."""

    def __init__(self, conversation_id: str):
        self.conversation_id = conversation_id


class MessageSent(DomainEvent):
    """Сообщение создано."""

    def __init__(self, message_id: str, conversation_id: str):
        self.message_id = message_id
        self.conversation_id = conversation_id


class ConversationEscalated(DomainEvent):
    """Диалог эскалирован на оператора."""

    def __init__(self, conversation_id: str):
        self.conversation_id = conversation_id


class ConversationClosed(DomainEvent):
    """Диалог закрыт."""

    def __init__(self, conversation_id: str):
        self.conversation_id = conversation_id


class OperatorAssigned(DomainEvent):
    """Оператор назначен на диалог."""

    def __init__(self, conversation_id: str, operator_id: str):
        self.conversation_id = conversation_id
        self.operator_id = operator_id


class ConversationReturnedToAI(DomainEvent):
    """Диалог возвращён из операторской очереди обратно ИИ."""

    def __init__(self, conversation_id: str, operator_id: str):
        self.conversation_id = conversation_id
        self.operator_id = operator_id


class ConversationMarkedForReview(DomainEvent):
    """Диалог помечен для обязательного ревью оператором."""

    def __init__(self, conversation_id: str):
        self.conversation_id = conversation_id


class UserRegistered(DomainEvent):
    """Пользователь зарегистрирован."""

    def __init__(self, user_id: str):
        self.user_id = user_id


class UserUpdated(DomainEvent):
    """Данные пользователя изменены."""

    def __init__(self, user_id: str):
        self.user_id = user_id


class UserDeleted(DomainEvent):
    """Пользователь удалён."""

    def __init__(self, user_id: str):
        self.user_id = user_id
