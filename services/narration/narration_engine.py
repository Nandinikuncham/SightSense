"""Grounded Narration Engine for SightSense.

Translates structured evidence, events, and risk assessments into concise,
natural language. Generative AI is constrained strictly to formatting structured facts.
"""

import json
import uuid
from abc import ABC, abstractmethod

import boto3
from botocore.exceptions import ClientError
from sightsense_api.core.logging import get_logger
from sightsense_api.core.models import (
    LanguageCode,
    Narration,
    Observation,
    RiskAssessment,
    SessionMode,
    TemporalEvent,
)

logger = get_logger("services.narration")


class NarrationProvider(ABC):
    """Abstract narration generator interface."""

    @abstractmethod
    async def generate_narration(
        self,
        risk: RiskAssessment,
        events: list[TemporalEvent],
        observations: list[Observation],
        mode: SessionMode = "assist",
        language: LanguageCode = "en-IN",
        query_text: str | None = None,
    ) -> Narration: ...


class TemplateNarrationProvider(NarrationProvider):
    """Deterministic, high-speed, zero-cost template narration generator.

    Guarantees 100% factual grounding and prevents any hallucination.
    """

    TRANSLATIONS = {
        "en-IN": {
            "approaching": "An approaching {object} is on your {direction}.",
            "approaching_center": "Caution: An approaching {object} is directly ahead.",
            "immediate_obstacle": "Caution: {object} directly ahead in your path.",
            "path_obstacle": "{object} ahead in your path.",
            "peripheral": "{object} on your {direction}.",
            "text": "The sign reads: {text}.",
            "clear": "Path ahead appears clear of detected obstacles.",
            "explore_summary": "In view: {items}.",
        },
        "hi-IN": {
            "approaching": "आपकी {direction} ओर एक {object} आ रहा है।",
            "approaching_center": "सावधान: आपके ठीक सामने एक {object} आ रहा है।",
            "immediate_obstacle": "सावधान: आपके रास्ते में ठीक सामने {object} है।",
            "path_obstacle": "आगे आपके रास्ते में {object} है।",
            "peripheral": "आपकी {direction} ओर {object} है।",
            "text": "बोर्ड पर लिखा है: {text}।",
            "clear": "आगे कोई ज्ञात रुकावट नहीं दिख रही है।",
            "explore_summary": "दिखाई दे रहा है: {items}।",
        },
        "te-IN": {
            "approaching": "మీ {direction} వైపు ఒక {object} వస్తోంది.",
            "approaching_center": "జాగ్రత్త: మీ ముందు నేరుగా ఒక {object} వస్తోంది.",
            "immediate_obstacle": "జాగ్రత్త: మీ దారిలో నేరుగా {object} ఉంది.",
            "path_obstacle": "మీ ముందు దారిలో {object} ఉంది.",
            "peripheral": "మీ {direction} వైపు {object} ఉంది.",
            "text": "బోర్డుపై ఇలా ఉంది: {text}.",
            "clear": "ముందు ఎటువంటి అడ్డంకులు కనిపించడం లేదు.",
            "explore_summary": "కనిపిస్తున్నవి: {items}.",
        },
    }

    DIRECTION_MAP = {
        "hi-IN": {"left": "बाएं", "right": "दाएं", "center": "सामने"},
        "te-IN": {"left": "ఎడమ", "right": "కుడి", "center": "ముందు"},
        "en-IN": {"left": "left", "right": "right", "center": "center"},
    }

    async def generate_narration(
        self,
        risk: RiskAssessment,
        events: list[TemporalEvent],
        observations: list[Observation],
        mode: SessionMode = "assist",
        language: LanguageCode = "en-IN",
        query_text: str | None = None,
    ) -> Narration:
        t = self.TRANSLATIONS.get(language, self.TRANSLATIONS["en-IN"])
        d_map = self.DIRECTION_MAP.get(language, self.DIRECTION_MAP["en-IN"])

        # 1. Ask Mode - Answer specifically if OCR text or targeted object
        if mode == "ask" and query_text:
            # Check for OCR text question
            ocr_obs = next((o for o in observations if o.ocr_text), None)
            if ocr_obs and any(w in query_text.lower() for w in ["read", "sign", "text", "say"]):
                text = t["text"].format(text=ocr_obs.ocr_text)
                return Narration(
                    narration_id=f"nar_{uuid.uuid4().hex[:12]}",
                    text=text,
                    language=language,
                    priority=risk.priority,
                    evidence_ids=[ocr_obs.observation_id],
                    confidence=ocr_obs.ocr_confidence or 0.9,
                    validated=False,
                )

        # 2. Approaching Temporal Events
        approaching_event = next(
            (e for e in events if e.movement == "approaching"), None
        )
        if approaching_event:
            dir_str = d_map.get(approaching_event.direction, approaching_event.direction)
            if approaching_event.direction == "center":
                text = t["approaching_center"].format(
                    object=approaching_event.object_class
                )
            else:
                text = t["approaching"].format(
                    object=approaching_event.object_class, direction=dir_str
                )
            return Narration(
                narration_id=f"nar_{uuid.uuid4().hex[:12]}",
                text=text,
                language=language,
                priority=risk.priority,
                evidence_ids=approaching_event.evidence_ids,
                confidence=approaching_event.confidence,
                validated=False,
            )

        # 3. Static Obstacle Observations
        if risk.risk_type in {"immediate_obstacle", "path_obstacle"}:
            matched_obs = next(
                (o for o in observations if o.observation_id in risk.evidence_ids), None
            )
            obj_name = matched_obs.object_class if matched_obs else "obstacle"
            template_key = (
                "immediate_obstacle" if risk.priority == "critical" else "path_obstacle"
            )
            text = t[template_key].format(object=obj_name)
            return Narration(
                narration_id=f"nar_{uuid.uuid4().hex[:12]}",
                text=text,
                language=language,
                priority=risk.priority,
                evidence_ids=risk.evidence_ids,
                confidence=risk.confidence,
                validated=False,
            )

        # 4. Explore Mode or General Items
        if mode == "explore" and observations:
            items_desc = []
            for obs in observations[:4]:
                dir_str = d_map.get(obs.spatial.horizontal, obs.spatial.horizontal)
                items_desc.append(f"{obs.object_class} on {dir_str}")
            text = t["explore_summary"].format(items=", ".join(items_desc))
            return Narration(
                narration_id=f"nar_{uuid.uuid4().hex[:12]}",
                text=text,
                language=language,
                priority=risk.priority,
                evidence_ids=[o.observation_id for o in observations[:4]],
                confidence=risk.confidence,
                validated=False,
            )

        # 5. Default single object or clear statement
        if observations:
            primary_obs = observations[0]
            dir_str = d_map.get(primary_obs.spatial.horizontal, primary_obs.spatial.horizontal)
            text = t["peripheral"].format(
                object=primary_obs.object_class, direction=dir_str
            )
            return Narration(
                narration_id=f"nar_{uuid.uuid4().hex[:12]}",
                text=text,
                language=language,
                priority=risk.priority,
                evidence_ids=[primary_obs.observation_id],
                confidence=primary_obs.confidence,
                validated=False,
            )

        return Narration(
            narration_id=f"nar_{uuid.uuid4().hex[:12]}",
            text=t["clear"],
            language=language,
            priority="informational",
            evidence_ids=[],
            confidence=1.0,
            validated=False,
        )


