"""One log line per request to stdout: method, path, status, duration."""

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("contacts.requests")


class RequestLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            return response
        finally:
            duration_ms = (time.perf_counter() - start) * 1000
            logger.info(
                "method=%s path=%s status=%d duration_ms=%.1f",
                request.method,
                request.url.path,
                status,
                duration_ms,
            )
