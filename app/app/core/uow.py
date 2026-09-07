"""Unit of work for centralized transactions handle"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio.session import async_sessionmaker

from app.repositories.conversation_repo import ConversationRepository
from app.repositories.user_repo import UserRepository
from app.repositories.message_repo import MessageRepository

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator


class UnitOfWork:
    """Basic unit of work for sessions"""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self.session_factory: async_sessionmaker[AsyncSession] = session_factory
        self.session: AsyncSession | None = None

    async def __aenter__(self):
        self.session = self.session_factory()

        self.users = UserRepository(self.session)
        self.message = MessageRepository(self.session)
        self.conversation = ConversationRepository(self.session)

        return self

    async def __aexit__(self, exc_type, exc, tb):
        try:
            if exc_type is not None:
                await self.session.rollback()
            else:
                await self.session.commit()

        finally:
            await self.session.close()


@asynccontextmanager
async def unit_of_work(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[UnitOfWork]:
    async with UnitOfWork(session_factory) as uow:
        yield uow
