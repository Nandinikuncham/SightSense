"""Request context, tracing, and security headers middleware."""

import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from sightsense_api.core.logging import get_logger

logger = get_logger("sightsense_api.middleware")


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Middleware ensuring X-Request-ID propagation, latency timing, and security headers."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Extract or generate X-Request-ID
        client_request_id = request.headers.get("X-Request-ID")
        if not client_request_id or len(client_request_id) > 128:
            request_id = f"req_{uuid.uuid4().hex[:16]}"
        else:
            request_id = client_request_id

        # Attach to request state for downstream handlers and dependencies
        request.state.request_id = request_id

        start_time = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception as exc:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error(
                "Unhandled exception during request processing",
                extra={
                    "request_id": request_id,
                    "route": request.url.path,
                    "duration_ms": duration_ms,
                },
                exc_info=exc,
            )
            raise exc

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # Attach tracking and security headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time-Ms"] = str(duration_ms)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Log completion
        logger.info(
            f"{request.method} {request.url.path} -> {response.status_code} ({duration_ms}ms)",
            extra={
                "request_id": request_id,
                "route": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )

        return response