class BedrockNarrationProvider(NarrationProvider):
    """Production narration generator using Amazon Bedrock with strict grounding."""

    def __init__(
        self,
        model_id: str = "anthropic.claude-3-5-haiku-20241022-v1:0",
        region_name: str = "ap-south-1",
    ) -> None:
        self.model_id = model_id
        self.bedrock = boto3.client("bedrock-runtime", region_name=region_name)
        self.fallback = TemplateNarrationProvider()

    async def generate_narration(
        self,
        risk: RiskAssessment,
        events: list[TemporalEvent],
        observations: list[Observation],
        mode: SessionMode = "assist",
        language: LanguageCode = "en-IN",
        query_text: str | None = None,
    ) -> Narration:
        # Structured input evidence for Bedrock
        evidence_summary = {
            "mode": mode,
            "language": language,
            "user_query": query_text,
            "risk_assessment": {
                "priority": risk.priority,
                "reason": risk.reason,
                "spatial": risk.spatial_relation,
                "temporal": risk.temporal_relation,
            },
            "events": [
                {
                    "event_type": e.event_type,
                    "object": e.object_class,
                    "direction": e.direction,
                    "movement": e.movement,
                }
                for e in events
            ],
            "observations": [
                {
                    "id": o.observation_id,
                    "class": o.object_class,
                    "direction": o.spatial.horizontal,
                    "proximity": o.spatial.relative_proximity,
                    "ocr_text": o.ocr_text,
                }
                for o in observations[:5]
            ],
        }

        system_prompt = (
            "You are the grounded auditory narration system for SightSense, an assistive vision platform for visually impaired users. "
            "Output a single, concise sentence (max 15 words) communicating the most critical environmental information. "
            "NON-NEGOTIABLE SAFETY RULES:\n"
            "1. Express ONLY facts directly substantiated by the input evidence JSON.\n"
            "2. NEVER invent objects, distances, or events not listed in the evidence.\n"
            "3. NEVER use safety guarantee words like 'safe', 'clear path', 'you can proceed', 'guaranteed', 'no danger'.\n"
            "4. Return ONLY the spoken text, with no explanations or preamble."
        )

        try:
            body = json.dumps(
                {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 100,
                    "temperature": 0.0,
                    "system": system_prompt,
                    "messages": [
                        {
                            "role": "user",
                            "content": f"Evidence: {json.dumps(evidence_summary)}",
                        }
                    ],
                }
            )
            response = self.bedrock.invoke_model(
                modelId=self.model_id,
                contentType="application/json",
                accept="application/json",
                body=body,
            )
            response_body = json.loads(response["body"].read())
            generated_text = response_body["content"][0]["text"].strip()

            return Narration(
                narration_id=f"nar_{uuid.uuid4().hex[:12]}",
                text=generated_text,
                language=language,
                priority=risk.priority,
                evidence_ids=list(risk.evidence_ids),
                confidence=risk.confidence,
                validated=False,
            )
        except (ClientError, Exception) as e:
            logger.warning(f"Bedrock invocation failed ({e}), falling back to template narration.")
            return await self.fallback.generate_narration(
                risk, events, observations, mode, language, query_text
            )
