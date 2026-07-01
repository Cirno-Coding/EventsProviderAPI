from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.events_provider import EventsProviderClient
from app.dependencies import (
    get_db_session,
    get_event_repository,
    get_events_provider_client,
    get_sync_metadata_repository,
)
from app.repositories.events import EventRepository
from app.repositories.sync_metadata import SyncMetadataRepository
from app.schemas.sync import SyncTriggerResponse
from app.sync.paginator import EventsPaginator
from app.usecases.sync_events import SyncEventsUseCase

router = APIRouter(prefix="/api/sync", tags=["sync"])


@router.post("/trigger", response_model=SyncTriggerResponse)
async def trigger_sync(
    session: AsyncSession = Depends(get_db_session),
    events: EventRepository = Depends(get_event_repository),
    metadata: SyncMetadataRepository = Depends(get_sync_metadata_repository),
    client: EventsProviderClient = Depends(get_events_provider_client),
) -> SyncTriggerResponse:
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

    try:
        last_changed_at = await usecase.execute()

        sync_metadata = await metadata.mark_success(last_changed_at=last_changed_at)
        await session.commit()

        return SyncTriggerResponse(
            status=sync_metadata.sync_status,
            last_sync_time=sync_metadata.last_sync_time,
            last_changed_at=sync_metadata.last_changed_at,
            error_message=sync_metadata.error_message,
        )

    except Exception as exc:
        await session.rollback()

        sync_metadata = await metadata.mark_failed(error_message=str(exc))
        await session.commit()

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Sync failed",
        ) from exc