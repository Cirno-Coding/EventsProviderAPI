from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import OutboxEvent, OutboxStatus


class OutboxRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        event_type: str,
        payload: dict[str, Any],
    ) -> OutboxEvent:
        event = OutboxEvent(
            id=uuid4(),
            event_type=event_type,
            payload=payload,
            status=OutboxStatus.pending.value,
            created_at=datetime.now(timezone.utc),
            sent_at=None,
        )
        self._session.add(event)
        return event

    async def get_pending(self, *, limit: int) -> list[OutboxEvent]:
        result = await self._session.execute(
            select(OutboxEvent)
            .where(OutboxEvent.status == OutboxStatus.pending.value)
            .order_by(OutboxEvent.created_at.asc(), OutboxEvent.id.asc())
            .limit(limit),
        )
        return list(result.scalars().all())

    async def get_pending_by_id(self, event_id: UUID) -> OutboxEvent | None:
        result = await self._session.execute(
            select(OutboxEvent).where(
                OutboxEvent.id == event_id,
                OutboxEvent.status == OutboxStatus.pending.value,
            ),
        )
        return result.scalar_one_or_none()

    async def mark_sent(self, event: OutboxEvent) -> None:
        event.status = OutboxStatus.sent.value
        event.sent_at = datetime.now(timezone.utc)
