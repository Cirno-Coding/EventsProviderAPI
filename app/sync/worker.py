import asyncio
import logging
from contextlib import suppress

from app.clients.events_provider import EventsProviderClient
from app.core.config import Settings
from app.core.database import async_session_maker
from app.repositories.events import EventRepository
from app.repositories.sync_metadata import SyncMetadataRepository
from app.sync.paginator import EventsPaginator
from app.usecases.sync_events import SyncEventsUseCase

logger = logging.getLogger(__name__)


async def run_sync_once(settings: Settings) -> None:
    async with async_session_maker() as session:
        client = EventsProviderClient(
            base_url=settings.events_provider_base_url,
            api_key=settings.events_provider_api_key,
        )

        events = EventRepository(session)
        metadata = SyncMetadataRepository(session)

        try:
            await metadata.mark_running()
            await session.commit()

            usecase = SyncEventsUseCase(
                repository=events,
                metadata_repository=metadata,
                paginator_factory=lambda changed_at: EventsPaginator(
                    client=client,
                    changed_at=changed_at,
                ),
            )

            last_changed_at = await usecase.execute()

            await metadata.mark_success(last_changed_at=last_changed_at)
            await session.commit()

            logger.info("Events sync completed successfully")

        except Exception as exc:
            await session.rollback()

            await metadata.mark_failed(error_message=str(exc))
            await session.commit()

            logger.exception("Events sync failed")

        finally:
            await client.close()


async def sync_loop(settings: Settings) -> None:
    while True:
        await run_sync_once(settings)
        await asyncio.sleep(settings.sync_interval_seconds)


def start_background_sync(settings: Settings) -> asyncio.Task:
    return asyncio.create_task(sync_loop(settings))


async def stop_background_sync(task: asyncio.Task) -> None:
    task.cancel()

    with suppress(asyncio.CancelledError):
        await task