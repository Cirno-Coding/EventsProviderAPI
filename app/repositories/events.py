from datetime import date
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Event, Place


class EventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, event_id: UUID) -> Event | None:
        result = await self._session.execute(
            select(Event)
            .options(selectinload(Event.place))
            .where(Event.id == event_id),
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        *,
        date_from: date | None,
        page: int,
        page_size: int,
    ) -> tuple[int, list[Event]]:
        query = select(Event).options(selectinload(Event.place))
        count_query = select(func.count()).select_from(Event)

        if date_from is not None:
            query = query.where(func.date(Event.event_time) >= date_from)
            count_query = count_query.where(func.date(Event.event_time) >= date_from)

        query = (
            query.order_by(Event.event_time.asc(), Event.id.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        total_result = await self._session.execute(count_query)
        total = total_result.scalar_one()

        events_result = await self._session.execute(query)
        events = list(events_result.scalars().all())

        return total, events

    async def upsert_event_with_place(self, event_data: dict) -> None:
        place_data = event_data["place"]

        place = Place(
            id=place_data["id"],
            name=place_data["name"],
            city=place_data["city"],
            address=place_data["address"],
            seats_pattern=place_data["seats_pattern"],
            changed_at=place_data["changed_at"],
            created_at=place_data["created_at"],
        )

        event = Event(
            id=event_data["id"],
            name=event_data["name"],
            place_id=place_data["id"],
            event_time=event_data["event_time"],
            registration_deadline=event_data["registration_deadline"],
            status=event_data["status"],
            number_of_visitors=event_data["number_of_visitors"],
            changed_at=event_data["changed_at"],
            created_at=event_data["created_at"],
            status_changed_at=event_data["status_changed_at"],
        )

        await self._session.merge(place)
        await self._session.merge(event)