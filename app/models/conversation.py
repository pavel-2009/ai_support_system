"""SQLAlchemy модели для диалогов."""

from datetime import datetime
from enum import Enum

from sqlalchemy import Column, DateTime, Enum as SqlEnum, Float, ForeignKey, Index, Integer
from sqlalchemy.orm import relationship

from app.db import Base


class Status(str, Enum):
    OPEN = "open"
    WAITING_FOR_USER = "waiting_for_user"
    WAITING_FOR_OPERATOR = "waiting_for_operator"
    ESCALATED = "escalated"
    PENDING_AI = "pending_ai"
    CLOSED = "closed"


class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Channel(str, Enum):
    WEB = "web"
    API = "api"
    EMAIL = "email"


class Conversation(Base):
    """Модель диалога."""

    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    operator_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(SqlEnum(Status), nullable=False, default=Status.OPEN)
    priority = Column(SqlEnum(Priority), nullable=False, default=Priority.MEDIUM)
    channel = Column(SqlEnum(Channel), nullable=False, default=Channel.API)
    ai_confidence = Column(Float, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)

    user = relationship("User", foreign_keys=[user_id], back_populates="conversations")
    operator = relationship("User", foreign_keys=[operator_id], back_populates="operator_conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")

    __table_args__ = (Index("idx_status_priority", "status", "priority"),)
