"""Standard envelope response schemas for SightSense API.

Guarantees consistent data, pagination, and error representations across all endpoints.
"""

from datetime import UTC, datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


def current_timestamp() -> str:
    """Return ISO 8601 UTC timestamp."""
    return datetime.now(UTC).isoformat()


class PaginationMeta(BaseModel):
    """Cursor-based pagination metadata."""

    next_cursor: str | None = Field(default=None, description="Cursor for the next page of results")
    has_more: bool = Field(default=False, description="Whether more items are available")


class SuccessEnvelope(BaseModel, Generic[T]):
    """Standard success envelope."""

    data: T
    request_id: str = Field(..., description="Unique request identifier")
    timestamp: str = Field(
        default_factory=current_timestamp, description="Timestamp of the response"
    )


class PaginatedEnvelope(BaseModel, Generic[T]):
    """Standard paginated success envelope."""

    data: list[T]
    pagination: PaginationMeta
    request_id: str = Field(..., description="Unique request identifier")
    timestamp: str = Field(
        default_factory=current_timestamp, description="Timestamp of the response"
    )


class ErrorDetail(BaseModel):
    """Inner error payload detail."""

    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable safe error message")
    details: dict[str, Any] = Field(default_factory=dict, description="Structured error context")
    retryable: bool = Field(default=False, description="Indicates if client can safely retry")


class ErrorEnvelope(BaseModel):
    """Standard error envelope for all application and validation failures."""

    error: ErrorDetail
    request_id: str = Field(..., description="Unique request identifier")
    timestamp: str = Field(default_factory=current_timestamp, description="Timestamp of the error")
