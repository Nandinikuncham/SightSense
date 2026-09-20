
"""Image analysis endpoints for SightSense."""

from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, UploadFile

from sightsense_api.core.config import Settings, get_settings
from sightsense_api.core.envelope import SuccessEnvelope
from sightsense_api.core.errors import (
    AuthorizationError,
    NotFoundError,
    PayloadTooLargeError,
    UnsupportedMediaTypeError,
    ValidationError,
)
from sightsense_api.core.models import Analysis
from sightsense_api.core.repository import RepositoryInterface
from sightsense_api.core.storage import StorageInterface
from sightsense_api.dependencies.services import (
    get_current_user,
    get_repository,
    get_storage,
)
from services.orchestrator import get_pipeline_orchestrator

router = APIRouter(prefix="/sessions", tags=["Analysis"])


@router.post(
    "/{session_id}/analysis",
    response_model=SuccessEnvelope[Analysis],
)
async def analyze_image(
    session_id: str,
    image: Annotated[UploadFile, File(...)],
    query_text: Annotated[str | None, Form()] = None,
    repo: RepositoryInterface = Depends(get_repository),
    storage: StorageInterface = Depends(get_storage),
    user=Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    """Analyze one uploaded image within an active session."""

    session = await repo.get_session(session_id)

    if not session:
        raise NotFoundError("Session not found")

    if session.user_id != user.user_id:
        raise AuthorizationError(
            "You do not have access to this session"
        )

    if session.status != "active":
        raise ValidationError(
            "Cannot analyze images in a closed session"
        )

    content_type = (image.content_type or "").lower().strip()

    if content_type not in settings.ALLOWED_MIME_TYPES:
        raise UnsupportedMediaTypeError(
            f"Unsupported image type: {content_type or 'unknown'}"
        )

    max_bytes = settings.MAX_UPLOAD_SIZE_BYTES
    image_bytes = await image.read(max_bytes + 1)

    if not image_bytes:
        raise ValidationError("The uploaded image is empty")

    if len(image_bytes) > max_bytes:
        raise PayloadTooLargeError(
            "Image exceeds the maximum upload size"
        )

    analysis_id = f"ana_{uuid4().hex[:16]}"

    input_object_key = (
        f"users/{user.user_id}/sessions/{session_id}/"
        f"analyses/{analysis_id}/input"
    )

    await storage.put_object_bytes(
        object_key=input_object_key,
        data=image_bytes,
        content_type=content_type,
    )

    analysis = await get_pipeline_orchestrator().execute_pipeline(
        session=session,
        image_bytes=image_bytes,
        analysis_id=analysis_id,
        query_text=query_text,
        storage=storage,
    )

    analysis.input_object_key = input_object_key

    await repo.create_analysis(analysis)

    session.frame_count += 1

    if (
        analysis.risk_assessment
        and analysis.risk_assessment.requires_interruption
    ):
        session.alert_count += 1

    await repo.update_session(session)

    return SuccessEnvelope[Analysis](
        data=analysis,
        request_id=str(uuid4()),
    )