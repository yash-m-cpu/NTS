"""
visual_aggregator.py
Converts stored FeatureExtraction + BehavioralMetric + ParticipantTrack
into a compact, token-efficient VisualReportInput dict.
No CV re-inference is performed here.
"""
import hashlib
import json
import math
import statistics
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.features import FeatureExtraction
from app.models.metrics import BehavioralMetric
from app.models.participants import ParticipantTrack


# Minimum observations before reporting a feature (avoid fabrication)
MIN_OBSERVATIONS = 5

PROMPT_VERSION = "1.0"


def _safe_stats(values: list[float]) -> dict | None:
    """Return mean/std/min/max or None if insufficient data."""
    if len(values) < MIN_OBSERVATIONS:
        return None
    return {
        "mean": round(statistics.mean(values), 4),
        "std": round(statistics.stdev(values) if len(values) > 1 else 0.0, 4),
        "min": round(min(values), 4),
        "max": round(max(values), 4),
    }


def _availability_wrapper(stats: dict | None, reason: str = "insufficient observations") -> dict:
    if stats is None:
        return {"available": False, "reason": reason}
    return {"available": True, **stats}


async def build_visual_report_input(
    db: AsyncSession,
    track_id: UUID,
    meeting_id: UUID,
) -> dict[str, Any]:
    """
    Main entry point: builds the compact VisualReportInput from DB.
    Returns a dict suitable for JSON serialization → LLM prompt.
    """
    # Load participant track metadata
    track = await db.scalar(select(ParticipantTrack).where(ParticipantTrack.id == track_id))
    if not track:
        raise ValueError(f"ParticipantTrack {track_id} not found")

    duration_ms = track.last_seen_at_ms - track.first_seen_at_ms
    duration_sec = duration_ms / 1000.0

    # Load all feature extractions for this track (exclude speaker_turn which is audio-derived)
    EXCLUDED_FEATURE_TYPES = {"speaker_turn"}
    result = await db.execute(
        select(FeatureExtraction)
        .where(FeatureExtraction.participant_track_id == track_id)
        .order_by(FeatureExtraction.timestamp_ms)
    )
    raw_features = [f for f in result.scalars().all() if f.feature_type not in EXCLUDED_FEATURE_TYPES]

    # Load behavioral metrics (visual-only: gaze_aversion_ratio etc.)
    EXCLUDED_METRIC_KEYS = {"speech_ratio", "speaking_time_seconds", "turn_count", "avg_turn_duration_seconds"}
    metric_result = await db.execute(
        select(BehavioralMetric).where(BehavioralMetric.participant_track_id == track_id)
    )
    metrics = {m.metric_key: float(m.value) for m in metric_result.scalars().all()
               if m.metric_key not in EXCLUDED_METRIC_KEYS}

    total_frames = track.detection_frame_count or len(raw_features)
    det_conf = float(track.avg_detection_confidence) if track.avg_detection_confidence else None

    # ---- Head rotation ----
    yaw_vals, pitch_vals, roll_vals = [], [], []
    for f in raw_features:
        rot = f.values.get("rotation") if f.values else None
        if rot:
            if rot.get("yaw") is not None:
                yaw_vals.append(float(rot["yaw"]))
            if rot.get("pitch") is not None:
                pitch_vals.append(float(rot["pitch"]))
            if rot.get("roll") is not None:
                roll_vals.append(float(rot["roll"]))

    def _movement_variability(std: float | None) -> str:
        if std is None:
            return "unknown"
        if std < 0.05:
            return "very_low"
        if std < 0.15:
            return "low"
        if std < 0.3:
            return "moderate"
        return "high"

    yaw_stats = _safe_stats(yaw_vals)
    pitch_stats = _safe_stats(pitch_vals)
    roll_stats = _safe_stats(roll_vals)

    head_section: dict[str, Any]
    if any(s is not None for s in [yaw_stats, pitch_stats, roll_stats]):
        head_section = {
            "available": True,
            "yaw": _availability_wrapper(yaw_stats),
            "pitch": _availability_wrapper(pitch_stats),
            "roll": _availability_wrapper(roll_stats),
            "movement_variability": _movement_variability(yaw_stats.get("std") if yaw_stats else None),
            "movement_stability": "stable" if yaw_stats and yaw_stats.get("std", 1) < 0.2 else "variable",
        }
    else:
        head_section = {"available": False, "reason": "no head rotation data found"}

    # ---- Gaze ----
    gaze_bearings = []
    for f in raw_features:
        if f.feature_type == "gaze" and f.values:
            b = f.values.get("gaze", {}).get("bearing")
            if b is not None:
                gaze_bearings.append(float(b))

    gaze_aversion = metrics.get("gaze_aversion_ratio")
    gaze_stats = _safe_stats(gaze_bearings)

    if gaze_stats or gaze_aversion is not None:
        def _gaze_stability(std: float | None, aversion: float | None) -> str:
            if std is None:
                return "unknown"
            if std < 20:
                return "stable"
            if std < 60:
                return "moderate"
            return "variable"

        gaze_section: dict[str, Any] = {
            "available": True,
            "stability": _gaze_stability(gaze_stats.get("std") if gaze_stats else None, gaze_aversion),
            "variability": _availability_wrapper(gaze_stats, "insufficient gaze observations"),
            "gaze_aversion_ratio": round(gaze_aversion, 4) if gaze_aversion is not None else None,
            "observations": len(gaze_bearings),
        }
    else:
        gaze_section = {"available": False, "reason": "no gaze data found"}

    # ---- Posture (body keypoints) ----
    keypoint_counts = []
    for f in raw_features:
        if f.feature_type == "body_pose" and f.values:
            kps = f.values.get("keypoints")
            if kps is not None:
                keypoint_counts.append(len(kps) if isinstance(kps, list) else 0)

    if len(keypoint_counts) >= MIN_OBSERVATIONS:
        avg_kp_count = statistics.mean(keypoint_counts)
        kp_std = statistics.stdev(keypoint_counts) if len(keypoint_counts) > 1 else 0.0
        posture_section: dict[str, Any] = {
            "available": True,
            "avg_keypoints_detected": round(avg_kp_count, 2),
            "keypoint_stability": round(kp_std, 3),
            "posture_consistency": "consistent" if kp_std < 3 else "variable",
            "observations": len(keypoint_counts),
        }
    else:
        posture_section = {"available": False, "reason": "insufficient body pose observations"}

    # ---- Hands ----
    hand_counts = []
    for f in raw_features:
        if f.feature_type == "hand_pose" and f.values:
            hands = f.values.get("hands")
            if hands is not None:
                hand_counts.append(len(hands) if isinstance(hands, list) else 0)

    if len(hand_counts) >= MIN_OBSERVATIONS:
        avg_hands = statistics.mean(hand_counts)
        hand_visibility_ratio = sum(1 for h in hand_counts if h > 0) / len(hand_counts)
        hands_section: dict[str, Any] = {
            "available": True,
            "avg_hands_visible": round(avg_hands, 3),
            "hand_visibility_ratio": round(hand_visibility_ratio, 4),
            "gesture_activity": "active" if avg_hands > 0.5 else "minimal",
            "observations": len(hand_counts),
        }
    else:
        hands_section = {"available": False, "reason": "insufficient hand pose observations"}

    # ---- Facial Affect ----
    emotion_accumulator: dict[str, list[float]] = {}
    for f in raw_features:
        if f.feature_type == "emotion" and f.values:
            emotions = f.values.get("emotions", {})
            for emo, prob in emotions.items():
                emotion_accumulator.setdefault(emo, []).append(float(prob))

    if emotion_accumulator and sum(len(v) for v in emotion_accumulator.values()) >= MIN_OBSERVATIONS:
        affect_dist = {emo: round(statistics.mean(probs), 4) for emo, probs in emotion_accumulator.items()}
        dominant = max(affect_dist, key=lambda k: affect_dist[k])
        # variability: std of the dominant emotion probability
        dom_std = round(statistics.stdev(emotion_accumulator[dominant]), 4) if len(emotion_accumulator[dominant]) > 1 else 0.0
        facial_section: dict[str, Any] = {
            "available": True,
            "affect_distribution": affect_dist,
            "dominant_affect": dominant,
            "dominant_affect_mean": affect_dist[dominant],
            "affect_variability": dom_std,
            "observations": len(emotion_accumulator.get(dominant, [])),
        }
    else:
        facial_section = {"available": False, "reason": "insufficient facial affect observations"}

    # ---- Missing features list ----
    missing = []
    if not head_section.get("available"):
        missing.append("head_rotation")
    if not gaze_section.get("available"):
        missing.append("gaze")
    if not posture_section.get("available"):
        missing.append("body_posture")
    if not hands_section.get("available"):
        missing.append("hand_pose")
    if not facial_section.get("available"):
        missing.append("facial_affect")

    filled = 5 - len(missing)
    coverage_score = filled / 5.0

    data_quality = "good" if coverage_score >= 0.8 and det_conf and det_conf >= 0.7 else \
                   "moderate" if coverage_score >= 0.5 else "limited"

    # ---- Assemble compact report input ----
    report_input = {
        "participant_track_id": str(track_id),
        "meeting_id": str(meeting_id),
        "track_label": track.track_label,
        "duration_seconds": round(duration_sec, 1),
        "total_detections": total_frames,
        "detection_confidence": round(det_conf, 4) if det_conf else None,
        "coverage": round(coverage_score, 3),
        "missing_features": missing,
        "data_quality": data_quality,
        "head": head_section,
        "gaze": gaze_section,
        "posture": posture_section,
        "hands": hands_section,
        "facial_affect": facial_section,
        "behavioral_metrics": metrics,
    }

    return report_input


def compute_input_hash(report_input: dict) -> str:
    """Deterministic SHA-256 hash of the compact report input for caching."""
    canonical = json.dumps(report_input, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(canonical.encode()).hexdigest()
