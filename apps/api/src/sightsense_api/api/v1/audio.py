from fastapi import APIRouter, Depends
from fastapi.responses import Response


from sightsense_api.dependencies.services import (
    get_current_user,
    get_repository,
    get_storage,
)
from sightsense_api.core.errors import NotFoundError, AuthorizationError

router = APIRouter(prefix="/audio", tags=["Audio"])


@router.get("/{analysis_id}")
async def get_analysis_audio(
    analysis_id: str,
    repository=Depends(get_repository),
    storage=Depends(get_storage),
    current_user=Depends(get_current_user),
):
    analysis = await repository.get_analysis(analysis_id)

    if not analysis:
        raise NotFoundError("Analysis not found")

    if analysis.user_id != current_user.user_id:
        raise AuthorizationError("You do not have access to this audio")

    if not analysis.audio or not analysis.audio.audio_url:
        raise NotFoundError("Audio is not available for this analysis")

    key = (
        f"users/{analysis.user_id}/sessions/{analysis.session_id}"
        f"/analyses/{analysis.analysis_id}/audio.mp3"
    )

    audio_bytes = await storage.get_object_bytes(key)

    if not audio_bytes:
        raise NotFoundError("Audio file not found")

    return Response(
        content=audio_bytes,
        media_type="audio/mpeg",
        headers={
            "Content-Disposition": f'inline; filename="{analysis_id}.mp3"',
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )