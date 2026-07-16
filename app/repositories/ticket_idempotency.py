from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import TicketIdempotencyKey


class TicketIdempotencyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def acquire_lock(self, idempotency_key: str) -> None:
        await self._session.execute(
            text(
                "SELECT pg_advisory_xact_lock(hashtext(:idempotency_key))",
            ),
            {"idempotency_key": idempotency_key},
        )

    async def delete_expired(self) -> None:
        await self._session.execute(
            delete(TicketIdempotencyKey).where(
                TicketIdempotencyKey.expires_at <= datetime.now(timezone.utc),
            ),
        )

    async def get_by_key(
        self,
        idempotency_key: str,
    ) -> TicketIdempotencyKey | None:
        result = await self._session.execute(
            select(TicketIdempotencyKey).where(
                TicketIdempotencyKey.idempotency_key == idempotency_key,
            ),
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        idempotency_key: str,
        request_fingerprint: str,
        ticket_id: UUID,
        ttl_seconds: int,
    ) -> TicketIdempotencyKey:
        now = datetime.now(timezone.utc)
        record = TicketIdempotencyKey(
            idempotency_key=idempotency_key,
            request_fingerprint=request_fingerprint,
            ticket_id=ticket_id,
            created_at=now,
            expires_at=now + timedelta(seconds=ttl_seconds),
        )
        self._session.add(record)
        return record
