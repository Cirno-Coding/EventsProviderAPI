from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.seats import seats_cache
from app.cache.ttl import TTLCache
from app.clients.events_provider import EventsProviderClient
from app.core.config import Settings, get_settings
from app.core.database import get_async_session
from app.repositories.events import EventRepository
from app.repositories.outbox import OutboxRepository
from app.repositories.sync_metadata import SyncMetadataRepository
from app.repositories.tickets import TicketRepository


def get_app_settings() -> Settings:
    return get_settings()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_async_session():
        yield session


def get_event_repository(
    session: AsyncSession = Depends(get_db_session),
) -> EventRepository:
    return EventRepository(session)


def get_ticket_repository(
    session: AsyncSession = Depends(get_db_session),
) -> TicketRepository:
    return TicketRepository(session)


def get_outbox_repository(
    session: AsyncSession = Depends(get_db_session),
) -> OutboxRepository:
    return OutboxRepository(session)


def get_sync_metadata_repository(
    session: AsyncSession = Depends(get_db_session),
) -> SyncMetadataRepository:
    return SyncMetadataRepository(session)


async def get_events_provider_client(
    settings: Settings = Depends(get_app_settings),
) -> AsyncGenerator[EventsProviderClient, None]:
    client = EventsProviderClient(
        base_url=settings.events_provider_base_url,
        api_key=settings.events_provider_api_key,
    )

    try:
        yield client
    finally:
        await client.close()


def get_seats_cache() -> TTLCache[list[str]]:
    return seats_cache
