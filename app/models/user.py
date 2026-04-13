"""SQLAlchemy модели для работы с пользователями."""

from sqlalchemy import Column, Integer, String, Enum as SqlEnum
from enum import Enum

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
