
"""Master Pipeline Orchestrator for SightSense.

Pipeline:
Perception -> Spatial -> Temporal -> Risk -> Narration
-> Safety Validation -> TTS.

Audio is persisted only after narration passes safety validation.
"""

import time
import uuid
from datetime import UTC, datetime

from sightsense_api.core.config import Settings, get_settings
from sightsense_api.core.logging import get_logger
from sightsense_api.core.models import Analysis, Session, SessionMode
from sightsense_api.core.storage import StorageInterface

from services.narration.narration_engine import (
    BedrockNarrationProvider,
    NarrationProvider,
    TemplateNarrationProvider,
)
from services.perception.engine import (
    DevelopmentPerceptionEngine,
    PerceptionEngine,
)
from services.perception.yolo_detector import YoloPerceptionEngine
from services.risk.risk_engine import RiskEngine
from services.safety.safety_validator import SafetyValidator
from services.spatial.spatial_engine import SpatialEngine
from services.temporal.temporal_engine import TemporalEngine
from services.tts.tts_service import (
    LocalMockTTSService,
    PollyTTSService,
    TTSService,
)

logger = get_logger("services.orchestrator")


class PipelineOrchestrator:
    """Coordinates end-to-end vision processing."""

    def __init__(
        self,
        settings: Settings | None = None,
        perception_engine: PerceptionEngine | None = None,
        narration_provider: NarrationProvider | None = None,
        tts_service: TTSService | None = None,
    ) -> None:
        self.settings = settings or get_settings()

        # 1. Perception
        if perception_engine:
            self.perception = perception_engine
        elif self.settings.USE_LOCAL_ADAPTERS:
            self.perception = DevelopmentPerceptionEngine()
        else:
            self.perception = YoloPerceptionEngine()

        # 2. Spatial reasoning
        self.spatial = SpatialEngine()

        # 3. Temporal reasoning
        self.temporal = TemporalEngine(
            suppression_window_seconds=(
                self.settings.ASSIST_FRAME_THROTTLE_SECONDS * 4
            )
        )

        # 4. Risk assessment
        self.risk_engine = RiskEngine()

        # 5. Narration
        if narration_provider:
            self.narration_provider = narration_provider
        elif self.settings.ENABLE_BEDROCK_NARRATION:
            self.narration_provider = BedrockNarrationProvider(
                model_id=self.settings.BEDROCK_MODEL_ID,
                region_name=self.settings.AWS_REGION,
            )
        else:
            self.narration_provider = TemplateNarrationProvider()

        # 6. Independent safety validation
        self.safety_validator = SafetyValidator(min_confidence=0.50)

        # 7. TTS
        if tts_service:
            self.tts = tts_service
        elif self.settings.ENABLE_POLLY_TTS:
            self.tts = PollyTTSService(
                region_name=self.settings.AWS_REGION
            )
        else:
            self.tts = LocalMockTTSService()

    async def execute_pipeline(
        self,
        session: Session,
        image_bytes: bytes,
        analysis_id: str | None = None,
        query_text: str | None = None,
        mode_override: SessionMode | None = None,
        storage: StorageInterface | None = None,
    ) -> Analysis:
        """Run the complete pipeline and optionally persist generated audio."""

        start_time = time.perf_counter()
        aid = analysis_id or f"ana_{uuid.uuid4().hex[:12]}"
        effective_mode = mode_override or session.mode
        prefs = session.preferences

        logger.info(
            "Starting pipeline analysis",
            extra={
                "analysis_id": aid,
                "session_id": session.session_id,
                "mode": effective_mode,
            },
        )

        # Step 1: Perception
        perc_res = await self.perception.process_frame(
            image_bytes,
            aid,
            query_text,
        )
        raw_observations = perc_res.observations

        # Step 2: Spatial refinement
        refined_observations = []

        for obs in raw_observations:
            spatial_rel = self.spatial.compute_spatial_relation(
                obs.bounding_box,
                obs.object_class,
                obs.confidence,
            )

            refined = obs.model_copy(
                update={"spatial": spatial_rel}
            )
            refined_observations.append(refined)

        # Step 3: Temporal reasoning
        temporal_events = self.temporal.process_observations(
            session_id=session.session_id,
            analysis_id=aid,
            current_observations=refined_observations,
        )

        # Step 4: Risk assessment
        risk = self.risk_engine.evaluate(
            observations=refined_observations,
            events=temporal_events,
            mode=effective_mode,
            preferences=prefs,
            query_text=query_text,
        )

        # Step 5: Narration generation
        candidate_narration = (
            await self.narration_provider.generate_narration(
                risk=risk,
                events=temporal_events,
                observations=refined_observations,
                mode=effective_mode,
                language=prefs.language,
                query_text=query_text,
            )
        )

        # Step 6: Mandatory safety validation
        val_result = self.safety_validator.validate(
            narration=candidate_narration,
            risk=risk,
            events=temporal_events,
            observations=refined_observations,
        )

        approved_narration = val_result.safe_narration

        # Step 7: TTS only after safety validation
        tts_result = await self.tts.synthesize_speech(
            narration=approved_narration,
            analysis_id=aid,
            speed=prefs.speech_speed,
        )

        audio = tts_result.output
        audio_bytes = tts_result.audio_bytes

        # Persist actual generated audio bytes.
        if audio_bytes:
            if storage is None:
                raise RuntimeError(
                    "Storage is required to persist generated audio."
                )

            audio_object_key = (
                f"users/{session.user_id}/"
                f"sessions/{session.session_id}/"
                f"analyses/{aid}/audio.mp3"
            )

            await storage.put_object_bytes(
                object_key=audio_object_key,
                data=audio_bytes,
                content_type="audio/mpeg",
            )

            audio.audio_url = f"/api/v1/audio/{aid}"
        else:
            # No playable audio was generated.
            audio.audio_url = None

        duration_ms = round(
            (time.perf_counter() - start_time) * 1000,
            2,
        )

        logger.info(
            "Pipeline analysis completed",
            extra={
                "analysis_id": aid,
                "duration_ms": duration_ms,
                "priority": risk.priority,
                "safety_valid": val_result.is_valid,
                "audio_available": bool(audio_bytes),
            },
        )

        return Analysis(
            analysis_id=aid,
            session_id=session.session_id,
            user_id=session.user_id,
            status="completed",
            mode=effective_mode,
            query_text=query_text,
            observations=refined_observations,
            events=temporal_events,
            risk_assessment=risk,
            narration=approved_narration,
            audio=audio,
            created_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        )


# Singleton orchestrator
_global_orchestrator: PipelineOrchestrator | None = None


def get_pipeline_orchestrator() -> PipelineOrchestrator:
    """Return the shared orchestrator instance."""

    global _global_orchestrator

    if _global_orchestrator is None:
        _global_orchestrator = PipelineOrchestrator()

    return _global_orchestrator