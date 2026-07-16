import hashlib
import json
from uuid import UUID

from app.clients.events_provider import EventsProviderClient
from app.db.models import EventStatus, OutboxEventType
from app.repositories.events import EventRepository
from app.repositories.outbox import OutboxRepository
from app.repositories.ticket_idempotency import TicketIdempotencyRepository
from app.repositories.tickets import TicketRepository


class EventNotFound(Exception):
    pass


class EventUnexpectedStatus(Exception):
    pass


class IdempotencyConflict(Exception):
    pass


def build_request_fingerprint(
    *,
    event_id: UUID,
    first_name: str,
    last_name: str,
    email: str,
    seat: str,
) -> str:
    payload = {
        "email": email,
        "event_id": str(event_id),
        "first_name": first_name,
        "last_name": last_name,
        "seat": seat,
    }
    serialized_payload = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(serialized_payload.encode("utf-8")).hexdigest()


class CreateTicketUseCase:
    def __init__(
        self,
        events: EventRepository,
        tickets: TicketRepository,
        outbox: OutboxRepository,
        idempotency: TicketIdempotencyRepository,
        client: EventsProviderClient,
    ) -> None:
        self.events = events
        self.tickets = tickets
        self.outbox = outbox
        self.idempotency = idempotency
        self.client = client

    async def execute(
        self,
        *,
        event_id: UUID,
        first_name: str,
        last_name: str,
        email: str,
        seat: str,
        idempotency_key: str | None,
        idempotency_ttl_seconds: int,
    ) -> UUID:
        request_fingerprint: str | None = None
        if idempotency_key is not None:
            request_fingerprint = build_request_fingerprint(
                event_id=event_id,
                first_name=first_name,
                last_name=last_name,
                email=email,
                seat=seat,
            )
            await self.idempotency.acquire_lock(idempotency_key)
            await self.idempotency.delete_expired()
            existing_record = await self.idempotency.get_by_key(idempotency_key)

            if existing_record is not None:
                if existing_record.request_fingerprint != request_fingerprint:
                    raise IdempotencyConflict
                return existing_record.ticket_id

        event = await self.events.get_by_id(event_id)

        if event is None:
            raise EventNotFound

        if event.status != EventStatus.published.value:
            raise EventUnexpectedStatus

        ticket_id = UUID(
            await self.client.register(
                event_id=str(event.id),
                first_name=first_name,
                last_name=last_name,
                email=email,
                seat=seat,
            ),
        )

        await self.tickets.create(
            ticket_id=ticket_id,
            event_id=event.id,
            first_name=first_name,
            last_name=last_name,
            email=email,
            seat=seat,
        )
        await self.outbox.create(
            event_type=OutboxEventType.ticket_purchased.value,
            payload={
                "ticket_id": str(ticket_id),
                "event_id": str(event.id),
                "event_name": event.name,
                "event_time": event.event_time.isoformat(),
                "seat": seat,
            },
        )

        if idempotency_key is not None and request_fingerprint is not None:
            await self.idempotency.create(
                idempotency_key=idempotency_key,
                request_fingerprint=request_fingerprint,
                ticket_id=ticket_id,
                ttl_seconds=idempotency_ttl_seconds,
            )

        return ticket_id
