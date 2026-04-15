"""SQLAlchemy модели для диалогов."""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, Index, Enum as SqlEnum
from sqlalchemy.orm import relationship

from enum import Enum

from app.db import Base


# === ENUM схемы === 
class Status(Enum):
    OPEN = 'open'
    WAITING_FOR_USER = 'waiting_for_user'
    WAITING_FOR_OPERATOR = 'waiting_for_operator'
    ESCALATED = 'escalated'
    PENDING_AI = 'pending_ai'
    CLOSED = 'closed'
    
    
class Priority(Enum):
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    
    
class Channel(Enum):
    WEB = 'web'
    API = 'api'
    EMAIL = 'email'
    

# === МОДЕЛЬ ДИАЛОГА ===
class Conversation(Base):
    """Модель диалога."""

    __tablename__ = 'conversations'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    operator_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    status = Column(SqlEnum(Status), nullable=False, default=Status.OPEN)
    priority = Column(SqlEnum(Priority), nullable=False)
    channel = Column(SqlEnum(Channel), nullable=False)
    ai_confidence = Column(Float, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    closed_at = Column(DateTime, nullable=True)
    
    # Связи
    user = relationship("User", foreign_keys=[user_id], back_populates="conversations")
    operator = relationship("User", foreign_keys=[operator_id], back_populates="operator_conversations")
    
    # Индексы
    __table_args__ = (
        # Индекс для быстрого поиска по статусу и приоритету
        Index('idx_status_priority', 'status', 'priority'),
    )
