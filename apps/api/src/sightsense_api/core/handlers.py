"""Global exception handlers converting all errors into standardized ErrorEnvelope."""

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from sightsense_api.core.envelope import ErrorDetail, ErrorEnvelope
from sightsense_api.core.errors import SightSenseException
from sightsense_api.core.logging import get_logger

logger = get_logger("sightsense_api.handlers")


def register_exception_handlers(app: FastAPI) -> None:
    """Register custom exception handlers with FastAPI application."""

    @app.exception_handler(SightSenseException)
    async def sightsense_exception_handler(
        request: Request, exc: SightSenseException
    ) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "req_unknown")
        envelope = ErrorEnvelope(
            error=ErrorDetail(
                code=exc.code,
                message=exc.message,
                details=exc.details,
                retryable=exc.retryable,
            ),
            request_id=request_id,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=envelope.model_dump(),
            headers={"X-Request-ID": request_id},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "req_unknown")
        details = {"errors": []}
        for error in exc.errors():
            details["errors"].append(
                {
                    "loc": [str(loc) for loc in error.get("loc", [])],
                    "msg": error.get("msg", ""),
                    "type": error.get("type", ""),
                }
            )

        envelope = ErrorEnvelope(
            error=ErrorDetail(
                code="INVALID_REQUEST",
                message="Schema validation failed for request parameters.",
                details=details,
                retryable=False,
            ),
            request_id=request_id,
        )
        return JSONResponse(
            status_code=422,
            content=envelope.model_dump(),
            headers={"X-Request-ID": request_id},
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "req_unknown")
        envelope = ErrorEnvelope(
            error=ErrorDetail(
                code=f"HTTP_{exc.status_code}",
                message=str(exc.detail),
                details={},
                retryable=exc.status_code in {502, 503, 504},
            ),
            request_id=request_id,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=envelope.model_dump(),
            headers={"X-Request-ID": request_id},
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "req_unknown")
        logger.error(
            "Unhandled server exception",
            extra={"request_id": request_id, "route": request.url.path},
            exc_info=exc,
        )
        envelope = ErrorEnvelope(
            error=ErrorDetail(
                code="INTERNAL_ERROR",
                message="An unexpected server error occurred. Please try again later.",
                details={},
                retryable=True,
            ),
            request_id=request_id,
        )
        return JSONResponse(
            status_code=500,
            content=envelope.model_dump(),
            headers={"X-Request-ID": request_id},
        )
