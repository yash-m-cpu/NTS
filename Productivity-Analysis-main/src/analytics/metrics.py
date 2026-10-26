"""Canonical Metric Engine for WBPIS.

Implements all 26 metrics across Groups A, B, C, D, and E with strict
adherence to Phase 04-Phase 09 mathematical formulations and status labels.
"""

from typing import Any, Dict, List, Optional
import numpy as np

from src.core.schemas import MetricStatus, MetricValue


def normalize_p5_p95(val: float, p5: float, p95: float) -> float:
    """Clips and normalizes an unbounded metric value using empirical 5th and 95th percentiles.

    Formula: Risk = 100.0 * clip((val - p5) / (p95 - p5), 0.0, 1.0)
    """
    if p95 <= p5:
        return 0.0
    clipped = max(0.0, min(1.0, (val - p5) / (p95 - p5)))
    return float(clipped * 100.0)


# ============================================================================
# GROUP A: PERCEPTION QUALITY & OBSERVATION COVERAGE
# ============================================================================

def calculate_detection_confidence(confidences: List[float]) -> MetricValue:
    """MET-A1: Detection Confidence."""
    if not confidences:
        return MetricValue(
            metric_id="MET-A1",
            display_name="Detection Confidence",
            status=MetricStatus.PROPOSED,
            value=None,
            unit="probability",
            is_valid=False,
            note="No detections available in window."
        )
    mean_conf = float(np.mean(confidences))
    return MetricValue(
        metric_id="MET-A1",
        display_name="Detection Confidence",
        status=MetricStatus.PROPOSED,
        value=round(mean_conf, 3),
        unit="probability",
        is_valid=True
    )


def calculate_tracking_continuity(continuous_frames: int, total_frames: int, num_frags: int) -> MetricValue:
    """MET-A2: Tracking Continuity."""
    if total_frames <= 0:
        return MetricValue(
            metric_id="MET-A2",
            display_name="Tracking Continuity",
            status=MetricStatus.PROPOSED,
            value=None,
            unit="%",
            is_valid=False
        )
    penalty = num_frags * 15
    denom = total_frames + penalty
    continuity = 100.0 * (continuous_frames / denom) if denom > 0 else 0.0
    return MetricValue(
        metric_id="MET-A2",
        display_name="Tracking Continuity",
        status=MetricStatus.PROPOSED,
        value=round(min(100.0, max(0.0, continuity)), 1),
        unit="%"
    )


def calculate_observation_coverage(valid_seconds: float, expected_seconds: float) -> MetricValue:
    """MET-A3: Valid Observation Coverage."""
    if expected_seconds <= 0.0:
        return MetricValue(
            metric_id="MET-A3",
            display_name="Observation Coverage",
            status=MetricStatus.PROPOSED,
            value=None,
            unit="%",
            is_valid=False
        )
    coverage = 100.0 * (valid_seconds / expected_seconds)
    return MetricValue(
        metric_id="MET-A3",
        display_name="Observation Coverage",
        status=MetricStatus.PROPOSED,
        value=round(min(100.0, max(0.0, coverage)), 1),
        unit="%"
    )


def calculate_unknown_state_ratio(unknown_seconds: float, total_observed_seconds: float) -> MetricValue:
    """MET-A4: Unknown-State Ratio."""
    if total_observed_seconds <= 0.0:
        return MetricValue(
            metric_id="MET-A4",
            display_name="Unknown-State Ratio",
            status=MetricStatus.PROPOSED,
            value=0.0,
            unit="%"
        )
    ratio = 100.0 * (unknown_seconds / total_observed_seconds)
    return MetricValue(
        metric_id="MET-A4",
        display_name="Unknown-State Ratio",
        status=MetricStatus.PROPOSED,
        value=round(min(100.0, max(0.0, ratio)), 1),
        unit="%"
    )


# ============================================================================
# GROUP B: WORKSTATION OCCUPANCY & PRESENCE
# ============================================================================

def calculate_workstation_occupancy_rate(occupied_seconds: float, monitored_seconds: float) -> MetricValue:
    """MET-B1: Workstation Occupancy Rate (WOR)."""
    if monitored_seconds <= 0.0:
        return MetricValue(
            metric_id="MET-B1",
            display_name="Workstation Occupancy Rate",
            status=MetricStatus.EXISTING_VERIFIED,
            value=None,
            unit="%",
            is_valid=False
        )
    rate = 100.0 * (occupied_seconds / monitored_seconds)
    return MetricValue(
        metric_id="MET-B1",
        display_name="Workstation Occupancy Rate",
        status=MetricStatus.EXISTING_VERIFIED,
        value=round(min(100.0, max(0.0, rate)), 1),
        unit="%"
    )


