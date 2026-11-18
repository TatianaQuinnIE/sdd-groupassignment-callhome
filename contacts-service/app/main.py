"""contacts-service: contacts, call log and availability for the Calling-home planner."""

import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import db, migrations
from app.config import Settings
from app.logging_middleware import RequestLogMiddleware
from app.repository import ContactsRepository, DatabaseUnavailable, SqlContactsRepository
from app.routes import router as contacts_router

logging.basicConfig(
    level=logging.INFO, stream=sys.stdout, format="%(asctime)s %(levelname)s %(name)s %(message)s"
)
logger = logging.getLogger("contacts")


def create_app(settings: Settings | None = None, repo: ContactsRepository | None = None) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if settings.run_migrations and settings.db_configured:
            applied = migrations.run_with_retry(lambda: db.connect(settings))
            logger.info("migrations applied: %s", applied or "none (up to date)")
        else:
            logger.info("skipping migrations (disabled or database not configured)")
        yield

    app = FastAPI(title="contacts-service", version="0.2.0", lifespan=lifespan)
    app.state.repo = repo or SqlContactsRepository(lambda: db.connect(settings))
    app.add_middleware(RequestLogMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Content-Type"],
    )

    @app.exception_handler(DatabaseUnavailable)
    async def database_unavailable(request: Request, exc: DatabaseUnavailable):
        # A clear message instead of a stack trace when the database is down or waking up.
        logger.warning("database unavailable: %s", exc)
        return JSONResponse(
            status_code=503, content={"detail": "Database unavailable, please try again shortly"}
        )

    @app.get("/health")
    def health():
        return {"status": "ok", "service": "contacts-service"}

    app.include_router(contacts_router)
    return app


app = create_app()
