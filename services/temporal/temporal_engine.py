"""Temporal Reasoning Engine for SightSense.

Tracks environmental objects across frames, detects movement and approach,
and suppresses repetitive alerts for persistent stationary items.
"""

import uuid
from datetime import UTC, datetime
from typing import Literal

from sightsense_api.core.models import (
    BoundingBox,
    Observation,
    TemporalEvent,
)


def compute_iou(box1: BoundingBox, box2: BoundingBox) -> float:
    """Compute Intersection over Union between two normalized bounding boxes."""
    x_left = max(box1.x_min, box2.x_min)
    y_top = max(box1.y_min, box2.y_min)
    x_right = min(box1.x_max, box2.x_max)
    y_bottom = min(box1.y_max, box2.y_max)

    if x_right < x_left or y_bottom < y_top:
        return 0.0

    intersection_area = (x_right - x_left) * (y_bottom - y_top)
    box1_area = box1.area
    box2_area = box2.area
    union_area = box1_area + box2_area - intersection_area

    if union_area <= 0:
        return 0.0

    return intersection_area / union_area


class TrackedObject:
    """Historical tracking state for an individual object."""

    def __init__(self, observation: Observation) -> None:
        self.track_id: str = f"trk_{uuid.uuid4().hex[:8]}"
        self.object_class: str = observation.object_class
        self.last_bbox: BoundingBox = observation.bounding_box
        self.last_observation_id: str = observation.observation_id
        self.last_seen: datetime = datetime.now(UTC)
        self.last_alert_time: datetime | None = None
        self.consecutive_frames: int = 1
        self.movement_state: Literal["approaching", "receding", "lateral", "stationary"] = (
            "stationary"
        )


class TemporalEngine:
    """Correlates observations across sequential frames to emit temporal events."""

    def __init__(
        self,
        iou_threshold: float = 0.25,
        approach_scale_threshold: float = 1.25,  # 25% scale increase indicates approach
        recede_scale_threshold: float = 0.80,    # 20% scale decrease indicates receding
        suppression_window_seconds: float = 8.0, # Quiet window for persistent stationary objects
    ) -> None:
        self.iou_threshold = iou_threshold
        self.approach_scale_threshold = approach_scale_threshold
        self.recede_scale_threshold = recede_scale_threshold
        self.suppression_window_seconds = suppression_window_seconds

        # Map session_id -> track_id -> TrackedObject
        self._session_tracks: dict[str, dict[str, TrackedObject]] = {}

    def process_observations(
        self,
        session_id: str,
        analysis_id: str,
        current_observations: list[Observation],
    ) -> list[TemporalEvent]:
        """Compare current observations with session history and generate temporal events."""
        now = datetime.now(UTC)
        tracks = self._session_tracks.setdefault(session_id, {})
        events: list[TemporalEvent] = []

        unmatched_observations = list(current_observations)
        matched_tracks: set[str] = set()

        # 1. Match current observations to existing tracks using IoU + class match
        for obs in current_observations:
            best_track_id: str | None = None
            best_iou = 0.0

            for track_id, track in tracks.items():
                if track.object_class != obs.object_class:
                    continue

                iou = compute_iou(obs.bounding_box, track.last_bbox)
                if iou > self.iou_threshold and iou > best_iou:
                    best_iou = iou
                    best_track_id = track_id

            if best_track_id and best_track_id not in matched_tracks:
                track = tracks[best_track_id]
                matched_tracks.add(best_track_id)
                if obs in unmatched_observations:
                    unmatched_observations.remove(obs)

                # Determine movement dynamics
                prev_area = track.last_bbox.area
                curr_area = obs.bounding_box.area
                scale_ratio = curr_area / max(prev_area, 0.0001)

                dx = abs(obs.bounding_box.center_x - track.last_bbox.center_x)

                if scale_ratio >= self.approach_scale_threshold:
                    movement: Literal["approaching", "receding", "lateral", "stationary"] = (
                        "approaching"
                    )
                    event_type = "OBJECT_APPROACHING"
                elif scale_ratio <= self.recede_scale_threshold:
                    movement = "receding"
                    event_type = "OBJECT_RECEDING"
                elif dx >= 0.15:
                    movement = "lateral"
                    event_type = "OBJECT_MOVING"
                else:
                    movement = "stationary"
                    event_type = "OBJECT_PERSISTENT"

                track.movement_state = movement
                track.last_bbox = obs.bounding_box
                track.last_observation_id = obs.observation_id
                track.last_seen = now
                track.consecutive_frames += 1

                # Check suppression policy:
                # Approaching objects always generate events; stationary persistent items are suppressed within the quiet window
                is_suppressed = False
                if movement == "stationary" and track.last_alert_time:
                    elapsed = (now - track.last_alert_time).total_seconds()
                    if elapsed < self.suppression_window_seconds:
                        is_suppressed = True

                if not is_suppressed:
                    track.last_alert_time = now
                    events.append(
                        TemporalEvent(
                            analysis_id=analysis_id,
                            event_type=event_type,
                            object_class=obs.object_class,
                            direction=obs.spatial.horizontal,
                            movement=movement,
                            confidence=obs.confidence,
                            evidence_ids=[obs.observation_id],
                        )
                    )

        # 2. Handle new unmatched observations (new arrivals)
        for obs in unmatched_observations:
            new_track = TrackedObject(obs)
            new_track.last_alert_time = now
            tracks[new_track.track_id] = new_track

            # Emit OCR event if text detected
            if obs.ocr_text:
                events.append(
                    TemporalEvent(
                        analysis_id=analysis_id,
                        event_type="OCR_DETECTED",
                        object_class="text",
                        direction=obs.spatial.horizontal,
                        movement="stationary",
                        confidence=obs.ocr_confidence or 0.9,
                        evidence_ids=[obs.observation_id],
                    )
                )

            events.append(
                TemporalEvent(
                    analysis_id=analysis_id,
                    event_type="OBJECT_APPEARED",
                    object_class=obs.object_class,
                    direction=obs.spatial.horizontal,
                    movement="stationary",
                    confidence=obs.confidence,
                    evidence_ids=[obs.observation_id],
                )
            )

        # 3. Clean up stale tracks not seen for > 15 seconds
        stale_track_ids = [
            tid
            for tid, t in tracks.items()
            if (now - t.last_seen).total_seconds() > 15.0
        ]
        for tid in stale_track_ids:
            del tracks[tid]

        return events

    def clear_session(self, session_id: str) -> None:
        """Clear temporal history when session closes."""
        self._session_tracks.pop(session_id, None)
