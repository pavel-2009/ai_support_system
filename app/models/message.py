"""SQLAlchemy модель для сообщений."""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Float, Text, Index
from sqlalchemy.orm import relationship

from app.db import Base


class Message(Base):
    """Модель для сообщений."""

    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    sender_type = Column(String, nullable=False)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    is_auto_reply = Column(Boolean, default=False, nullable=False)
    confidence = Column(Float, nullable=True)
    needs_review = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, nullable=False)
    
    # Отношения
    conversation = relationship("Conversation", back_populates="messages")
    sender = relationship("User", back_populates="messages")
    
    # Индексы
    __table_args__ = (
        # Индекс для быстрого поиска сообщений по conversation_id
        Index("idx_conversation_id", "conversation_id"),
        # Индекс для быстрого поиска сообщений по sender_id
        Index("idx_sender_id", "sender_id"),
    )