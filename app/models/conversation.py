"""SQLAlchemy модели для диалогов и связанных сущностей."""

from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, Column, DateTime, Enum as SqlEnum, Float, ForeignKey, Index, Integer, String
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
    audit_logs = relationship("AuditLog", back_populates="conversation", cascade="all, delete-orphan")
    operator_links = relationship(
        "ConversationOperatorLink",
        back_populates="conversation",
        cascade="all, delete-orphan",
    )

    __table_args__ = (Index("idx_status_priority", "status", "priority"),)


class ConversationOperatorLink(Base):
    """Промежуточная модель связи операторов с диалогами (история назначений)."""

    __tablename__ = "conversation_operator_links"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    operator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    assigned_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    unassigned_at = Column(DateTime, nullable=True)

    conversation = relationship("Conversation", back_populates="operator_links")
    operator = relationship("User", back_populates="conversation_links")

    __table_args__ = (
        Index("idx_conversation_operator_active", "conversation_id", "operator_id", "is_active"),
    )


class AuditLog(Base):
    """Базовая модель audit-логов действий по диалогу."""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False, index=True)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String, nullable=False)
    from_status = Column(SqlEnum(Status), nullable=True)
    to_status = Column(SqlEnum(Status), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    conversation = relationship("Conversation", back_populates="audit_logs")
    actor = relationship("User", back_populates="audit_logs")
