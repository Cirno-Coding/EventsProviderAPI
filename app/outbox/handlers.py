from app.clients.capashino import CapashinoClient
from app.db.models import OutboxEvent, OutboxEventType


class UnsupportedOutboxEvent(Exception):
    pass


class CapashinoOutboxHandler:
    def __init__(self, client: CapashinoClient) -> None:
        self._client = client

    async def __call__(self, event: OutboxEvent) -> None:
        if event.event_type != OutboxEventType.ticket_purchased.value:
            raise UnsupportedOutboxEvent(
                f"Unsupported outbox event: {event.event_type}",
            )

        try:
            ticket_id = str(event.payload["ticket_id"])
            event_name = str(event.payload["event_name"])
            seat = str(event.payload["seat"])
        except KeyError as exc:
            raise ValueError(
                f"Outbox event {event.id} has incomplete payload",
            ) from exc

        await self._client.create_notification(
            message=(
                f"Вы успешно зарегистрированы на мероприятие «{event_name}». "
                f"Ваше место: {seat}."
            ),
            reference_id=ticket_id,
            idempotency_key=str(event.id),
        )
