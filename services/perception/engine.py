"""Perception engine interface and implementations for SightSense.

Detects objects, bounding boxes, confidences, and OCR text without making safety or risk judgements.
"""

import uuid
from abc import ABC, abstractmethod

from pydantic import BaseModel, Field
from sightsense_api.core.models import BoundingBox, Observation, SpatialRelation


class PerceptionResult(BaseModel):
    """Structured perception output for a single frame."""

    analysis_id: str
    observations: list[Observation] = Field(default_factory=list)
    image_quality: float = Field(default=1.0, ge=0.0, le=1.0)
    processing_time_ms: float = 0.0
    engine_name: str = "DevelopmentPerceptionEngine"


class PerceptionEngine(ABC):
    """Abstract perception interface."""

    @abstractmethod
    async def process_frame(
        self,
        image_bytes: bytes,
        analysis_id: str,
        query_text: str | None = None,
    ) -> PerceptionResult: ...


class DevelopmentPerceptionEngine(PerceptionEngine):
    """Deterministic perception engine for testing, evaluation, and offline development.

    Produces structured evidence based on simulated scenarios or byte inspection.
    """

    def __init__(self) -> None:
        self.preset_scenarios: dict[str, list[dict]] = {
            "approaching_bike": [
                {
                    "class": "bicycle",
                    "confidence": 0.92,
                    "bbox": (0.65, 0.40, 0.90, 0.85),
                    "horizontal": "right",
                    "vertical": "ground_level",
                    "proximity": "near",
                    "ground": "ground_obstacle",
                }
            ],
            "center_obstacle": [
                {
                    "class": "stairs",
                    "confidence": 0.95,
                    "bbox": (0.35, 0.50, 0.65, 0.95),
                    "horizontal": "center",
                    "vertical": "ground_level",
                    "proximity": "immediate",
                    "ground": "ground_obstacle",
                }
            ],
            "store_sign": [
                {
                    "class": "sign",
                    "confidence": 0.91,
                    "bbox": (0.30, 0.15, 0.70, 0.40),
                    "horizontal": "center",
                    "vertical": "upper",
                    "proximity": "moderate",
                    "ground": "overhead",
                    "ocr_text": "METRO STATION ENTRANCE",
                    "ocr_confidence": 0.96,
                }
            ],
            "hallucination_test": [
                {
                    "class": "bench",
                    "confidence": 0.88,
                    "bbox": (0.10, 0.50, 0.35, 0.80),
                    "horizontal": "left",
                    "vertical": "ground_level",
                    "proximity": "moderate",
                    "ground": "ground_obstacle",
                }
            ],
        }

    async def process_frame(
        self,
        image_bytes: bytes,
        analysis_id: str,
        query_text: str | None = None,
    ) -> PerceptionResult:
        observations: list[Observation] = []

        # Check if a scenario tag is encoded in the first 64 bytes (for testing)
        scenario_key = "default"
        try:
            prefix = image_bytes[:64].decode("utf-8", errors="ignore").lower()
            for key in self.preset_scenarios:
                if key in prefix:
                    scenario_key = key
                    break
        except Exception:
            scenario_key = "default"

        # If query asks about reading, prioritize OCR text
        if query_text and any(word in query_text.lower() for word in ["read", "sign", "text"]):
            scenario_key = "store_sign"

        preset = self.preset_scenarios.get(
            scenario_key,
            [
                {
                    "class": "person",
                    "confidence": 0.89,
                    "bbox": (0.40, 0.20, 0.60, 0.75),
                    "horizontal": "center",
                    "vertical": "middle",
                    "proximity": "moderate",
                    "ground": "none",
                }
            ],
        )

        for item in preset:
            b = item["bbox"]
            bbox = BoundingBox(x_min=b[0], y_min=b[1], x_max=b[2], y_max=b[3])
            spatial = SpatialRelation(
                horizontal=item["horizontal"],
                vertical=item["vertical"],
                relative_proximity=item["proximity"],
                ground_relation=item["ground"],
                confidence=item["confidence"],
            )
            obs = Observation(
                observation_id=f"obs_{uuid.uuid4().hex[:12]}",
                analysis_id=analysis_id,
                object_class=item["class"],
                confidence=item["confidence"],
                bounding_box=bbox,
                spatial=spatial,
                ocr_text=item.get("ocr_text"),
                ocr_confidence=item.get("ocr_confidence"),
                image_quality=1.0,
                uncertainty=round(1.0 - item["confidence"], 2),
            )
            observations.append(obs)

        return PerceptionResult(
            analysis_id=analysis_id,
            observations=observations,
            image_quality=1.0,
            processing_time_ms=12.5,
            engine_name="DevelopmentPerceptionEngine",
        )
