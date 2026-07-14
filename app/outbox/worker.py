import asyncio
import logging
from collections.abc import Awaitable, Callable
from contextlib import suppress
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models import OutboxEvent
from app.repositories.outbox import OutboxRepository

logger = logging.getLogger(__name__)

OutboxEventHandler = Callable[[OutboxEvent], Awaitable[None]]


class OutboxWorker:
    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession],
        handler: OutboxEventHandler,
        batch_size: int,
        poll_interval_seconds: int,
    ) -> None:
        self._session_factory = session_factory
        self._handler = handler
        self._batch_size = batch_size
        self._poll_interval_seconds = poll_interval_seconds

    async def process_once(self) -> int:
        event_ids = await self._get_pending_ids()
        processed_count = 0

        for event_id in event_ids:
            if await self._process_event(event_id):
                processed_count += 1

        return processed_count

    async def run_forever(self) -> None:
        while True:
            try:
                await self.process_once()
            except Exception:
                logger.exception("Outbox worker iteration failed")

            await asyncio.sleep(self._poll_interval_seconds)

    async def _get_pending_ids(self) -> list[UUID]:
        async with self._session_factory() as session:
            repository = OutboxRepository(session)
            events = await repository.get_pending(limit=self._batch_size)
            return [event.id for event in events]

    async def _process_event(self, event_id: UUID) -> bool:
        async with self._session_factory() as session:
            repository = OutboxRepository(session)
            event = await repository.get_pending_by_id(event_id)

            if event is None:
                return False

            try:
                await self._handler(event)
                await repository.mark_sent(event)
                await session.commit()
            except Exception:
                await session.rollback()
                logger.exception("Outbox event processing failed: %s", event_id)
                return False

        return True


def start_background_outbox(worker: OutboxWorker) -> asyncio.Task:
    return asyncio.create_task(worker.run_forever())


async def stop_background_outbox(task: asyncio.Task) -> None:
    task.cancel()

    with suppress(asyncio.CancelledError):
        await task
