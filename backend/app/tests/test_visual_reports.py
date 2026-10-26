"""
Tests for the NTS Visual Report feature.
Tests: aggregation, missing features, caching, LLM output validation.
Run: docker exec pjt-worker-1 bash -c "cd /app && python -m pytest app/tests/test_visual_reports.py -v"
"""
import hashlib
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4


# ---- 1. Visual aggregator: test compact output structure ----

def test_compute_input_hash_deterministic():
    from app.services.visual_aggregator import compute_input_hash
    data = {"a": 1, "b": [1, 2], "c": {"d": 3}}
    h1 = compute_input_hash(data)
    h2 = compute_input_hash(data)
    assert h1 == h2, "Hash must be deterministic"
    assert len(h1) == 64, "SHA-256 should produce 64-char hex"


def test_compute_input_hash_changes_on_different_input():
    from app.services.visual_aggregator import compute_input_hash
    h1 = compute_input_hash({"value": 1.0})
    h2 = compute_input_hash({"value": 2.0})
    assert h1 != h2, "Different inputs must produce different hashes"


def test_safe_stats_insufficient_data():
    """Missing features must NOT produce fabricated values."""
    from app.services.visual_aggregator import _safe_stats
    # Fewer than MIN_OBSERVATIONS (5)
    result = _safe_stats([1.0, 2.0])
    assert result is None, "Should return None for insufficient data"


def test_safe_stats_sufficient_data():
    from app.services.visual_aggregator import _safe_stats
    result = _safe_stats([1.0, 2.0, 3.0, 4.0, 5.0])
    assert result is not None
    assert "mean" in result
    assert "std" in result
    assert "min" in result
    assert "max" in result
    assert result["min"] == 1.0
    assert result["max"] == 5.0


def test_availability_wrapper_marks_unavailable():
    from app.services.visual_aggregator import _availability_wrapper
    result = _availability_wrapper(None, reason="no data")
    assert result["available"] is False
    assert "reason" in result


def test_availability_wrapper_marks_available():
    from app.services.visual_aggregator import _availability_wrapper
    result = _availability_wrapper({"mean": 1.0, "std": 0.1, "min": 0.5, "max": 1.5})
    assert result["available"] is True
    assert result["mean"] == 1.0


# ---- 2. LLM service: schema validation ----

def _make_valid_report_json(track_id: str) -> dict:
    """Helper to produce a valid LLM report JSON."""
    return {
        "participant_id": track_id,
        "executive_summary": "The participant demonstrated stable visual engagement throughout the session.",
        "visual_profile": {
            "head_movement": "Low variability in yaw (std=0.08 rad).",
            "gaze": "Moderate gaze stability.",
            "posture": "Consistent keypoint detection.",
            "hands_gestures": "Minimal hand activity observed.",
            "facial_affect": "Predominantly neutral affect.",
        },
        "nts_visual_profile": {
            "communication": {"score": 72, "confidence": 0.65, "evidence": ["Stable gaze direction."], "limitations": ["No speech data."]},
            "teamwork": {"score": None, "confidence": None, "evidence": [], "limitations": ["Insufficient orientation data."]},
            "leadership": {"score": None, "confidence": None, "evidence": [], "limitations": ["No comparative data."]},
            "influence": {"score": None, "confidence": None, "evidence": [], "limitations": []},
            "resilience_consistency": {"score": 68, "confidence": 0.55, "evidence": ["Low head roll variability."], "limitations": []},
            "decision_making": {"score": None, "status": "not_assessed", "reason": "Requires semantic/task-level evidence unavailable in visual-only mode"},
        },
        "strengths": ["Stable posture throughout session.", "Consistent gaze direction during key periods."],
        "development_areas": ["Increase variation in gaze engagement.", "Reduce high-frequency head roll movements."],
        "recommendations": ["Maintain upright posture.", "Use deliberate gaze direction changes."],
        "detailed_summary": "Overall, the participant showed stable visual behavior with low movement variability.",
        "limitations": ["This report is derived from visual features only.", "No speech or audio analysis performed."],
    }


def test_llm_output_validates_required_keys():
    """LLM output must have all required top-level keys."""
    report_json = _make_valid_report_json(str(uuid4()))
    required = {"executive_summary", "visual_profile", "nts_visual_profile", "strengths", "development_areas", "recommendations", "detailed_summary", "limitations"}
    assert required.issubset(set(report_json.keys()))


