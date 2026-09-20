
"""Authenticated audio playback endpoints for SightSense."""

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from sightsense_api.core.errors import (
    AuthorizationError,
    NotFoundError,
)
from sightsense_api.core.repository import RepositoryInterface
from sightsense_api.core.storage import StorageInterface
from sightsense_api.dependencies.services import (
    get_current_user,
    get_repository,
    get_storage,
)

router = APIRouter(prefix="/audio", tags=["Audio"])


@router.get("/{analysis_id}")
async def get_analysis_audio(
    analysis_id: str,
    repo: Annotated[
        RepositoryInterface,
        Depends(get_repository),
    ],
    storage: Annotated[
        StorageInterface,
        Depends(get_storage),
    ],
    user=Depends(get_current_user),
) -> Response:
    """Return an analysis MP3 after verifying ownership."""

    analysis = await repo.get_analysis(analysis_id)

    if not analysis:
        raise NotFoundError("Analysis not found")

    if analysis.user_id != user.user_id:
        raise AuthorizationError(
            "You do not have access to this audio"
        )

    audio = analysis.audio

    if not audio or not audio.audio_url:
        raise NotFoundError(
            "Playable audio is not available for this analysis"
        )

    object_key = (
        f"users/{analysis.user_id}/"
        f"sessions/{analysis.session_id}/"
        f"analyses/{analysis.analysis_id}/audio.mp3"
    )

    audio_bytes = await storage.get_object_bytes(object_key)

    if not audio_bytes:
        raise NotFoundError("Audio file was not found")

    return Response(
        content=audio_bytes,
        media_type="audio/mpeg",
        headers={
            "Content-Disposition": (
                f'inline; filename="{analysis_id}.mp3"'
            ),
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )