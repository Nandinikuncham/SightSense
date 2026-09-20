"""Domain entities and Pydantic schemas for SightSense.

These models serve as clean domain representations independent of any AWS SDK
or database driver specifics.
"""

import uuid
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    """Return timezone-aware current UTC datetime."""
    return datetime.now(UTC)


def generate_id(prefix: str) -> str:
    """Generate clean prefixed UUID."""
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


# User Entities
class User(BaseModel):
    """User profile domain model."""

    user_id: str
    email: str
    full_name: str
    status: Literal["active", "suspended"] = "active"
    created_at: datetime = Field(default_factory=utc_now)


# Session Entities & Preferences
SessionMode = Literal["assist", "ask", "explore"]
SessionStatus = Literal["active", "closed"]
LanguageCode = Literal["en-IN", "hi-IN", "te-IN"]
VerbosityLevel = Literal["concise", "detailed"]
AlertSensitivity = Literal["high", "medium", "low"]


class SessionPreferences(BaseModel):
    """Configurable user preferences for narration and sensory alerts."""

    language: LanguageCode = "en-IN"
    speech_speed: float = Field(default=1.0, ge=0.5, le=2.0)
    verbosity: VerbosityLevel = "concise"
    alert_sensitivity: AlertSensitivity = "high"
    narration_frequency: float = Field(default=3.0, ge=1.0, le=30.0)
    enabled_categories: list[str] = Field(
        default_factory=lambda: [
            "person",
            "vehicle",
            "bicycle",
            "car",
            "motorcycle",
            "bus",
            "truck",
            "traffic light",
            "stop sign",
            "bench",
            "dog",
            "cat",
            "stairs",
            "door",
            "chair",
            "curb",
            "pothole",
        ]
    )


class Session(BaseModel):
    """Assistive vision session model."""

    session_id: str = Field(default_factory=lambda: generate_id("ses"))
    user_id: str
    mode: SessionMode = "assist"
    status: SessionStatus = "active"
    preferences: SessionPreferences = Field(default_factory=SessionPreferences)
    started_at: datetime = Field(default_factory=utc_now)
    closed_at: datetime | None = None
    frame_count: int = 0
    alert_count: int = 0


# Upload Entities
UploadStatus = Literal["pending", "uploaded", "failed", "expired"]


class Upload(BaseModel):
    """S3 Upload tracking entity."""

    upload_id: str = Field(default_factory=lambda: generate_id("upl"))
    user_id: str
    session_id: str | None = None
    object_key: str
    content_type: str
    content_length: int
    status: UploadStatus = "pending"
    upload_url: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    expires_at: datetime


# Perception Entities
class BoundingBox(BaseModel):
    """Normalized bounding box coordinates (0.0 - 1.0)."""

    x_min: float = Field(..., ge=0.0, le=1.0)
    y_min: float = Field(..., ge=0.0, le=1.0)
    x_max: float = Field(..., ge=0.0, le=1.0)
    y_max: float = Field(..., ge=0.0, le=1.0)

    @property
    def width(self) -> float:
        return max(0.0, self.x_max - self.x_min)

    @property
    def height(self) -> float:
        return max(0.0, self.y_max - self.y_min)

    @property
    def area(self) -> float:
        return self.width * self.height

    @property
    def center_x(self) -> float:
        return (self.x_min + self.x_max) / 2.0

    @property
    def center_y(self) -> float:
        return (self.y_min + self.y_max) / 2.0


class SpatialRelation(BaseModel):
    """Derived spatial location and proximity."""

    horizontal: Literal["left", "center", "right"]
    vertical: Literal["upper", "middle", "ground_level"]
    relative_proximity: Literal["immediate", "near", "moderate", "distant"]
    ground_relation: Literal["ground_obstacle", "elevated", "overhead", "none"]
    confidence: float = Field(..., ge=0.0, le=1.0)


class Observation(BaseModel):
    """Perception evidence unit."""

    observation_id: str = Field(default_factory=lambda: generate_id("obs"))
    analysis_id: str
    object_class: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    bounding_box: BoundingBox
    spatial: SpatialRelation
    ocr_text: str | None = None
    ocr_confidence: float | None = None
    image_quality: float = Field(default=1.0, ge=0.0, le=1.0)
    uncertainty: float = Field(default=0.0, ge=0.0, le=1.0)
    timestamp: datetime = Field(default_factory=utc_now)


# Temporal Reasoning Entities
EventType = Literal[
    "OBJECT_APPEARED",
    "OBJECT_DISAPPEARED",
    "OBJECT_APPROACHING",
    "OBJECT_RECEDING",
    "OBJECT_MOVING",
    "OBJECT_PERSISTENT",
    "SCENE_CHANGED",
    "OCR_DETECTED",
]


class TemporalEvent(BaseModel):
    """Detected temporal dynamics between frames."""

    event_id: str = Field(default_factory=lambda: generate_id("evt"))
    analysis_id: str
    event_type: EventType
    object_class: str
    direction: Literal["left", "center", "right"]
    movement: Literal["approaching", "receding", "lateral", "stationary"]
    confidence: float = Field(..., ge=0.0, le=1.0)
    evidence_ids: list[str]
    timestamp: datetime = Field(default_factory=utc_now)


# Risk / Relevance Assessment
RiskPriority = Literal["critical", "high", "medium", "low", "informational"]


class RiskAssessment(BaseModel):
    """Evaluated risk and relevance for user notification."""

    assessment_id: str = Field(default_factory=lambda: generate_id("rsk"))
    priority: RiskPriority
    risk_type: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    reason: str
    evidence_ids: list[str]
    spatial_relation: str
    temporal_relation: str
    requires_interruption: bool = False
    timestamp: datetime = Field(default_factory=utc_now)


# Narration & Safety Entities
class Narration(BaseModel):
    """Generated language narration payload."""

    narration_id: str = Field(default_factory=lambda: generate_id("nar"))
    text: str
    language: LanguageCode = "en-IN"
    priority: RiskPriority
    evidence_ids: list[str]
    confidence: float = Field(..., ge=0.0, le=1.0)
    validated: bool = False
    validation_errors: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=utc_now)


# Audio Output
AudioStatus = Literal["pending", "synthesized", "failed", "cached"]


class AudioOutput(BaseModel):
    """Synthesized speech output entity."""

    audio_id: str = Field(default_factory=lambda: generate_id("aud"))
    analysis_id: str
    language: LanguageCode
    voice: str
    speed: float
    duration_seconds: float = 0.0
    audio_url: str | None = None
    status: AudioStatus = "pending"
    priority: RiskPriority = "medium"
    timestamp: datetime = Field(default_factory=utc_now)


# Analysis Aggregate
AnalysisStatus = Literal["pending", "processing", "completed", "failed"]


class Analysis(BaseModel):
    """Analysis aggregate record."""

    analysis_id: str = Field(default_factory=lambda: generate_id("ana"))
    session_id: str
    user_id: str
    status: AnalysisStatus = "pending"
    input_object_key: str | None = None
    mode: SessionMode = "assist"
    query_text: str | None = None
    observations: list[Observation] = Field(default_factory=list)
    events: list[TemporalEvent] = Field(default_factory=list)
    risk_assessment: RiskAssessment | None = None
    narration: Narration | None = None
    audio: AudioOutput | None = None
    error_message: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime | None = None


# Feedback Entity
FeedbackType = Literal[
    "useful",
    "incorrect_observation",
    "missed_object",
    "incorrect_narration",
    "inappropriate_alert",
    "too_repetitive",
    "too_slow",
    "ocr_error",
    "other",
]


class Feedback(BaseModel):
    """User feedback report."""

    feedback_id: str = Field(default_factory=lambda: generate_id("fdb"))
    user_id: str
    session_id: str
    analysis_id: str | None = None
    feedback_type: FeedbackType
    comment: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
