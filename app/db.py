"""Соединение с базой данных."""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from typing import AsyncGenerator
from app.core.config import settings

# Создаем асинхронный движок для подключения к базе данных SQLite
Base = declarative_base()

# Инициализация базы данных
engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)

# Создаем асинхронную сессию для работы с базой данных
async_session = sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)

# Генератор для получения асинхронной сессии базы данных
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Генератор для получения асинхронной сессии базы данных."""
    async with async_session() as session:
        yield session
