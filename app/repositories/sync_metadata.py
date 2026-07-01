from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import SyncMetadata, SyncStatus

SYNC_METADATA_ID = 1


class SyncMetadataRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_create(self) -> SyncMetadata:
        result = await self._session.execute(
            select(SyncMetadata).where(SyncMetadata.id == SYNC_METADATA_ID),
        )
        metadata = result.scalar_one_or_none()

        if metadata is None:
            metadata = SyncMetadata(
                id=SYNC_METADATA_ID,
                last_sync_time=None,
                last_changed_at=None,
                sync_status=SyncStatus.success.value,
                error_message=None,
            )
            self._session.add(metadata)
            await self._session.flush()

        return metadata

    async def mark_running(self) -> SyncMetadata:
        metadata = await self.get_or_create()
        metadata.sync_status = SyncStatus.running.value
        metadata.error_message = None
        return metadata

    async def mark_success(self, *, last_changed_at: datetime | None) -> SyncMetadata:
        metadata = await self.get_or_create()
        metadata.sync_status = SyncStatus.success.value
        metadata.last_sync_time = datetime.now(timezone.utc)

        if last_changed_at is not None:
            metadata.last_changed_at = last_changed_at

        metadata.error_message = None
        return metadata

    async def mark_failed(self, *, error_message: str) -> SyncMetadata:
        metadata = await self.get_or_create()
        metadata.sync_status = SyncStatus.failed.value
        metadata.last_sync_time = datetime.now(timezone.utc)
        metadata.error_message = error_message
        return metadata