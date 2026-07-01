from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.cache.ttl import TTLCache
from app.clients.events_provider import EventsProviderClient
from app.dependencies import (
    get_event_repository,
    get_events_provider_client,
    get_seats_cache,
)
from app.repositories.events import EventRepository
from app.schemas.events import (
    EventDetailResponse,
    EventListItemResponse,
    EventListResponse,
    SeatsResponse,
)
from app.usecases.get_event import GetEventUseCase
from app.usecases.get_events import GetEventsUseCase
from app.usecases.get_seats import (
    EventNotFound as SeatsEventNotFound,
)
from app.usecases.get_seats import (
    EventUnexpectedStatus as SeatsEventUnexpectedStatus,
)
from app.usecases.get_seats import GetSeatsUseCase

router = APIRouter(prefix="/api/events", tags=["events"])


@router.get("", response_model=EventListResponse)
async def list_events(
    request: Request,
    date_from: date | None = None,
    page: int = 1,
    page_size: int = 20,
    repository: EventRepository = Depends(get_event_repository),
) -> EventListResponse:
    if page < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="page must be greater than or equal to 1",
        )

    if page_size < 1 or page_size > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="page_size must be between 1 and 100",
        )

    usecase = GetEventsUseCase(repository)
    count, events = await usecase.execute(
        date_from=date_from,
        page=page,
        page_size=page_size,
    )

    next_url = None
    previous_url = None

    if page * page_size < count:
        next_url = str(request.url.include_query_params(page=page + 1))

    if page > 1:
        previous_url = str(request.url.include_query_params(page=page - 1))

    return EventListResponse(
        count=count,
        next=next_url,
        previous=previous_url,
        results=[EventListItemResponse.model_validate(event) for event in events],
    )


@router.get("/{event_id}", response_model=EventDetailResponse)
async def get_event(
    event_id: UUID,
    repository: EventRepository = Depends(get_event_repository),
) -> EventDetailResponse:
    usecase = GetEventUseCase(repository)
    event = await usecase.execute(event_id)

    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )

    return EventDetailResponse.model_validate(event)


@router.get("/{event_id}/seats", response_model=SeatsResponse)
async def get_event_seats(
    event_id: UUID,
    repository: EventRepository = Depends(get_event_repository),
    client: EventsProviderClient = Depends(get_events_provider_client),
    cache: TTLCache[list[str]] = Depends(get_seats_cache),
) -> SeatsResponse:
    usecase = GetSeatsUseCase(
        events=repository,
        client=client,
        cache=cache,
    )

    try:
        seats = await usecase.execute(event_id)
    except SeatsEventNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        ) from None
    except SeatsEventUnexpectedStatus:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Event is not published",
        ) from None

    return SeatsResponse(
        event_id=event_id,
        available_seats=seats,
    )