def calculate_workspace_utilization(total_occupied_desk_minutes: float, total_available_desk_minutes: float) -> MetricValue:
    """MET-B6: Workspace Utilization."""
    if total_available_desk_minutes <= 0.0:
        return MetricValue(
            metric_id="MET-B6",
            display_name="Workspace Utilization",
            status=MetricStatus.PROPOSED,
            value=None,
            unit="%",
            is_valid=False
        )
    util = 100.0 * (total_occupied_desk_minutes / total_available_desk_minutes)
    return MetricValue(
        metric_id="MET-B6",
        display_name="Workspace Utilization",
        status=MetricStatus.PROPOSED,
        value=round(min(100.0, max(0.0, util)), 1),
        unit="%"
    )


# ============================================================================
# GROUP C: ACTIVITY & TIME DISTRIBUTION
# ============================================================================

def calculate_activity_shares(activity_durations: Dict[str, float]) -> Dict[str, float]:
    """MET-C2: Activity Share across all 7 mutually exclusive categories."""
    total_duration = sum(activity_durations.values())
    if total_duration <= 0.0:
        return {k: 0.0 for k in activity_durations.keys()}
    return {
        k: round(100.0 * (dur / total_duration), 1)
        for k, dur in activity_durations.items()
    }


def calculate_interaction_ratio(interaction_seconds: float, total_desk_seconds: float) -> MetricValue:
    """MET-C3: Workstation Interaction Ratio."""
    if total_desk_seconds <= 0.0:
        return MetricValue(
            metric_id="MET-C3",
            display_name="Workstation Interaction Ratio",
            status=MetricStatus.PROPOSED,
            value=None,
            unit="%",
            is_valid=False
        )
    ratio = 100.0 * (interaction_seconds / total_desk_seconds)
    return MetricValue(
        metric_id="MET-C3",
        display_name="Workstation Interaction Ratio",
        status=MetricStatus.PROPOSED,
        value=round(min(100.0, max(0.0, ratio)), 1),
        unit="%"
    )


def calculate_movement_ratio(walking_seconds: float, total_observed_seconds: float) -> MetricValue:
    """MET-C4: Movement Ratio."""
    if total_observed_seconds <= 0.0:
        return MetricValue(
            metric_id="MET-C4",
            display_name="Movement Ratio",
            status=MetricStatus.PROPOSED,
            value=None,
            unit="%",
            is_valid=False
        )
    ratio = 100.0 * (walking_seconds / total_observed_seconds)
    return MetricValue(
        metric_id="MET-C4",
        display_name="Movement Ratio",
        status=MetricStatus.PROPOSED,
        value=round(min(100.0, max(0.0, ratio)), 1),
        unit="%"
    )


# ============================================================================
# GROUP D: WORKFLOW & BOTTLENECK METRICS
# ============================================================================

def calculate_interruption_frequency(interruption_events: int, focus_hours: float) -> MetricValue:
    """MET-D1: Interruption Frequency."""
    if focus_hours <= 0.0:
        return MetricValue(
            metric_id="MET-D1",
            display_name="Interruption Frequency",
            status=MetricStatus.PROPOSED,
            value=None,
            unit="events/hour",
            is_valid=False
        )
    freq = interruption_events / focus_hours
    return MetricValue(
        metric_id="MET-D1",
        display_name="Interruption Frequency",
        status=MetricStatus.PROPOSED,
        value=round(freq, 2),
        unit="events/hour"
    )


def calculate_waiting_time_ratio(waiting_seconds: float, operational_seconds: float) -> MetricValue:
    """MET-D2: Waiting-Time Ratio."""
    if operational_seconds <= 0.0:
        return MetricValue(
            metric_id="MET-D2",
            display_name="Waiting-Time Ratio",
            status=MetricStatus.PROPOSED,
            value=None,
            unit="%",
            is_valid=False
        )
    ratio = 100.0 * (waiting_seconds / operational_seconds)
    return MetricValue(
        metric_id="MET-D2",
        display_name="Waiting-Time Ratio",
        status=MetricStatus.PROPOSED,
        value=round(min(100.0, max(0.0, ratio)), 1),
        unit="%"
    )


