"""Unit of work for centralized transaction handling."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.event_bus import event_bus
from app.core.logging import get_logger
from app.domain.events import DomainEvent
from app.repositories.conversation_repo import ConversationRepository
from app.repositories.message_repo import MessageRepository
from app.repositories.user_repo import UserRepository


logger = get_logger(__name__)


class UnitOfWork:
    """Basic unit of work for sessions."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self.session_factory = session_factory
        self.session: AsyncSession | None = None
        self._events: list[DomainEvent] = []

    def add_event(self, event: DomainEvent) -> None:
        """Поставить событие в очередь до успешного завершения транзакции."""
        self._events.append(event)

    async def __aenter__(self):
        self.session = self.session_factory()
        self.users = UserRepository(self.session)
        self.message = MessageRepository(self.session)
        self.conversation = ConversationRepository(self.session)
        logger.debug("DB UOW OPEN: session_id=%s", id(self.session))
        return self

    async def __aexit__(self, exc_type, exc, tb):
        try:
            if exc_type is not None:
                logger.error(
                    "DB TRANSACTION ROLLBACK: session_id=%s exception=%s",
                    id(self.session),
                    exc,
                )
                await self.session.rollback()
            else:
                logger.debug("DB TRANSACTION COMMIT START: session_id=%s", id(self.session))
                await self.session.commit()
                logger.debug("DB TRANSACTION COMMIT OK: session_id=%s", id(self.session))
                for event in self._events:
                    await event_bus.publish_async(event)
        except Exception:
            logger.exception("DB TRANSACTION FINALIZATION FAILED: session_id=%s", id(self.session))
            raise
        finally:
            await self.session.close()
            logger.debug("DB UOW CLOSE: session_id=%s", id(self.session))


@asynccontextmanager
async def unit_of_work(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[UnitOfWork]:
    async with UnitOfWork(session_factory) as uow:
        yield uow
