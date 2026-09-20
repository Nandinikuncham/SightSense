"""Centralized exception hierarchy for SightSense.

Every domain and operational error maps to a standard error code, HTTP status,
user-safe error message, and retryable flag. Stack traces or internal details
are never leaked in production responses.
"""

from typing import Any


class SightSenseException(Exception):
    """Base exception for all application errors."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 500,
        details: dict[str, Any] | None = None,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        self.retryable = retryable


class AuthenticationError(SightSenseException):
    """Raised when authentication credentials are missing or invalid."""

    def __init__(
        self,
        message: str = "Authentication failed or token is invalid.",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="AUTHENTICATION_FAILED",
            message=message,
            status_code=401,
            details=details,
            retryable=False,
        )


class AuthorizationError(SightSenseException):
    """Raised when an authenticated user attempts to access a forbidden resource."""

    def __init__(
        self,
        message: str = "You do not have permission to access this resource.",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="FORBIDDEN_RESOURCE",
            message=message,
            status_code=403,
            details=details,
            retryable=False,
        )


class NotFoundError(SightSenseException):
    """Raised when a requested resource does not exist."""

    def __init__(
        self,
        message: str = "The requested resource was not found.",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="RESOURCE_NOT_FOUND",
            message=message,
            status_code=404,
            details=details,
            retryable=False,
        )


class ConflictError(SightSenseException):
    """Raised on state conflict or idempotency key violations."""

    def __init__(
        self,
        message: str = "A conflicting resource or request already exists.",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="CONFLICT",
            message=message,
            status_code=409,
            details=details,
            retryable=False,
        )


class PayloadTooLargeError(SightSenseException):
    """Raised when upload size exceeds the configured maximum bytes."""

    def __init__(
        self,
        message: str = "The uploaded file exceeds the maximum allowed size.",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="PAYLOAD_TOO_LARGE",
            message=message,
            status_code=413,
            details=details,
            retryable=False,
        )


class UnsupportedMediaTypeError(SightSenseException):
    """Raised when uploaded MIME type is not supported."""

    def __init__(
        self,
        message: str = "The provided media type is not supported.",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="UNSUPPORTED_MEDIA_TYPE",
            message=message,
            status_code=415,
            details=details,
            retryable=False,
        )


class ValidationError(SightSenseException):
    """Raised when input parameters fail schema or business validation."""

    def __init__(
        self,
        message: str = "Validation failed for request parameters.",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="INVALID_REQUEST",
            message=message,
            status_code=422,
            details=details,
            retryable=False,
        )


class RateLimitExceededError(SightSenseException):
    """Raised when client exceeds rate limits."""

    def __init__(
        self,
        message: str = "Too many requests. Please slow down.",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="RATE_LIMIT_EXCEEDED",
            message=message,
            status_code=429,
            details=details,
            retryable=True,
        )


class UpstreamServiceError(SightSenseException):
    """Raised when an upstream AWS or ML provider fails."""

    def __init__(
        self,
        message: str = "An upstream service encountered an error.",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="UPSTREAM_FAILURE",
            message=message,
            status_code=502,
            details=details,
            retryable=True,
        )


class SafetyValidationError(SightSenseException):
    """Raised when generated narration violates grounding or safety constraints."""

    def __init__(
        self,
        message: str = "Narration failed safety validation checks.",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="SAFETY_VALIDATION_FAILED",
            message=message,
            status_code=422,
            details=details,
            retryable=False,
        )


class InternalServerError(SightSenseException):
    """Raised for unexpected internal server errors."""

    def __init__(
        self,
        message: str = "An internal server error occurred.",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="INTERNAL_ERROR",
            message=message,
            status_code=500,
            details=details,
            retryable=True,
        )
