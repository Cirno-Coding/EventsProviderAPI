from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from app.clients.events_provider import EventsProviderError
from app.db.models import EventStatus, OutboxEventType
from app.usecases.create_ticket import CreateTicketUseCase


class FakeEventsRepository:
    def __init__(self, event: SimpleNamespace | None) -> None:
        self.event = event

    async def get_by_id(self, event_id: UUID) -> SimpleNamespace | None:
        return self.event


class FakeTicketsRepository:
    def __init__(self) -> None:
        self.created: list[dict[str, object]] = []

    async def create(self, **kwargs: object) -> None:
        self.created.append(kwargs)


class FakeOutboxRepository:
    def __init__(self) -> None:
        self.created: list[dict[str, object]] = []

    async def create(self, **kwargs: object) -> None:
        self.created.append(kwargs)


class FakeEventsProviderClient:
    def __init__(self, ticket_id: UUID) -> None:
        self.ticket_id = ticket_id
        self.calls: list[dict[str, str]] = []

    async def register(self, **kwargs: str) -> str:
        self.calls.append(kwargs)
        return str(self.ticket_id)


class FailingEventsProviderClient:
    async def register(self, **kwargs: str) -> str:
        raise EventsProviderError("Events Provider is unavailable")


@pytest.mark.asyncio
async def test_creates_outbox_event_with_ticket() -> None:
    event_id = uuid4()
    ticket_id = uuid4()
    event = SimpleNamespace(
        id=event_id,
        name="Python meetup",
        event_time=datetime(2026, 8, 1, 18, 0, tzinfo=timezone.utc),
        status=EventStatus.published.value,
    )
    tickets = FakeTicketsRepository()
    outbox = FakeOutboxRepository()
    client = FakeEventsProviderClient(ticket_id)
    usecase = CreateTicketUseCase(
        events=FakeEventsRepository(event),
        tickets=tickets,
        outbox=outbox,
        client=client,
    )

    result = await usecase.execute(
        event_id=event_id,
        first_name="Ada",
        last_name="Lovelace",
        email="ada@example.com",
        seat="A-1",
    )

    assert result == ticket_id
    assert len(tickets.created) == 1
    assert outbox.created == [
        {
            "event_type": OutboxEventType.ticket_purchased.value,
            "payload": {
                "ticket_id": str(ticket_id),
                "event_id": str(event_id),
                "event_name": "Python meetup",
                "event_time": "2026-08-01T18:00:00+00:00",
                "seat": "A-1",
            },
        },
    ]


@pytest.mark.asyncio
async def test_does_not_create_ticket_or_outbox_event_after_provider_error() -> None:
    event = SimpleNamespace(
        id=uuid4(),
        name="Python meetup",
        event_time=datetime(2026, 8, 1, 18, 0, tzinfo=timezone.utc),
        status=EventStatus.published.value,
    )
    tickets = FakeTicketsRepository()
    outbox = FakeOutboxRepository()
    usecase = CreateTicketUseCase(
        events=FakeEventsRepository(event),
        tickets=tickets,
        outbox=outbox,
        client=FailingEventsProviderClient(),
    )

    with pytest.raises(EventsProviderError):
        await usecase.execute(
            event_id=event.id,
            first_name="Ada",
            last_name="Lovelace",
            email="ada@example.com",
            seat="A-1",
        )

    assert tickets.created == []
    assert outbox.created == []
