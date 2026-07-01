from datetime import date

from app.repositories.events import EventRepository


class GetEventsUseCase:
    def __init__(self, repository: EventRepository) -> None:
        self.repository = repository

    async def execute(
        self,
        *,
        date_from: date | None,
        page: int,
        page_size: int,
    ):
        return await self.repository.list(
            date_from=date_from,
            page=page,
            page_size=page_size,
        )