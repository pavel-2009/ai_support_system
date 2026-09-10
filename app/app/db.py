"""Соединение с базой данных."""

import time
from typing import AsyncGenerator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings
from app.core.logging import get_logger


logger = get_logger(__name__)
Base = declarative_base()


def create_database_engine(database_url: str) -> AsyncEngine:
    """Создать async engine с диагностикой SQL-запросов."""
    database_engine = create_async_engine(database_url, pool_pre_ping=True)

    @event.listens_for(database_engine.sync_engine, "before_cursor_execute")
    def _before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        context._query_start_time = time.perf_counter()
        logger.debug("DB SQL START: %s", statement.strip())

    @event.listens_for(database_engine.sync_engine, "after_cursor_execute")
    def _after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        elapsed_ms = (time.perf_counter() - context._query_start_time) * 1000
        logger.debug(
            "DB SQL END: %.2f ms rowcount=%s sql=%s",
            elapsed_ms,
            cursor.rowcount,
            statement.strip(),
        )

    @event.listens_for(database_engine.sync_engine, "handle_error")
    def _handle_db_error(exception_context):
        logger.error(
            "DB SQL ERROR: statement=%s original=%s",
            exception_context.statement,
            exception_context.original_exception,
        )

    return database_engine


engine = create_database_engine(settings.DATABASE_URL)
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Генератор для получения асинхронной сессии базы данных."""
    async with async_session() as session:
        logger.debug("DB SESSION OPEN: id=%s", id(session))
        try:
            yield session
        finally:
            logger.debug("DB SESSION CLOSE: id=%s", id(session))
