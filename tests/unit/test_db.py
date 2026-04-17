"""Minimal tests for app/db.py"""
import pytest


class TestDatabaseConnection:
    """Basic database connection tests."""

    def test_base_exists(self):
        """Test Base is initialized."""
        from app.db import Base
        assert Base is not None
        assert hasattr(Base, 'metadata')

    def test_engine_exists(self):
        """Test engine is initialized."""
        from app.db import engine
        assert engine is not None

    @pytest.mark.asyncio
    async def test_async_session_factory_exists(self):
        """Test async_session factory exists."""
        from app.db import async_session
        assert async_session is not None

    @pytest.mark.asyncio
    async def test_get_async_session(self):
        """Test get_async_session generator."""
        from app.db import get_async_session
        async for session in get_async_session():
            assert session is not None
            break
