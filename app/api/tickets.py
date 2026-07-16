from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.events_provider import (
    EventsProviderBadRequestError,
    EventsProviderClient,
    EventsProviderError,
    EventsProviderNotFoundError,
)
from app.core.config import Settings
from app.dependencies import (
    get_app_settings,
    get_db_session,
    get_event_repository,
    get_events_provider_client,
    get_outbox_repository,
    get_ticket_idempotency_repository,
    get_ticket_repository,
)
from app.repositories.events import EventRepository
from app.repositories.outbox import OutboxRepository
from app.repositories.ticket_idempotency import TicketIdempotencyRepository
from app.repositories.tickets import TicketRepository
from app.schemas.tickets import (
    CreateTicketRequest,
    CreateTicketResponse,
    DeleteTicketResponse,
)
from app.usecases.create_ticket import (
    CreateTicketUseCase,
    EventNotFound,
    EventUnexpectedStatus,
    IdempotencyConflict,
)
from app.usecases.delete_ticket import DeleteTicketUseCase, TicketNotFound

router = APIRouter(prefix="/api/tickets", tags=["tickets"])


@router.post(
    "",
    response_model=CreateTicketResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_409_CONFLICT: {
            "description": "Idempotency key was already used with different request data",
        },
    },
)
async def create_ticket(
    data: CreateTicketRequest,
    session: AsyncSession = Depends(get_db_session),
    events: EventRepository = Depends(get_event_repository),
    tickets: TicketRepository = Depends(get_ticket_repository),
    outbox: OutboxRepository = Depends(get_outbox_repository),
    idempotency: TicketIdempotencyRepository = Depends(get_ticket_idempotency_repository),
    client: EventsProviderClient = Depends(get_events_provider_client),
    settings: Settings = Depends(get_app_settings),
) -> CreateTicketResponse:
    usecase = CreateTicketUseCase(
        events=events,
        tickets=tickets,
        outbox=outbox,
        idempotency=idempotency,
        client=client,
    )

    try:
        ticket_id = await usecase.execute(
            event_id=data.event_id,
            first_name=data.first_name,
            last_name=data.last_name,
            email=str(data.email),
            seat=data.seat,
            idempotency_key=data.idempotency_key,
            idempotency_ttl_seconds=settings.idempotency_key_ttl_seconds,
        )
        await session.commit()
    except EventNotFound:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        ) from None
    except EventUnexpectedStatus:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Event is not published",
        ) from None
    except IdempotencyConflict:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Idempotency key was already used with different request data",
        ) from None
    except EventsProviderBadRequestError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from None
    except EventsProviderNotFoundError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found in provider",
        ) from None
    except EventsProviderError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from None

    return CreateTicketResponse(ticket_id=ticket_id)


@router.delete("/{ticket_id}", response_model=DeleteTicketResponse)
async def delete_ticket(
    ticket_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    tickets: TicketRepository = Depends(get_ticket_repository),
    client: EventsProviderClient = Depends(get_events_provider_client),
) -> DeleteTicketResponse:
    usecase = DeleteTicketUseCase(
        repository=tickets,
        client=client,
    )

    try:
        await usecase.execute(ticket_id)
        await session.commit()
    except TicketNotFound:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        ) from None
    except EventsProviderNotFoundError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registration not found in provider",
        ) from None
    except EventsProviderBadRequestError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from None
    except EventsProviderError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from None

    return DeleteTicketResponse(success=True)
