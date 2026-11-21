"""Overlap service main.py, builds FastAPI app, connectes the startip logic and middleware,
and exposes a health endpoint."""

import logging
import sys
from collections.abc import Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import db, migrations
from app.config import Settings
from app.contacts_client import ContactsClient, ContactsUnavailable
from app.demo_user import DEMO_USER
from app.logging_middleware import RequestLogMiddleware
from app.routes import router as suggestions_router
from app.windows import Person

# Root login
logging.basicConfig(
    level=logging.INFO, stream=sys.stdout, format="%(asctime)s %(levelname)s %(name)s %(message)s"
)
logger = logging.getLogger("overlap")


def create_app(
    settings: Settings | None = None,
    contacts: ContactsClient | None = None,
    clock: Callable[[], datetime] | None = None,
    user: Person | None = None,
) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if settings.run_migrations and settings.db_configured:
            applied = migrations.run_with_retry(lambda: db.connect(settings))
            logger.info("migrations applied: %s", applied or "none (up to date)")
        else:
            logger.info("skipping migrations (disabled or database not configured)")
        yield

    app = FastAPI(title="overlap-service", version="0.2.0", lifespan=lifespan)
    app.state.contacts = contacts or ContactsClient(
        settings.contacts_service_url, settings.contacts_timeout_s
    )
    app.state.clock = clock or (lambda: datetime.now(UTC))
    app.state.user = user or DEMO_USER
    app.add_middleware(RequestLogMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET"],
        allow_headers=["Content-Type"],
    )

    @app.exception_handler(ContactsUnavailable)
    async def contacts_unavailable(request: Request, exc: ContactsUnavailable):
        # A clear message instead of a stack trace when contacts-service is down or slow.
        logger.warning("contacts-service unavailable: %s", exc)
        return JSONResponse(
            status_code=503,
            content={"detail": "contacts-service is unavailable, suggestions are not available"},
        )

    @app.get("/health")
    def health():
        # Deliberately independent of contacts-service and Nager.Date, so a
        # dependency outage never makes this service look dead to the pipeline.
        return {"status": "ok", "service": "overlap-service"}

    app.include_router(suggestions_router)
    return app


app = create_app()