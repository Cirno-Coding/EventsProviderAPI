from uuid import UUID

from app.clients.events_provider import EventsProviderClient
from app.db.models import EventStatus, OutboxEventType
from app.repositories.events import EventRepository
from app.repositories.outbox import OutboxRepository
from app.repositories.tickets import TicketRepository


class EventNotFound(Exception):
    pass


class EventUnexpectedStatus(Exception):
    pass


class CreateTicketUseCase:
    def __init__(
        self,
        events: EventRepository,
        tickets: TicketRepository,
        outbox: OutboxRepository,
        client: EventsProviderClient,
    ) -> None:
        self.events = events
        self.tickets = tickets
        self.outbox = outbox
        self.client = client

    async def execute(
        self,
        *,
        event_id: UUID,
        first_name: str,
        last_name: str,
        email: str,
        seat: str,
    ) -> UUID:
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

        return ticket_id
