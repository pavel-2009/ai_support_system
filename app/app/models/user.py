"""SQLAlchemy модели для работы с пользователями."""

from enum import Enum

from sqlalchemy import Column, Enum as SqlEnum, Integer, String
from sqlalchemy.orm import relationship

from app.db import Base


class UserRole(str, Enum):
    """Роли пользователей."""

    USER = "user"
    OPERATOR = "operator"
    ADMIN = "admin"


class User(Base):
    """Модель пользователя для хранения данных в базе данных."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    nickname = Column(String, unique=True, index=True, nullable=False)
    fullname = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(SqlEnum(UserRole), default=UserRole.USER, nullable=False)
    active_conversations_count = Column(Integer, nullable=False, default=0)

    conversations = relationship(
        "Conversation",
        foreign_keys="Conversation.user_id",
        back_populates="user",
    )
    operator_conversations = relationship(
        "Conversation",
        foreign_keys="Conversation.operator_id",
        back_populates="operator",
    )
    conversation_links = relationship(
        "ConversationOperatorLink",
        back_populates="operator",
        foreign_keys="ConversationOperatorLink.operator_id",
        cascade="all, delete-orphan",
    )
    audit_logs = relationship(
        "AuditLog",
        back_populates="actor",
        foreign_keys="AuditLog.actor_id",
    )
    messages = relationship("Message", back_populates="sender", cascade="all, delete-orphan")
