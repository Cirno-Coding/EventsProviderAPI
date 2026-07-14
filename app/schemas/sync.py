from datetime import datetime

from pydantic import BaseModel


class SyncTriggerResponse(BaseModel):
    status: str
    last_sync_time: datetime | None = None
    last_changed_at: datetime | None = None
    error_message: str | None = None
