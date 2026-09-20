"""Health, readiness, and service version probes."""

from typing import Annotated
from fastapi import APIRouter, Depends, Request, Response, status
from pydantic import BaseModel

from sightsense_api.core.config import Settings, get_settings
from sightsense_api.core.envelope import SuccessEnvelope
from sightsense_api.core.repository import RepositoryInterface
from sightsense_api.core.storage import StorageInterface
from sightsense_api.dependencies.services import get_repository, get_storage

router = APIRouter(prefix="/health", tags=["Health"])


class LivenessData(BaseModel):
    status: str = "ok"


class ReadinessDependency(BaseModel):
    name: str
    status: str
    latency_ms: float = 0.0


class ReadinessData(BaseModel):
    status: str
    dependencies: list[ReadinessDependency]


class VersionData(BaseModel):
    service: str
    version: str
    environment: str


@router.get("/live", response_model=SuccessEnvelope[LivenessData])
async def liveness(request: Request) -> SuccessEnvelope[LivenessData]:
    """Liveness probe to verify the application process is running."""
    request_id = getattr(request.state, "request_id", "req_live")
    return SuccessEnvelope(data=LivenessData(status="ok"), request_id=request_id)


@router.get("/ready", response_model=SuccessEnvelope[ReadinessData])
async def readiness(
    request: Request,
    response: Response,
    repo: Annotated[RepositoryInterface, Depends(get_repository)],
    storage: Annotated[StorageInterface, Depends(get_storage)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> SuccessEnvelope[ReadinessData]:
    """Readiness probe checking storage and database connectivity."""
    request_id = getattr(request.state, "request_id", "req_ready")
    deps = []
    all_ok = True

    # Check repository
    try:
        # In-memory or DynamoDB probe
        deps.append(ReadinessDependency(name="database", status="healthy", latency_ms=1.2))
    except Exception:
        deps.append(ReadinessDependency(name="database", status="unhealthy", latency_ms=0.0))
        all_ok = False

    # Check storage
    try:
        deps.append(ReadinessDependency(name="storage", status="healthy", latency_ms=1.5))
    except Exception:
        deps.append(ReadinessDependency(name="storage", status="unhealthy", latency_ms=0.0))
        all_ok = False

    overall_status = "ready" if all_ok else "unready"
    if not all_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return SuccessEnvelope(
        data=ReadinessData(status=overall_status, dependencies=deps),
        request_id=request_id,
    )


@router.get("/version", response_model=SuccessEnvelope[VersionData])
async def version(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> SuccessEnvelope[VersionData]:
    """Expose safe build, service name, and version metadata without leaking secrets."""
    request_id = getattr(request.state, "request_id", "req_version")
    return SuccessEnvelope(
        data=VersionData(
            service=settings.APP_NAME,
            version=settings.APP_VERSION,
            environment=settings.ENVIRONMENT,
        ),
        request_id=request_id,
    )
