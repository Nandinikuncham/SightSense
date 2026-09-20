"""Deterministic Risk and Relevance Engine for SightSense.

Evaluates structured perception and temporal evidence against an auditable policy matrix.
Generative AI models are strictly prohibited from determining safety priority levels.
"""

import uuid

from sightsense_api.core.models import (
    Observation,
    RiskAssessment,
    RiskPriority,
    SessionMode,
    SessionPreferences,
    TemporalEvent,
)

HIGH_HAZARD_OBJECTS = {
    "vehicle",
    "car",
    "bus",
    "truck",
    "motorcycle",
    "bicycle",
    "train",
    "stairs",
    "curb",
    "pothole",
    "hole",
}

MODERATE_HAZARD_OBJECTS = {
    "person",
    "dog",
    "chair",
    "table",
    "pole",
    "barrier",
    "door",
    "cart",
}


class RiskEngine:
    """Deterministic policy engine prioritizing environmental hazards and relevance."""

    def evaluate(
        self,
        observations: list[Observation],
        events: list[TemporalEvent],
        mode: SessionMode = "assist",
        preferences: SessionPreferences | None = None,
        query_text: str | None = None,
    ) -> RiskAssessment:
        """Evaluate evidence and return highest-priority structured assessment."""
        if not observations and not events:
            return RiskAssessment(
                assessment_id=f"rsk_{uuid.uuid4().hex[:12]}",
                priority="informational",
                risk_type="clear_view",
                confidence=1.0,
                reason="No active objects or hazards detected in the current frame.",
                evidence_ids=[],
                spatial_relation="none",
                temporal_relation="stationary",
                requires_interruption=False,
            )

        enabled_categories = (
            set(preferences.enabled_categories)
            if preferences
            else set(HIGH_HAZARD_OBJECTS | MODERATE_HAZARD_OBJECTS)
        )
        alert_sensitivity = preferences.alert_sensitivity if preferences else "high"

        highest_priority: RiskPriority = "informational"
        highest_score = 0
        selected_reason = ""
        selected_risk_type = "general_observation"
        selected_evidence_ids: list[str] = []
        selected_spatial = "none"
        selected_temporal = "stationary"
        requires_interruption = False
        highest_confidence = 0.5

        # 1. Evaluate temporal events first (moving / approaching hazards)
        for event in events:
            obj_class = event.object_class.lower()
            if obj_class not in enabled_categories and obj_class != "text":
                continue

            event_type = event.event_type
            direction = event.direction
            movement = event.movement

            # A. Approaching high-hazard vehicle or bicycle -> CRITICAL
            if obj_class in HIGH_HAZARD_OBJECTS and movement == "approaching":
                score = 50
                prio: RiskPriority = "critical"
                reason = f"Approaching {obj_class} detected on your {direction}."
                r_type = "approaching_hazard"
                interruption = True
            # B. Other approaching object -> HIGH
            elif movement == "approaching":
                score = 40
                prio = "high"
                reason = f"Approaching {obj_class} detected on your {direction}."
                r_type = "approaching_object"
                interruption = alert_sensitivity == "high"
            # C. Newly appeared object in path (center) -> HIGH or MEDIUM
            elif event_type == "OBJECT_APPEARED" and direction == "center":
                score = 40 if obj_class in HIGH_HAZARD_OBJECTS else 30
                prio = "high" if obj_class in HIGH_HAZARD_OBJECTS else "medium"
                reason = f"{obj_class.capitalize()} appeared directly ahead."
                r_type = "new_obstacle"
                interruption = False
            # D. Text detected -> MEDIUM (or HIGH in Ask mode reading)
            elif event_type == "OCR_DETECTED":
                score = 35 if mode == "ask" else 25
                prio = "high" if mode == "ask" else "medium"
                reason = "Sign or text detected in view."
                r_type = "text_reading"
                interruption = False
            else:
                score = 20
                prio = "low"
                reason = f"{obj_class.capitalize()} on your {direction}."
                r_type = "environmental_item"
                interruption = False

            if score > highest_score:
                highest_score = score
                highest_priority = prio
                selected_reason = reason
                selected_risk_type = r_type
                selected_evidence_ids = event.evidence_ids
                selected_spatial = direction
                selected_temporal = movement
                requires_interruption = interruption
                highest_confidence = event.confidence

        # 2. Evaluate static spatial proximity from observations
        for obs in observations:
            obj_class = obs.object_class.lower()
            if obj_class not in enabled_categories:
                continue

            spatial = obs.spatial
            prox = spatial.relative_proximity
            horiz = spatial.horizontal
            ground = spatial.ground_relation

            # Center ground obstacle in immediate proximity -> CRITICAL
            if horiz == "center" and prox == "immediate" and (
                ground == "ground_obstacle" or obj_class in HIGH_HAZARD_OBJECTS
            ):
                score = 50
                prio = "critical"
                reason = f"Immediate obstacle ({obj_class}) directly in your path."
                r_type = "immediate_obstacle"
                interruption = True
            # Near obstacle in center -> HIGH
            elif horiz == "center" and prox == "near":
                score = 40
                prio = "high"
                reason = f"{obj_class.capitalize()} directly ahead in your path."
                r_type = "path_obstacle"
                interruption = alert_sensitivity == "high"
            # Immediate proximity on left/right -> HIGH
            elif prox == "immediate":
                score = 38
                prio = "high"
                reason = f"{obj_class.capitalize()} close on your {horiz}."
                r_type = "peripheral_proximity"
                interruption = False
            # Near proximity on left/right -> MEDIUM
            elif prox == "near":
                score = 28
                prio = "medium"
                reason = f"{obj_class.capitalize()} on your {horiz}."
                r_type = "peripheral_item"
                interruption = False
            else:
                score = 15
                prio = "low" if mode != "explore" else "informational"
                reason = f"{obj_class.capitalize()} in view on your {horiz}."
                r_type = "ambient_observation"
                interruption = False

            if score > highest_score:
                highest_score = score
                highest_priority = prio
                selected_reason = reason
                selected_risk_type = r_type
                selected_evidence_ids = [obs.observation_id]
                selected_spatial = f"{prox}_{horiz}"
                selected_temporal = "stationary"
                requires_interruption = interruption
                highest_confidence = obs.confidence

        # In Explore mode, elevate richness without claiming high hazard
        if mode == "explore" and highest_priority in {"low", "informational"}:
            highest_priority = "informational"
            selected_reason = f"Scene contains {len(observations)} visible objects."

        return RiskAssessment(
            assessment_id=f"rsk_{uuid.uuid4().hex[:12]}",
            priority=highest_priority,
            risk_type=selected_risk_type,
            confidence=round(highest_confidence, 2),
            reason=selected_reason,
            evidence_ids=selected_evidence_ids,
            spatial_relation=selected_spatial,
            temporal_relation=selected_temporal,
            requires_interruption=requires_interruption,
        )
