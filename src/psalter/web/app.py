from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.responses import Response

from psalter.application.errors import ApplicationError
from psalter.bootstrap import build_container
from psalter.config import AppConfig
from psalter.logging import debug_event, get_logger
from psalter.web.errors import application_error_response, validation_error_response
from psalter.web.routes.health import router as health_router
from psalter.web.routes.installation import router as installation_router
from psalter.web.routes.progress import router as progress_router
from psalter.web.routes.psalms import router as psalms_router
from psalter.web.routes.reviews import router as reviews_router
from psalter.web.routes.settings import router as settings_router

logger = get_logger(__name__)


def create_app(config: AppConfig | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        container = build_container(config)
        applied = container.migrator.apply_pending()
        app.state.container = container
        debug_event(logger, "web_app_started", applied_migrations=tuple(applied))
        yield

    app = FastAPI(title="Psalter API", version="0.1.0", lifespan=lifespan)
    app.add_exception_handler(ApplicationError, _handle_application_error)
    app.add_exception_handler(RequestValidationError, _handle_validation_error)

    @app.middleware("http")
    async def request_id_middleware(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = str(uuid4())
        request.state.request_id = request_id
        debug_event(
            logger,
            "request_started",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        debug_event(
            logger,
            "request_completed",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
        )
        return response

    app.include_router(health_router)
    app.include_router(installation_router)
    app.include_router(psalms_router)
    app.include_router(progress_router)
    app.include_router(reviews_router)
    app.include_router(settings_router)
    return app


async def _handle_application_error(request: Request, exc: Exception) -> Response:
    if isinstance(exc, ApplicationError):
        return application_error_response(request, exc)
    return application_error_response(request, ApplicationError(str(exc)))


async def _handle_validation_error(request: Request, exc: Exception) -> Response:
    if isinstance(exc, RequestValidationError):
        return validation_error_response(request, exc)
    return application_error_response(request, ApplicationError(str(exc)))
