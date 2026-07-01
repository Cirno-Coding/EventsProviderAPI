from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.events import router as events_router
from app.api.health import router as health_router
from app.api.sync import router as sync_router
from app.api.tickets import router as tickets_router
from app.core.config import get_settings
from app.sync.worker import start_background_sync, stop_background_sync


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    sync_task = None

    if settings.enable_background_sync:
        sync_task = start_background_sync(settings)

    try:
        yield
    finally:
        if sync_task is not None:
            await stop_background_sync(sync_task)


def create_app() -> FastAPI:
    settings = get_settings()

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