from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sentry_sdk.integrations.fastapi import FastApiIntegration

from app.api.events import router as events_router
from app.api.health import router as health_router
from app.api.sync import router as sync_router
from app.api.tickets import router as tickets_router
from app.clients.capashino import CapashinoClient
from app.core.config import get_settings
from app.core.database import async_session_maker
from app.outbox.handlers import CapashinoOutboxHandler
from app.outbox.worker import (
    OutboxWorker,
    start_background_outbox,
    stop_background_outbox,
)
from app.sync.worker import start_background_sync, stop_background_sync


def configure_glitchtip() -> None:
    settings = get_settings()

    if settings.glitchtip_dsn is None:
        return

    sentry_sdk.init(
        dsn=settings.glitchtip_dsn,
        environment=settings.app_env,
        send_default_pii=False,
        integrations=[FastApiIntegration()],
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    sync_task = None
    outbox_task = None
    capashino_client = None

    try:
        if settings.enable_background_sync:
            sync_task = start_background_sync(settings)

        if settings.enable_outbox_worker:
            if settings.capashino_base_url is None or settings.capashino_api_key is None:
                raise RuntimeError(
                    "CAPASHINO_BASE_URL and CAPASHINO_API_KEY are required "
                    "when ENABLE_OUTBOX_WORKER is enabled",
                )

            capashino_client = CapashinoClient(
                base_url=settings.capashino_base_url,
                api_key=settings.capashino_api_key,
            )
            outbox_worker = OutboxWorker(
                session_factory=async_session_maker,
                handler=CapashinoOutboxHandler(capashino_client),
                batch_size=settings.outbox_batch_size,
                poll_interval_seconds=settings.outbox_poll_interval_seconds,
            )
            outbox_task = start_background_outbox(outbox_worker)

        yield
    finally:
        if outbox_task is not None:
            await stop_background_outbox(outbox_task)

        if capashino_client is not None:
            await capashino_client.close()

        if sync_task is not None:
            await stop_background_sync(sync_task)


def create_app() -> FastAPI:
    settings = get_settings()
    configure_glitchtip()

    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        lifespan=lifespan,
    )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": exc.errors()},
        )

    app.include_router(health_router)
    app.include_router(events_router)
    app.include_router(tickets_router)
    app.include_router(sync_router)

    return app


app = create_app()
