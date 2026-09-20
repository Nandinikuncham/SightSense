"""Session management endpoints with strict user ownership authorization."""

from datetime import datetime, timezone
from typing import Annotated
from fastapi import APIRouter, Depends, Query, Request, status
from pydantic import BaseModel

from sightsense_api.core.envelope import PaginatedEnvelope, PaginationMeta, SuccessEnvelope
from sightsense_api.core.errors import AuthorizationError, NotFoundError
from sightsense_api.core.models import (
    Session,
    SessionMode,
    SessionPreferences,
    User,
)
from sightsense_api.core.repository import RepositoryInterface
from sightsense_api.dependencies.services import get_current_user, get_repository
from services.orchestrator import get_pipeline_orchestrator

router = APIRouter(prefix="/sessions", tags=["Sessions"])


class CreateSessionRequest(BaseModel):
    mode: SessionMode = "assist"
    preferences: SessionPreferences | None = None


class UpdateSessionRequest(BaseModel):
    mode: SessionMode | None = None
    preferences: SessionPreferences | None = None


@router.post(
    "",
    response_model=SuccessEnvelope[Session],
    status_code=status.HTTP_201_CREATED,
)
async def create_session(
    request: Request,
    body: CreateSessionRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    repo: Annotated[RepositoryInterface, Depends(get_repository)],
) -> SuccessEnvelope[Session]:
    """Create a new assistive vision session for authenticated user."""
    request_id = getattr(request.state, "request_id", "req_session")
    session = Session(
        user_id=current_user.user_id,
        mode=body.mode,
        preferences=body.preferences or SessionPreferences(),
    )
    saved = await repo.create_session(session)
    return SuccessEnvelope(data=saved, request_id=request_id)


@router.get("", response_model=PaginatedEnvelope[Session])
async def list_sessions(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    repo: Annotated[RepositoryInterface, Depends(get_repository)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: Annotated[str | None, Query()] = None,
) -> PaginatedEnvelope[Session]:
    """List sessions owned by authenticated user with cursor pagination."""
    request_id = getattr(request.state, "request_id", "req_session")
    sessions, next_cursor = await repo.list_sessions_by_user(
        user_id=current_user.user_id, limit=limit, cursor=cursor
    )
    return PaginatedEnvelope(
        data=sessions,
        pagination=PaginationMeta(next_cursor=next_cursor, has_more=next_cursor is not None),
        request_id=request_id,
    )


@router.get("/{session_id}", response_model=SuccessEnvelope[Session])
async def get_session(
    request: Request,
    session_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    repo: Annotated[RepositoryInterface, Depends(get_repository)],
) -> SuccessEnvelope[Session]:
    """Retrieve details for a specific session. Enforces strict user ownership."""
    request_id = getattr(request.state, "request_id", "req_session")
    session = await repo.get_session(session_id)
    if not session:
        raise NotFoundError("Session not found.")

    if session.user_id != current_user.user_id:
        raise AuthorizationError("You do not have permission to access this session.")

    return SuccessEnvelope(data=session, request_id=request_id)


@router.patch("/{session_id}", response_model=SuccessEnvelope[Session])
async def update_session(
    request: Request,
    session_id: str,
    body: UpdateSessionRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    repo: Annotated[RepositoryInterface, Depends(get_repository)],
) -> SuccessEnvelope[Session]:
    """Update active mode or preferences for a session."""
    request_id = getattr(request.state, "request_id", "req_session")
    session = await repo.get_session(session_id)
    if not session:
        raise NotFoundError("Session not found.")

    if session.user_id != current_user.user_id:
        raise AuthorizationError("You do not have permission to modify this session.")

    if body.mode is not None:
        session.mode = body.mode
    if body.preferences is not None:
        session.preferences = body.preferences

    updated = await repo.update_session(session)
    return SuccessEnvelope(data=updated, request_id=request_id)


@router.post("/{session_id}/close", response_model=SuccessEnvelope[Session])
async def close_session(
    request: Request,
    session_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    repo: Annotated[RepositoryInterface, Depends(get_repository)],
) -> SuccessEnvelope[Session]:
    """Close an active session and clear temporal tracking state."""
    request_id = getattr(request.state, "request_id", "req_session")
    session = await repo.get_session(session_id)
    if not session:
        raise NotFoundError("Session not found.")

    if session.user_id != current_user.user_id:
        raise AuthorizationError("You do not have permission to close this session.")

    session.status = "closed"
    session.closed_at = datetime.now(timezone.utc)
    updated = await repo.update_session(session)

    # Clear temporal tracking state
    orchestrator = get_pipeline_orchestrator()
    orchestrator.temporal.clear_session(session_id)

    return SuccessEnvelope(data=updated, request_id=request_id)
