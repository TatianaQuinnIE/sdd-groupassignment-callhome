"""Overlap service main.py, builds FastAPI app, connectes the startip logic and middleware,
and exposes a health endpoint."""

import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import db, migrations
from app.config import Settings
from app.logging_middleware import RequestLogMiddleware

# Root login
logging.basicConfig(
    level=logging.INFO, stream=sys.stdout, format="%(asctime)s %(levelname)s %(name)s %(message)s"
)
logger = logging.getLogger("overlap")


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

    app = FastAPI(title="overlap-service", version="0.1.0", lifespan=lifespan)
    app.add_middleware(RequestLogMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET"],
        allow_headers=["Content-Type"],
    )

    @app.get("/health")
    def health():
        # Deliberately independent of contacts-service and Nager.Date, so a
        # dependency outage never makes this service look dead to the pipeline.
        return {"status": "ok", "service": "overlap-service"}

    return app


app = create_app()
