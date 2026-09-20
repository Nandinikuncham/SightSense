
from functools import lru_cache
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """SightSense application configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Application
    APP_NAME: str = "SightSense"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # Security
    SECRET_KEY: str = Field(
        default="CHANGE_ME_FOR_LOCAL_DEVELOPMENT_ONLY",
        description="Replace with a strong random secret before deployment.",
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ALGORITHM: str = "HS256"

    # Image upload
    MAX_UPLOAD_SIZE_BYTES: int = 5 * 1024 * 1024
    ALLOWED_MIME_TYPES: list[str] = [
        "image/jpeg",
        "image/png",
        "image/webp",
    ]

    # Local development adapters
    USE_LOCAL_ADAPTERS: bool = True

    # AWS configuration
    AWS_REGION: str = "ap-south-1"

    # Amazon Bedrock narration
    ENABLE_BEDROCK_NARRATION: bool = False
    BEDROCK_MODEL_ID: str = (
        "anthropic.claude-3-5-haiku-20241022-v1:0"
    )

    # Amazon Polly text-to-speech
    ENABLE_POLLY_TTS: bool = False

    # Assist-mode frame throttling
    ASSIST_FRAME_THROTTLE_SECONDS: int = 2

    # Storage
    USE_S3_STORAGE: bool = False
    S3_BUCKET_NAME: str | None = None

    # Logging
    LOG_LEVEL: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()