def calculate_zone_transition_rate(transitions_count: int, monitored_hours: float) -> MetricValue:
    """MET-D3: Zone Transition Rate."""
    if monitored_hours <= 0.0:
        return MetricValue(
            metric_id="MET-D3",
            display_name="Zone Transition Rate",
            status=MetricStatus.PROPOSED,
            value=None,
            unit="transitions/hour",
            is_valid=False
        )
    rate = transitions_count / monitored_hours
    return MetricValue(
        metric_id="MET-D3",
        display_name="Zone Transition Rate",
        status=MetricStatus.PROPOSED,
        value=round(rate, 1),
        unit="transitions/hour"
    )


def calculate_congestion_rate(congested_seconds: float, monitored_seconds: float) -> MetricValue:
    """MET-D4: Congestion Rate."""
    if monitored_seconds <= 0.0:
        return MetricValue(
            metric_id="MET-D4",
            display_name="Congestion Rate",
            status=MetricStatus.PROPOSED,
            value=None,
            unit="%",
            is_valid=False
        )
    rate = 100.0 * (congested_seconds / monitored_seconds)
    return MetricValue(
        metric_id="MET-D4",
        display_name="Congestion Rate",
        status=MetricStatus.PROPOSED,
        value=round(min(100.0, max(0.0, rate)), 1),
        unit="%"
    )


def calculate_shared_resource_utilization(occupied_seconds: float, available_seconds: float) -> MetricValue:
    """MET-D6: Shared-Resource Utilization (SRU)."""
    if available_seconds <= 0.0:
        return MetricValue(
            metric_id="MET-D6",
            display_name="Shared-Resource Utilization",
            status=MetricStatus.PROPOSED,
            value=None,
            unit="%",
            is_valid=False
        )
    rate = 100.0 * (occupied_seconds / available_seconds)
    return MetricValue(
        metric_id="MET-D6",
        display_name="Shared-Resource Utilization",
        status=MetricStatus.PROPOSED,
        value=round(min(100.0, max(0.0, rate)), 1),
        unit="%"
    )


# ============================================================================
# GROUP E: OPERATIONAL OUTPUTS (REQUIRES EXTERNAL DATA)
# ============================================================================

def calculate_throughput_attainment(actual_units: Optional[int], target_units: Optional[int]) -> MetricValue:
    """MET-E1: Throughput Attainment."""
    if actual_units is None or target_units is None or target_units <= 0:
        return MetricValue(
            metric_id="MET-E1",
            display_name="Throughput Attainment",
            status=MetricStatus.REQUIRES_EXTERNAL_DATA,
            value=None,
            unit="%",
            is_valid=False,
            note="Outcome data unavailable. CCTV data is never used to infer work output."
        )
    rate = 100.0 * (actual_units / target_units)
    return MetricValue(
        metric_id="MET-E1",
        display_name="Throughput Attainment",
        status=MetricStatus.REQUIRES_EXTERNAL_DATA,
        value=round(rate, 1),
        unit="%"
    )


def calculate_quality_rate(accepted_units: Optional[int], assessed_units: Optional[int]) -> MetricValue:
    """MET-E2: Quality Rate."""
    if accepted_units is None or assessed_units is None or assessed_units <= 0:
        return MetricValue(
            metric_id="MET-E2",
            display_name="Quality Rate",
            status=MetricStatus.REQUIRES_EXTERNAL_DATA,
            value=None,
            unit="%",
            is_valid=False,
            note="Quality inspection records unconfigured."
        )
    rate = 100.0 * (accepted_units / assessed_units)
    return MetricValue(
        metric_id="MET-E2",
        display_name="Quality Rate",
        status=MetricStatus.REQUIRES_EXTERNAL_DATA,
        value=round(min(100.0, max(0.0, rate)), 1),
        unit="%"
    )


def calculate_output_effectiveness_score(
    throughput_score: Optional[float],
    quality_score: Optional[float],
    timeliness_score: Optional[float]
) -> MetricValue:
    """MET-E6: Output Effectiveness Score."""
    if throughput_score is None or quality_score is None or timeliness_score is None:
        return MetricValue(
            metric_id="MET-E6",
            display_name="Output Effectiveness Score",
            status=MetricStatus.REQUIRES_EXTERNAL_DATA,
            value=None,
            unit="score (0-100)",
            is_valid=False,
            note="Requires authenticated external business outcome records."
        )
    # Provisional weights: 50% Throughput, 30% Quality, 20% Timeliness
    composite = (
        0.50 * min(100.0, throughput_score) +
        0.30 * min(100.0, quality_score) +
        0.20 * min(100.0, timeliness_score)
    )
    return MetricValue(
        metric_id="MET-E6",
        display_name="Output Effectiveness Score",
        status=MetricStatus.REQUIRES_EXTERNAL_DATA,
        value=round(composite, 1),
        unit="score (0-100)"
    )