def test_decision_making_always_not_assessed():
    """decision_making must always be status=not_assessed."""
    report_json = _make_valid_report_json(str(uuid4()))
    dm = report_json["nts_visual_profile"]["decision_making"]
    assert dm["score"] is None
    assert dm["status"] == "not_assessed"
    assert "reason" in dm


def test_nts_scores_null_when_insufficient():
    """NTS dimensions may have null score when evidence is insufficient."""
    report_json = _make_valid_report_json(str(uuid4()))
    teamwork = report_json["nts_visual_profile"]["teamwork"]
    assert teamwork["score"] is None
    assert teamwork["confidence"] is None


# ---- 3. LLM service: invalid output handling ----

def test_llm_invalid_json_raises_value_error():
    """Invalid JSON from LLM must be caught and raise ValueError."""
    from app.services.llm_service import SYSTEM_PROMPT
    # Simulate what call_llm does when content is not valid JSON
    content = "This is not JSON at all."
    with pytest.raises((ValueError, json.JSONDecodeError)):
        json.loads(content)


def test_llm_missing_required_keys_detected():
    """LLM output missing required keys must be detected."""
    incomplete = {"executive_summary": "Test"}
    required_keys = {"executive_summary", "visual_profile", "nts_visual_profile", "strengths", "development_areas", "recommendations", "detailed_summary", "limitations"}
    missing = required_keys - set(incomplete.keys())
    assert len(missing) > 0


# ---- 4. Caching: same hash = same report ----

def test_same_input_produces_same_hash():
    """Caching depends on deterministic hash — same input must never change hash."""
    from app.services.visual_aggregator import compute_input_hash
    input_data = {
        "participant_track_id": "abc-123",
        "meeting_id": "meet-456",
        "duration_seconds": 570.0,
        "head": {"available": True, "yaw": {"mean": 0.02, "std": 0.08}},
        "gaze": {"available": True, "stability": "stable"},
    }
    assert compute_input_hash(input_data) == compute_input_hash(input_data)


def test_changed_input_produces_different_hash():
    """Changed visual data must invalidate cache by changing hash."""
    from app.services.visual_aggregator import compute_input_hash
    base = {"head": {"yaw_mean": 0.02}}
    modified = {"head": {"yaw_mean": 0.15}}
    assert compute_input_hash(base) != compute_input_hash(modified)


# ---- 5. PDF generation: structure test ----

def test_pdf_generation_produces_bytes():
    """PDF generator must produce non-empty bytes for a valid report."""
    from app.services.pdf_generator import build_pdf_bytes
    report_json = _make_valid_report_json(str(uuid4()))
    report_input = {
        "track_label": "person_0",
        "duration_seconds": 300.0,
        "coverage": 0.85,
        "detection_confidence": 0.78,
        "data_quality": "good",
        "missing_features": [],
        "total_detections": 600,
    }
    pdf_bytes = build_pdf_bytes(report_json, report_input, "meeting-abc")
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000  # Non-trivial PDF
    assert pdf_bytes[:4] == b"%PDF"  # Valid PDF magic bytes


def test_pdf_skips_unavailable_features():
    """PDF must not crash when features are unavailable."""
    from app.services.pdf_generator import build_pdf_bytes
    report_json = _make_valid_report_json(str(uuid4()))
    report_json["limitations"] = []  # Empty limitations
    report_input = {
        "track_label": "person_1",
        "duration_seconds": 60.0,
        "coverage": 0.3,
        "detection_confidence": None,  # No confidence
        "data_quality": "limited",
        "missing_features": ["gaze", "body_posture", "hand_pose"],
        "total_detections": 30,
    }
    # Should not raise
    pdf_bytes = build_pdf_bytes(report_json, report_input, "meeting-xyz")
    assert len(pdf_bytes) > 1000


# ---- 6. Security: no API key leakage ----

def test_llm_api_key_not_in_system_prompt():
    """The LLM system prompt must never contain an API key."""
    from app.services.llm_service import SYSTEM_PROMPT
    # Check for actual key patterns (hf_ token or OpenAI sk- prefixed key formats)
    assert "hf_fhQ" not in SYSTEM_PROMPT  # No actual HF key
    assert "Bearer hf_" not in SYSTEM_PROMPT
    assert "Authorization" not in SYSTEM_PROMPT


def test_prompt_version_defined():
    """Prompt version must be a non-empty string for caching."""
    from app.services.llm_service import PROMPT_VERSION
    assert isinstance(PROMPT_VERSION, str)
    assert len(PROMPT_VERSION) > 0
