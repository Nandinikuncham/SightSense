"""Spatial Reasoning Engine for SightSense.

Transforms raw 2D bounding boxes into relative directional, vertical,
and proximity relations with quantified uncertainty.
Never claims exact geometric distance without certified depth sensors.
"""

from typing import Literal

from sightsense_api.core.models import BoundingBox, SpatialRelation

OBSTACLE_CLASSES = {
    "stairs",
    "curb",
    "pothole",
    "pole",
    "fire hydrant",
    "chair",
    "table",
    "bench",
    "bicycle",
    "motorcycle",
    "car",
    "dog",
    "trash can",
}


class SpatialEngine:
    """Computes spatial relations and uncertainty from normalized bounding box coordinates."""

    def __init__(
        self,
        left_boundary: float = 0.35,
        right_boundary: float = 0.65,
        upper_boundary: float = 0.35,
        ground_boundary: float = 0.65,
    ) -> None:
        self.left_boundary = left_boundary
        self.right_boundary = right_boundary
        self.upper_boundary = upper_boundary
        self.ground_boundary = ground_boundary

    def compute_spatial_relation(
        self,
        bbox: BoundingBox,
        object_class: str = "",
        detection_confidence: float = 1.0,
    ) -> SpatialRelation:
        """Derive direction, vertical zone, proximity, and uncertainty."""
        cx = bbox.center_x
        cy = bbox.center_y
        area = bbox.area

        # 1. Horizontal direction
        if cx < self.left_boundary:
            horizontal: Literal["left", "center", "right"] = "left"
        elif cx > self.right_boundary:
            horizontal = "right"
        else:
            horizontal = "center"

        # 2. Vertical zone
        if cy < self.upper_boundary:
            vertical: Literal["upper", "middle", "ground_level"] = "upper"
        elif cy > self.ground_boundary or bbox.y_max > self.ground_boundary:
            vertical = "ground_level"
        else:
            vertical = "middle"

        # 3. Relative proximity estimate (based on scale and ground baseline)
        if area >= 0.20 or (bbox.y_max >= 0.85 and area >= 0.12):
            proximity: Literal["immediate", "near", "moderate", "distant"] = "immediate"
        elif area >= 0.06 or bbox.y_max >= 0.70:
            proximity = "near"
        elif area >= 0.015:
            proximity = "moderate"
        else:
            proximity = "distant"

        # 4. Ground relation
        is_obstacle_type = object_class.lower() in OBSTACLE_CLASSES
        if vertical == "ground_level" and is_obstacle_type:
            ground_rel: Literal["ground_obstacle", "elevated", "overhead", "none"] = (
                "ground_obstacle"
            )
        elif vertical == "upper":
            ground_rel = "overhead"
        elif vertical == "middle":
            ground_rel = "elevated"
        else:
            ground_rel = "none"

        # 5. Uncertainty calculation
        # Uncertainty is higher when object center is right on the boundary between left/center or center/right
        boundary_dist_left = abs(cx - self.left_boundary)
        boundary_dist_right = abs(cx - self.right_boundary)
        min_boundary_dist = min(boundary_dist_left, boundary_dist_right)

        boundary_penalty = max(0.0, 0.15 - min_boundary_dist) if min_boundary_dist < 0.15 else 0.0
        confidence = max(0.2, min(1.0, detection_confidence - boundary_penalty))

        return SpatialRelation(
            horizontal=horizontal,
            vertical=vertical,
            relative_proximity=proximity,
            ground_relation=ground_rel,
            confidence=round(confidence, 2),
        )
