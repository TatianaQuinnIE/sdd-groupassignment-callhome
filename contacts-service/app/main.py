"""contacts-service: contacts, call log and availability for the Calling-home planner."""

import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import db, migrations
from app.config import Settings
from app.logging_middleware import RequestLogMiddleware

logging.basicConfig(
    level=logging.INFO, stream=sys.stdout, format="%(asctime)s %(levelname)s %(name)s %(message)s"
)
logger = logging.getLogger("contacts")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if settings.run_migrations and settings.db_configured:
            applied = migrations.run_with_retry(lambda: db.connect(settings))
            logger.info("migrations applied: %s", applied or "none (up to date)")
        else:
            logger.info("skipping migrations (disabled or database not configured)")
        yield

    app = FastAPI(title="contacts-service", version="0.1.0", lifespan=lifespan)
    app.add_middleware(RequestLogMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Content-Type"],
    )

    @app.get("/health")
    def health():
        return {"status": "ok", "service": "contacts-service"}

    return app


app = create_app()
