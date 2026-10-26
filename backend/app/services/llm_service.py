"""
llm_service.py
Calls HuggingFace Inference API (OpenAI-compatible endpoint) with a compact
visual report input and returns a validated structured JSON report.
No raw video, no frame arrays, no audio data is ever sent.
"""
import json
import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

PROMPT_VERSION = "1.0"

SYSTEM_PROMPT = """You are a professional NTS (Non-Technical Skills) behavioral analyst producing structured visual reports.

STRICT RULES — you MUST follow all of them:
1. Use ONLY the visual data provided in the input JSON. Never invent measurements.
2. Never fabricate observations. If data is unavailable, return null or "not_assessed".
3. Never make psychological diagnoses or personality claims.
4. Never infer internal emotions as factual states (e.g. do not say "the person felt nervous").
5. Never call detection_confidence the person's psychological confidence.
6. Never claim leadership solely from head movement alone.
7. Never claim teamwork solely from posture alone.
8. Never claim influence solely from gaze alone.
9. Resilience is "resilience-related behavioral consistency" — NOT a psychological trait.
10. Decision-making MUST always be returned as not_assessed in visual-only mode.
11. Every strength must reference a specific measured metric or observation.
12. Every development area must be grounded in specific measured data.
13. Avoid generic corporate language like "a great team player" without evidence.
14. Do not mention STT, speech, transcription, or audio — this is visual-only.
15. Only use information from the supplied JSON input.
16. NTS scores must be on a 0-100 scale or null if insufficient evidence.
17. Confidence values must be 0.0-1.0 or null.

OUTPUT: Return ONLY a valid JSON object matching this exact schema. No markdown, no explanation, no preamble.
{
  "participant_id": "string",
  "executive_summary": "2-4 paragraph string describing observed visual behavior only",
  "visual_profile": {
    "head_movement": "string",
    "gaze": "string",
    "posture": "string",
    "hands_gestures": "string",
    "facial_affect": "string"
  },
  "nts_visual_profile": {
    "communication": {"score": null_or_0_to_100, "confidence": null_or_0_to_1, "evidence": ["list of strings"], "limitations": ["list of strings"]},
    "teamwork": {"score": null_or_0_to_100, "confidence": null_or_0_to_1, "evidence": ["list of strings"], "limitations": ["list of strings"]},
    "leadership": {"score": null_or_0_to_100, "confidence": null_or_0_to_1, "evidence": ["list of strings"], "limitations": ["list of strings"]},
    "influence": {"score": null_or_0_to_100, "confidence": null_or_0_to_1, "evidence": ["list of strings"], "limitations": ["list of strings"]},
    "resilience_consistency": {"score": null_or_0_to_100, "confidence": null_or_0_to_1, "evidence": ["list of strings"], "limitations": ["list of strings"]},
    "decision_making": {"score": null, "status": "not_assessed", "reason": "Requires semantic/task-level evidence unavailable in visual-only mode"}
  },
  "strengths": ["3-5 strings, each referencing a specific measured behavior"],
  "development_areas": ["3-5 strings, each grounded in measured data"],
  "recommendations": ["3-5 specific actionable strings based on the participant's actual data"],
  "detailed_summary": "string — comprehensive paragraph covering overall visual behavior, temporal patterns, strongest/weakest indicators, limitations",
  "limitations": ["list of strings explicitly stating what this report cannot assess"]
}"""


def _build_user_prompt(report_input: dict[str, Any]) -> str:
    compact = json.dumps(report_input, indent=2)
    return f"""Generate an NTS visual behavioral report for the following participant data.

PARTICIPANT VISUAL DATA:
{compact}

Return ONLY the JSON report. No explanation, no markdown fences."""


async def call_llm(report_input: dict[str, Any]) -> dict[str, Any]:
    """
    Calls HuggingFace Inference API and returns validated structured report JSON.
    Raises ValueError on invalid output or LLM failure.
    """
    api_key = settings.LLM_API_KEY
    if not api_key:
        raise ValueError("LLM_API_KEY is not configured.")

    groq_endpoint = "https://api.groq.com/openai/v1/chat/completions"

    payload = {
        "model": settings.LLM_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_prompt(report_input)},
        ],
        "max_tokens": settings.LLM_MAX_OUTPUT_TOKENS,
        "temperature": 0.3,
        "stream": False,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    logger.info("Calling Groq LLM model=%s for track=%s",
                settings.LLM_MODEL, report_input.get("participant_track_id"))

    async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT) as client:
        try:
            resp = await client.post(groq_endpoint, json=payload, headers=headers)
        except httpx.TimeoutException as e:
            raise ValueError(f"LLM request timed out after {settings.LLM_TIMEOUT}s: {e}") from e
        except httpx.RequestError as e:
            raise ValueError(f"LLM network error: {e}") from e

    if resp.status_code == 429:
        raise ValueError("LLM rate limit reached. Please try again later.")
    if resp.status_code not in (200, 201):
        raise ValueError(f"LLM API error {resp.status_code}: {resp.text[:300]}")

    try:
        data = resp.json()
    except Exception as e:
        raise ValueError(f"LLM returned non-JSON response: {e}") from e

    # Extract content from OpenAI-compatible response
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as e:
        raise ValueError(f"Unexpected LLM response structure: {data}") from e

    # Parse the JSON content
    try:
        # Strip any accidental markdown fences
        content = content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        report_json = json.loads(content)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM returned invalid JSON: {e}\nContent: {content[:500]}") from e

    # Validate required top-level keys
    required_keys = {
        "executive_summary", "visual_profile", "nts_visual_profile",
        "strengths", "development_areas", "recommendations",
        "detailed_summary", "limitations"
    }
    missing = required_keys - set(report_json.keys())
    if missing:
        raise ValueError(f"LLM report missing required keys: {missing}")

    # Ensure decision_making is always not_assessed
    nts = report_json.get("nts_visual_profile", {})
    nts["decision_making"] = {
        "score": None,
        "status": "not_assessed",
        "reason": "Requires semantic/task-level evidence unavailable in visual-only mode",
    }
    report_json["nts_visual_profile"] = nts

    # Always inject participant_id
    report_json["participant_id"] = report_input["participant_track_id"]

    logger.info("LLM report generated successfully for track=%s", report_input.get("participant_track_id"))
    return report_json
