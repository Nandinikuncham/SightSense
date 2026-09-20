"""FastAPI dependency injection providers for repositories, storage, and auth."""

from typing import Annotated

from fastapi import Depends, Header, Request

from sightsense_api.core.config import Settings, get_settings
from sightsense_api.core.errors import AuthenticationError
from sightsense_api.core.models import User
from sightsense_api.core.repository import (
    DynamoDBRepository,
    InMemoryRepository,
    RepositoryInterface,
)
from sightsense_api.core.storage import (
    LocalStorageAdapter,
    S3StorageAdapter,
    StorageInterface,
)

# Shared in-memory singletons for local development/testing
_in_memory_repo = InMemoryRepository()
_local_storage = LocalStorageAdapter()


def get_repository(
    settings: Annotated[Settings, Depends(get_settings)],
) -> RepositoryInterface:
    """Return configured database repository."""
    if settings.USE_LOCAL_ADAPTERS or not settings.DYNAMODB_TABLE_NAME:
        return _in_memory_repo
    return DynamoDBRepository(
        table_name=settings.DYNAMODB_TABLE_NAME,
        region_name=settings.AWS_REGION,
    )


def get_storage(
    settings: Annotated[Settings, Depends(get_settings)],
) -> StorageInterface:
    """Return configured object storage adapter."""
    if settings.USE_LOCAL_ADAPTERS or not settings.S3_BUCKET_NAME:
        return _local_storage
    return S3StorageAdapter(
        bucket_name=settings.S3_BUCKET_NAME,
        region_name=settings.AWS_REGION,
    )


async def get_current_user(
    request: Request,
    repo: Annotated[RepositoryInterface, Depends(get_repository)],
    settings: Annotated[Settings, Depends(get_settings)],
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    """Validate bearer token and retrieve authenticated user."""
    if not authorization:
        raise AuthenticationError("Authorization header is missing")

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise AuthenticationError("Invalid authorization format. Expected 'Bearer <token>'")

    token = parts[1]

    # In local development / test mode, allow 'test_user_<id>' or create default demo user
    if settings.USE_LOCAL_ADAPTERS or not settings.is_production:
        user_id = token if token.startswith("usr_") else f"usr_{token}"
        user = await repo.get_user_by_id(user_id)
        if not user:
            user = User(
                user_id=user_id,
                email=f"{user_id}@example.com",
                full_name="SightSense Verified User",
            )
            await repo.create_user(user)
        return user

    # Production Cognito token validation:
    raise AuthenticationError("Cognito authentication required in production")
