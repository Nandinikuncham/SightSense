"""Text-To-Speech (TTS) service package for SightSense."""

from services.tts.tts_service import (
    LocalMockTTSService,
    PollyTTSService,
    TTSService,
)

__all__ = ["TTSService", "LocalMockTTSService", "PollyTTSService"]
