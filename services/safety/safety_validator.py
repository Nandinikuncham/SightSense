"""Independent Safety Validator for SightSense.

CRITICAL INSTRUCTION:
No single AI model is allowed to own the entire pipeline.
This validator sits as a mandatory, independent gate between Narration generation
and Text-To-Speech (TTS). Any narration violating factual grounding or containing
forbidden safety guarantees is rejected with zero bypass capability.
"""

import re
from typing import NamedTuple

from sightsense_api.core.logging import get_logger
from sightsense_api.core.models import (
    Narration,
    Observation,
    RiskAssessment,
    TemporalEvent,
)

logger = get_logger("services.safety.validator")


class ValidationResult(NamedTuple):
    """Result of safety validation check."""

    is_valid: bool
    errors: list[str]
    safe_narration: Narration


class SafetyValidator:
    """Independent validator checking grounding, direction, and safety claims."""

    # Banned safety guarantees and unauthorized clearance claims
    FORBIDDEN_PATTERNS = [
        r"\b(?:definitely|guaranteed|completely)\s+safe\b",
        r"\byou\s+(?:are|will\s+be)\s+safe\b",
        r"\byou\s+can\s+(?:safely\s+)?(?:cross|proceed|walk|step)\b",
        r"\b(?:there\s+is\s+)?definitely\s+no\s+obstacle\b",
        r"\bpath\s+is\s+(?:definitely\s+)?(?:safe|completely\s+clear)\b",
        r"\ball\s+clear\b",
        r"\bno\s+(?:need\s+to\s+worry|danger|threat|risk)\b",
        r"\bclear\s+to\s+walk\b",
        r"\bसुरक्षित\b",       # Hindi: safe
        r"\bसुरक्षा\s+की\s+गारंटी\b", # Hindi: guarantee of safety
        r"\bముందుకు\s+వెళ్లవచ్చు\b",   # Telugu: you can proceed
        r"\bసురక్షితంగా\b",     # Telugu: safely
    ]

    def __init__(self, min_confidence: float = 0.50) -> None:
        self.min_confidence = min_confidence
        self.compiled_forbidden = [
            re.compile(p, re.IGNORECASE) for p in self.FORBIDDEN_PATTERNS
        ]
        self._total_validated = 0
        self._total_rejected = 0

    @property
    def rejection_count(self) -> int:
        return self._total_rejected

    @property
    def validation_count(self) -> int:
        return self._total_validated

    def validate(
        self,
        narration: Narration,
        risk: RiskAssessment,
        events: list[TemporalEvent],
        observations: list[Observation],
    ) -> ValidationResult:
        """Validate narration against structured evidence before allowing TTS synthesis."""
        self._total_validated += 1
        errors: list[str] = []
        text = narration.text
        text_lower = text.lower()

        # 1. Check for forbidden safety guarantees
        for pattern in self.compiled_forbidden:
            if pattern.search(text):
                errors.append(
                    f"Forbidden safety claim detected matching pattern: {pattern.pattern}"
                )

        # 2. Check confidence threshold
        if narration.confidence < self.min_confidence:
            errors.append(
                f"Narration confidence {narration.confidence:.2f} is below safety threshold {self.min_confidence:.2f}"
            )

        # 3. Grounding: Check for hallucinated objects
        # Gather all validated object classes and OCR text
        verified_classes = {obs.object_class.lower() for obs in observations}
        for event in events:
            verified_classes.add(event.object_class.lower())

        # Collect OCR texts
        verified_ocr_words: set[str] = set()
        for obs in observations:
            if obs.ocr_text:
                for w in obs.ocr_text.lower().split():
                    verified_ocr_words.add(w.strip(".,;:\"'()"))

        # Check if narration mentions concrete nouns not substantiated in verified classes
        SUSPECT_NOUNS = {
            "car", "vehicle", "bicycle", "bike", "truck", "bus", "motorcycle",
            "dog", "cat", "person", "pedestrian", "bench", "chair", "table",
            "stairs", "pothole", "hydrant", "traffic light", "train", "tree",
        }

        for suspect in SUSPECT_NOUNS:
            # If the suspect noun is in the narration text
            if re.search(rf"\b{re.escape(suspect)}\b", text_lower):
                # Ensure it exists in verified_classes or verified OCR
                if suspect not in verified_classes and not any(
                    suspect in cls for cls in verified_classes
                ):
                    errors.append(
                        f"Hallucinated object detected: '{suspect}' is not substantiated by evidence"
                    )

        # 4. Direction grounding
        # If narration explicitly says "on your left", verify an object actually was on the left
        if "left" in text_lower or "बाएं" in text_lower or "ఎడమ" in text_lower:
            has_left = any(o.spatial.horizontal == "left" for o in observations) or any(
                e.direction == "left" for e in events
            )
            if not has_left:
                errors.append("Direction mismatch: Narration mentions 'left' but evidence has no left object")

        if "right" in text_lower or "दाएं" in text_lower or "కుడి" in text_lower:
            has_right = any(o.spatial.horizontal == "right" for o in observations) or any(
                e.direction == "right" for e in events
            )
            if not has_right:
                errors.append("Direction mismatch: Narration mentions 'right' but evidence has no right object")

        # Decision
        if errors:
            self._total_rejected += 1
            logger.warning(
                "Safety validation REJECTED narration",
                extra={
                    "narration_text": text,
                    "validation_errors": errors,
                    "evidence_count": len(observations),
                },
            )

            # Produce safe deterministic fallback narration
            fallback_text = "Obstacle detected ahead." if risk.priority in {"critical", "high"} else "Observation detected."
            if observations:
                primary = observations[0]
                fallback_text = f"{primary.object_class.capitalize()} on your {primary.spatial.horizontal}."

            safe_narration = Narration(
                narration_id=narration.narration_id,
                text=fallback_text,
                language=narration.language,
                priority=risk.priority,
                evidence_ids=list(risk.evidence_ids),
                confidence=risk.confidence,
                validated=True,
                validation_errors=errors,
            )
            return ValidationResult(is_valid=False, errors=errors, safe_narration=safe_narration)

        # Approved
        approved_narration = Narration(
            narration_id=narration.narration_id,
            text=narration.text,
            language=narration.language,
            priority=narration.priority,
            evidence_ids=narration.evidence_ids,
            confidence=narration.confidence,
            validated=True,
            validation_errors=[],
        )
        return ValidationResult(is_valid=True, errors=[], safe_narration=approved_narration)
