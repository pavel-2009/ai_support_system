"""Database lifecycle for Celery worker processes.

Each prefork worker process owns exactly one AsyncEngine and one
async_sessionmaker. Tasks must create short-lived sessions from that factory.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.config import settings
from app.db import create_database_engine


_worker_engine: AsyncEngine | None = None
_worker_session_factory: async_sessionmaker[AsyncSession] | None = None


def initialize_worker_database() -> async_sessionmaker[AsyncSession]:
    """Create the database engine and session factory once per worker process."""
    global _worker_engine, _worker_session_factory

    if _worker_session_factory is not None:
        return _worker_session_factory

    _worker_engine = create_database_engine(settings.DATABASE_URL)
    _worker_session_factory = async_sessionmaker(
        _worker_engine,
        expire_on_commit=False,
    )
    return _worker_session_factory


def get_worker_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the worker-local session factory after worker initialization."""
    if _worker_session_factory is None:
        return initialize_worker_database()
    return _worker_session_factory


async def close_worker_database() -> None:
    """Dispose the worker-local engine during worker-process shutdown."""
    global _worker_engine, _worker_session_factory

    if _worker_engine is not None:
        await _worker_engine.dispose()

    _worker_engine = None
    _worker_session_factory = None
