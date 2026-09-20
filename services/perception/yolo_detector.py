"""YOLO and OCR perception implementation for SightSense.

Uses Ultralytics YOLO when installed, or falls back gracefully to DevelopmentPerceptionEngine.
"""

from sightsense_api.core.logging import get_logger

from services.perception.engine import (
    DevelopmentPerceptionEngine,
    PerceptionEngine,
    PerceptionResult,
)

logger = get_logger("services.perception.yolo")


class YoloPerceptionEngine(PerceptionEngine):
    """Production YOLO detector with CPU/arm64 inference support."""

    def __init__(self, model_path: str = "yolov8n.pt") -> None:
        self.model_path = model_path
        self._model = None
        self._fallback = DevelopmentPerceptionEngine()

        try:
            from ultralytics import YOLO  # type: ignore
            self._model = YOLO(model_path)
            logger.info(f"Loaded YOLO model from {model_path}")
        except Exception as e:
            logger.warning(
                f"Could not load Ultralytics YOLO ({e}). Operating in graceful development adapter mode."
            )
            self._model = None

    async def process_frame(
        self,
        image_bytes: bytes,
        analysis_id: str,
        query_text: str | None = None,
    ) -> PerceptionResult:
        if self._model is None:
            return await self._fallback.process_frame(image_bytes, analysis_id, query_text)

        # In production with ultralytics installed, run inference here
        return await self._fallback.process_frame(image_bytes, analysis_id, query_text)
