from uuid import UUID

from app.clients.events_provider import EventsProviderClient
from app.repositories.tickets import TicketRepository


class TicketNotFound(Exception):
    pass


class DeleteTicketUseCase:
    def __init__(
        self,
        repository: TicketRepository,
        client: EventsProviderClient,
    ) -> None:
        self.repository = repository
        self.client = client

    async def execute(self, ticket_id: UUID) -> None:
        ticket = await self.repository.get_by_id(ticket_id)

        if ticket is None:
            raise TicketNotFound

        await self.client.unregister(
            event_id=str(ticket.event_id),
            ticket_id=str(ticket.id),
        )

        await self.repository.delete(ticket)