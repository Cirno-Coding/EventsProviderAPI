from uuid import UUID

from app.repositories.events import EventRepository


class GetEventUseCase:
    def __init__(self, repository: EventRepository) -> None:
        self.repository = repository

    async def execute(self, event_id: UUID):
        return await self.repository.get_by_id(event_id)