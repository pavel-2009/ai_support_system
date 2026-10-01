from unittest.mock import AsyncMock, Mock

import pytest

import app.celery.worker_db as worker_db


@pytest.fixture(autouse=True)
def reset_worker_database_state():
    worker_db._worker_engine = None
    worker_db._worker_session_factory = None
    yield
    worker_db._worker_engine = None
    worker_db._worker_session_factory = None


def test_initialize_worker_database_creates_engine_and_factory_once(monkeypatch):
    engine = Mock()
    session_factory = Mock()

    create_engine = Mock(return_value=engine)
    create_session_factory = Mock(return_value=session_factory)

    monkeypatch.setattr(worker_db, "create_database_engine", create_engine)
    monkeypatch.setattr(worker_db, "async_sessionmaker", create_session_factory)

    assert worker_db.initialize_worker_database() is session_factory
    assert worker_db.initialize_worker_database() is session_factory

    create_engine.assert_called_once_with(worker_db.settings.DATABASE_URL)
    create_session_factory.assert_called_once_with(engine, expire_on_commit=False)


@pytest.mark.asyncio
async def test_close_worker_database_disposes_engine():
    engine = Mock()
    engine.dispose = AsyncMock()
    worker_db._worker_engine = engine
    worker_db._worker_session_factory = Mock()

    await worker_db.close_worker_database()

    engine.dispose.assert_awaited_once()
    assert worker_db._worker_engine is None
    assert worker_db._worker_session_factory is None


def test_get_worker_session_factory_initializes_when_needed(monkeypatch):
    session_factory = Mock()
    initialize = Mock(return_value=session_factory)
    monkeypatch.setattr(worker_db, "initialize_worker_database", initialize)

    assert worker_db.get_worker_session_factory() is session_factory
    initialize.assert_called_once_with()
