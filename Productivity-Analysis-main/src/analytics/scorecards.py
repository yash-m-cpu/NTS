"""Scorecard synthesis engine for WBPIS.

Assembles the four independent scorecards (A, B, C, D) with strict
governance enforcing the anti-conflation policy.
"""

from typing import Any, Dict, List, Optional
from src.core.schemas import (
    MetricStatus,
    ScorecardA_WorkflowEfficiency,
    ScorecardB_ActivityAnalytics,
    ScorecardC_OccupancyPresence,
    ScorecardD_OutputEffectiveness,
    ScorecardSuite
)
from src.analytics.metrics import (
    calculate_congestion_rate,
    calculate_interruption_frequency,
    calculate_output_effectiveness_score,
    calculate_quality_rate,
    calculate_throughput_attainment,
    calculate_waiting_time_ratio,
    calculate_workstation_occupancy_rate,
    calculate_zone_transition_rate,
    normalize_p5_p95
)


class ScorecardEngine:
    """Assembles and calibrates Scorecards A, B, C, and D."""

    # Reference population P5 and P95 percentiles
    P5_INTERRUPTION = 0.5
    P95_INTERRUPTION = 4.5

    P5_WAITING_PCT = 1.0
    P95_WAITING_PCT = 12.0

    P5_CONGESTION_PCT = 0.0
    P95_CONGESTION_PCT = 8.0

    P5_TRANSITION_RATE = 2.0
    P95_TRANSITION_RATE = 14.0

    @classmethod
    def build_scorecard_a(
        cls,
        interruption_events: int = 0,
        focus_hours: float = 1.0,
        waiting_seconds: float = 0.0,
        operational_seconds: float = 3600.0,
        congested_seconds: float = 0.0,
        monitored_seconds: float = 3600.0,
        transitions_count: int = 0,
        monitored_hours: float = 1.0
    ) -> ScorecardA_WorkflowEfficiency:
        """Builds Scorecard A: Workflow Efficiency Score."""
        m_intr = calculate_interruption_frequency(interruption_events, focus_hours)
        m_wait = calculate_waiting_time_ratio(waiting_seconds, operational_seconds)
        m_cong = calculate_congestion_rate(congested_seconds, monitored_seconds)
        m_trans = calculate_zone_transition_rate(transitions_count, monitored_hours)

        # Apply P5/P95 percentile normalization
        risk_intr = normalize_p5_p95(m_intr.value or 0.0, cls.P5_INTERRUPTION, cls.P95_INTERRUPTION)
        risk_wait = normalize_p5_p95(m_wait.value or 0.0, cls.P5_WAITING_PCT, cls.P95_WAITING_PCT)
        risk_cong = normalize_p5_p95(m_cong.value or 0.0, cls.P5_CONGESTION_PCT, cls.P95_CONGESTION_PCT)
        risk_trans = normalize_p5_p95(m_trans.value or 0.0, cls.P5_TRANSITION_RATE, cls.P95_TRANSITION_RATE)

        # Provisional weights: 30% Intr, 25% Wait, 25% Cong, 20% Trans
        bottleneck_risk = (
            0.30 * risk_intr +
            0.25 * risk_wait +
            0.25 * risk_cong +
            0.20 * risk_trans
        )
        workflow_score = max(0.0, min(100.0, 100.0 - bottleneck_risk))

        return ScorecardA_WorkflowEfficiency(
            status=MetricStatus.PROPOSED,
            workflow_efficiency_score=round(workflow_score, 1),
            bottleneck_risk_index=round(bottleneck_risk, 1),
            interruption_frequency=m_intr,
            waiting_time_ratio=m_wait,
            congestion_rate=m_cong,
            zone_transition_rate=m_trans
        )

    @classmethod
    def build_scorecard_b(
        cls,
        activity_shares: Dict[str, float],
        interaction_ratio_pct: Optional[float] = None,
        movement_ratio_pct: Optional[float] = None,
        transition_rate: Optional[float] = None,
        unknown_ratio_pct: float = 0.0
    ) -> ScorecardB_ActivityAnalytics:
        """Builds Scorecard B: Activity Analytics."""
        coverage = max(0.0, min(100.0, 100.0 - unknown_ratio_pct))
        return ScorecardB_ActivityAnalytics(
            status=MetricStatus.PROPOSED,
            activity_shares=activity_shares,
            interaction_ratio_pct=round(interaction_ratio_pct, 1) if interaction_ratio_pct is not None else None,
            movement_ratio_pct=round(movement_ratio_pct, 1) if movement_ratio_pct is not None else None,
            activity_transition_rate=round(transition_rate, 1) if transition_rate is not None else None,
            classification_coverage_pct=round(coverage, 1),
            unknown_state_ratio_pct=round(unknown_ratio_pct, 1)
        )

    @classmethod
    def build_scorecard_c(
        cls,
        occupied_seconds: float = 0.0,
        monitored_seconds: float = 3600.0,
        total_presence_seconds: float = 0.0,
        away_time_ratio_pct: Optional[float] = None
    ) -> ScorecardC_OccupancyPresence:
        """Builds Scorecard C: Occupancy and Presence."""
        wor = calculate_workstation_occupancy_rate(occupied_seconds, monitored_seconds)
        return ScorecardC_OccupancyPresence(
            status=MetricStatus.EXISTING_VERIFIED,
            workstation_occupancy_rate_pct=wor.value,
            workspace_utilization_pct=wor.value,
            observed_presence_seconds=round(total_presence_seconds, 1),
            away_time_ratio_pct=away_time_ratio_pct,
            observation_coverage_pct=100.0
        )

    @classmethod
    def build_scorecard_d(
        cls,
        actual_units: Optional[int] = None,
        target_units: Optional[int] = None,
        accepted_units: Optional[int] = None,
        assessed_units: Optional[int] = None,
        on_time_units: Optional[int] = None,
        total_deadline_units: Optional[int] = None
    ) -> ScorecardD_OutputEffectiveness:
        """Builds Scorecard D: Output Effectiveness (Strict external data requirement)."""
        m_thru = calculate_throughput_attainment(actual_units, target_units)
        m_qual = calculate_quality_rate(accepted_units, assessed_units)

        timeliness_pct = None
        if on_time_units is not None and total_deadline_units is not None and total_deadline_units > 0:
            timeliness_pct = 100.0 * (on_time_units / total_deadline_units)

        m_score = calculate_output_effectiveness_score(
            throughput_score=m_thru.value,
            quality_score=m_qual.value,
            timeliness_score=timeliness_pct
        )

        return ScorecardD_OutputEffectiveness(
            status=MetricStatus.REQUIRES_EXTERNAL_DATA,
            output_effectiveness_score=m_score.value,
            throughput_attainment_pct=m_thru.value,
            quality_rate_pct=m_qual.value,
            timeliness_rate_pct=round(timeliness_pct, 1) if timeliness_pct is not None else None,
            message="Outcome data unavailable. CCTV data is never used to infer work output." if m_score.value is None else "Validated external outcome data."
        )

    @classmethod
    def build_suite(
        cls,
        camera_id: str = "CAM-01",
        scorecard_a_args: Optional[Dict[str, Any]] = None,
        scorecard_b_args: Optional[Dict[str, Any]] = None,
        scorecard_c_args: Optional[Dict[str, Any]] = None,
        scorecard_d_args: Optional[Dict[str, Any]] = None
    ) -> ScorecardSuite:
        """Assembles the complete four-scorecard analytical suite."""
        sc_a = cls.build_scorecard_a(**(scorecard_a_args or {}))
        sc_b = cls.build_scorecard_b(**(scorecard_b_args or {"activity_shares": {}}))
        sc_c = cls.build_scorecard_c(**(scorecard_c_args or {}))
        sc_d = cls.build_scorecard_d(**(scorecard_d_args or {}))

        return ScorecardSuite(
            camera_id=camera_id,
            scorecard_a=sc_a,
            scorecard_b=sc_b,
            scorecard_c=sc_c,
            scorecard_d=sc_d
        )

    calculate_scorecard_a = build_scorecard_a
    calculate_scorecard_b = build_scorecard_b
    calculate_scorecard_c = build_scorecard_c
    calculate_scorecard_d = build_scorecard_d

