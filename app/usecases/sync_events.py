from datetime import datetime

from app.repositories.events import EventRepository
from app.repositories.sync_metadata import SyncMetadataRepository


class SyncEventsUseCase:
    FIRST_SYNC_DATE = "2000-01-01"

    def __init__(
        self,
        repository: EventRepository,
        metadata_repository: SyncMetadataRepository,
        paginator_factory,
    ) -> None:
        self.repository = repository
        self.metadata_repository = metadata_repository
        self.paginator_factory = paginator_factory

    async def execute(self) -> datetime | None:
        metadata = await self.metadata_repository.get_or_create()

        if metadata.last_changed_at is None:
            changed_at = self.FIRST_SYNC_DATE
        else:
            changed_at = metadata.last_changed_at.date().isoformat()

        paginator = self.paginator_factory(changed_at)

        last_changed_at: datetime | None = metadata.last_changed_at

        async for event in paginator:
            await self.repository.upsert_event_with_place(event)

            event_changed_at = datetime.fromisoformat(event["changed_at"])

            if last_changed_at is None or event_changed_at > last_changed_at:
                last_changed_at = event_changed_at

        return last_changed_at
