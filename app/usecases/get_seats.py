from uuid import UUID

from app.cache.ttl import TTLCache
from app.clients.events_provider import EventsProviderClient
from app.db.models import EventStatus
from app.repositories.events import EventRepository


class EventNotFound(Exception):
    pass


class EventUnexpectedStatus(Exception):
    pass


class GetSeatsUseCase:
    def __init__(
        self,
        *,
        events: EventRepository,
        client: EventsProviderClient,
        cache: TTLCache[list[str]],
    ) -> None:
        self.events = events
        self.client = client
        self.cache = cache

    async def execute(self, event_id: UUID) -> list[str]:
        event = await self.events.get_by_id(event_id)

        if event is None:
            raise EventNotFound

        if event.status != EventStatus.published.value:
            raise EventUnexpectedStatus

        cache_key = str(event_id)
        cached_seats = self.cache.get(cache_key)

        if cached_seats is not None:
            return cached_seats

        seats = await self.client.get_available_seats(str(event_id))
        self.cache.set(cache_key, seats)

        return seats