from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from app.db.models import OutboxStatus
from app.outbox.worker import OutboxWorker


class FakeSession:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


class FakeSessionContext:
    def __init__(self, session: FakeSession) -> None:
        self.session = session

    async def __aenter__(self) -> FakeSession:
        return self.session

    async def __aexit__(self, *args: object) -> None:
        return None


class FakeSessionFactory:
    def __init__(self) -> None:
        self.sessions: list[FakeSession] = []

    def __call__(self) -> FakeSessionContext:
        session = FakeSession()
        self.sessions.append(session)
        return FakeSessionContext(session)


class FakeOutboxRepository:
    events: dict[UUID, SimpleNamespace] = {}

    def __init__(self, session: FakeSession) -> None:
        self.session = session

    async def get_pending(self, *, limit: int) -> list[SimpleNamespace]:
        return [
            event for event in self.events.values() if event.status == OutboxStatus.pending.value
        ][:limit]

    async def get_pending_by_id(self, event_id: UUID) -> SimpleNamespace | None:
        event = self.events.get(event_id)
        if event is None or event.status != OutboxStatus.pending.value:
            return None
        return event

    async def mark_sent(self, event: SimpleNamespace) -> None:
        event.status = OutboxStatus.sent.value


@pytest.mark.asyncio
async def test_worker_marks_event_sent_only_after_handler_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.outbox import worker as worker_module

    event_id = uuid4()
    FakeOutboxRepository.events = {
        event_id: SimpleNamespace(id=event_id, status=OutboxStatus.pending.value),
    }
    monkeypatch.setattr(worker_module, "OutboxRepository", FakeOutboxRepository)
    handled_event_ids: list[UUID] = []

    async def handler(event: SimpleNamespace) -> None:
        handled_event_ids.append(event.id)

    session_factory = FakeSessionFactory()
    worker = OutboxWorker(
        session_factory=session_factory,
        handler=handler,
        batch_size=10,
        poll_interval_seconds=1,
    )

    processed = await worker.process_once()

    assert processed == 1
    assert handled_event_ids == [event_id]
    assert FakeOutboxRepository.events[event_id].status == OutboxStatus.sent.value
    assert sum(session.commits for session in session_factory.sessions) == 1


@pytest.mark.asyncio
async def test_worker_keeps_event_pending_when_handler_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.outbox import worker as worker_module

    event_id = uuid4()
    FakeOutboxRepository.events = {
        event_id: SimpleNamespace(id=event_id, status=OutboxStatus.pending.value),
    }
    monkeypatch.setattr(worker_module, "OutboxRepository", FakeOutboxRepository)

    async def handler(event: SimpleNamespace) -> None:
        raise RuntimeError("Notification service is unavailable")

    session_factory = FakeSessionFactory()
    worker = OutboxWorker(
        session_factory=session_factory,
        handler=handler,
        batch_size=10,
        poll_interval_seconds=1,
    )

    processed = await worker.process_once()

    assert processed == 0
    assert FakeOutboxRepository.events[event_id].status == OutboxStatus.pending.value
    assert sum(session.rollbacks for session in session_factory.sessions) == 1
