import asyncio

from fastapi import APIRouter, Depends, status

from app.core.config import Settings
from app.dependencies import get_app_settings
from app.schemas.sync import SyncTriggerResponse
from app.sync.worker import run_sync_once

router = APIRouter(prefix="/api/sync", tags=["sync"])


@router.post(
    "/trigger",
    response_model=SyncTriggerResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def trigger_sync(
    settings: Settings = Depends(get_app_settings),
) -> SyncTriggerResponse:
    asyncio.create_task(run_sync_once(settings))

    return SyncTriggerResponse(
        status="accepted",
        last_sync_time=None,
        last_changed_at=None,
        error_message=None,
    )
