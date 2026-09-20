
"""Text-To-Speech (TTS) service for SightSense.

Audio generation occurs strictly AFTER narration passes the SafetyValidator.
TTS returns both metadata and actual audio bytes when audio is available.
"""

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from sightsense_api.core.logging import get_logger
from sightsense_api.core.models import AudioOutput, LanguageCode, Narration

logger = get_logger("services.tts")


@dataclass
class TTSResult:
    """TTS metadata and optional playable MP3 bytes."""

    output: AudioOutput
    audio_bytes: bytes | None


class TTSService(ABC):
    """Abstract TTS service interface."""

    @abstractmethod
    async def synthesize_speech(
        self,
        narration: Narration,
        analysis_id: str,
        voice_id: str | None = None,
        speed: float = 1.0,
    ) -> TTSResult:
        """Synthesize narration and return metadata plus optional MP3 bytes."""
        ...


class LocalMockTTSService(TTSService):
    """Offline mock provider.

    This provider does not generate audio bytes. It must not claim to
    provide a playable MP3 URL.
    """

    async def synthesize_speech(
        self,
        narration: Narration,
        analysis_id: str,
        voice_id: str | None = None,
        speed: float = 1.0,
    ) -> TTSResult:
        safe_speed = max(0.5, min(speed, 2.0))
        word_count = max(1, len(narration.text.split()))
        duration = round((word_count / 2.5) / safe_speed, 2)

        output = AudioOutput(
            audio_id=f"aud_{uuid.uuid4().hex[:12]}",
            analysis_id=analysis_id,
            language=narration.language,
            voice=voice_id or "Aditi",
            speed=safe_speed,
            duration_seconds=duration,
            audio_url=None,
            status="pending",
            priority=narration.priority,
        )

        return TTSResult(output=output, audio_bytes=None)


class PollyTTSService(TTSService):
    """Amazon Polly TTS provider."""

    VOICE_MAP: dict[LanguageCode, str] = {
        "en-IN": "Aditi",
        "hi-IN": "Aditi",
        "te-IN": "Kajal",
    }

    def __init__(self, region_name: str = "ap-south-1") -> None:
        self.polly = boto3.client("polly", region_name=region_name)
        self.mock_fallback = LocalMockTTSService()

    async def synthesize_speech(
        self,
        narration: Narration,
        analysis_id: str,
        voice_id: str | None = None,
        speed: float = 1.0,
    ) -> TTSResult:
        selected_voice = voice_id or self.VOICE_MAP.get(
            narration.language, "Aditi"
        )

        safe_speed = max(0.5, min(speed, 2.0))
        rate_percent = int(safe_speed * 100)

        # Escape narration text before embedding it in SSML.
        import html

        escaped_text = html.escape(narration.text)
        ssml_text = (
            f"<speak><prosody rate='{rate_percent}%'>"
            f"{escaped_text}"
            f"</prosody></speak>"
        )

        try:
            response = self.polly.synthesize_speech(
                Engine="standard",
                OutputFormat="mp3",
                Text=ssml_text,
                TextType="ssml",
                VoiceId=selected_voice,
            )

            audio_stream = response.get("AudioStream")
            if audio_stream is None:
                raise RuntimeError("Polly returned no audio stream.")

            try:
                audio_bytes = audio_stream.read()
            finally:
                audio_stream.close()

            if not audio_bytes:
                raise RuntimeError("Polly returned an empty audio stream.")

            word_count = max(1, len(narration.text.split()))
            duration = round((word_count / 2.5) / safe_speed, 2)

            output = AudioOutput(
                audio_id=f"aud_{uuid.uuid4().hex[:12]}",
                analysis_id=analysis_id,
                language=narration.language,
                voice=selected_voice,
                speed=safe_speed,
                duration_seconds=duration,
                # Set to a working API URL after the API persists the bytes.
                audio_url=None,
                status="synthesized",
                priority=narration.priority,
            )

            return TTSResult(
                output=output,
                audio_bytes=bytes(audio_bytes),
            )

        except (ClientError, BotoCoreError, Exception) as exc:
            logger.warning(
                "Polly synthesis failed; falling back to mock TTS.",
                extra={
                    "analysis_id": analysis_id,
                    "error_type": type(exc).__name__,
                },
            )

            return await self.mock_fallback.synthesize_speech(
                narration=narration,
                analysis_id=analysis_id,
                voice_id=selected_voice,
                speed=safe_speed,
            )