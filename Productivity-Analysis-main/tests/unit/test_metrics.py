"""Unit tests for WBPIS metrics engine and scorecard synthesis."""

import pytest
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
from src.analytics.scorecards import ScorecardEngine


class TestMetricFormulas:
    """Validates mathematical correctness of core metrics."""

    def test_p5_p95_normalization(self):
        # Value at p5 is 0.0, value at p95 is 100.0, midpoint is 50.0
        assert normalize_p5_p95(1.0, 1.0, 5.0) == 0.0
        assert normalize_p5_p95(5.0, 1.0, 5.0) == 100.0
        assert normalize_p5_p95(3.0, 1.0, 5.0) == 50.0
        # Beyond bounds is clamped
        assert normalize_p5_p95(0.0, 1.0, 5.0) == 0.0
        assert normalize_p5_p95(10.0, 1.0, 5.0) == 100.0

    def test_interruption_frequency(self):
        # 4 interruptions across 2 monitored focus hours = 2.0 / hr
        m = calculate_interruption_frequency(interruption_events=4, focus_hours=2.0)
        assert m.value == 2.0
        assert m.is_valid is True

        # Zero denominator edge case
        m_zero = calculate_interruption_frequency(4, 0.0)
        assert m_zero.is_valid is False
        assert m_zero.value is None

    def test_waiting_time_ratio(self):
        # 180s waiting out of 3600s = 5.0%
        m = calculate_waiting_time_ratio(waiting_seconds=180.0, operational_seconds=3600.0)
        assert m.value == 5.0
        assert m.is_valid is True

        m_zero = calculate_waiting_time_ratio(100.0, 0.0)
        assert m_zero.is_valid is False
        assert m_zero.value is None

    def test_congestion_rate(self):
        # 360s congested out of 3600s = 10.0%
        m = calculate_congestion_rate(congested_seconds=360.0, monitored_seconds=3600.0)
        assert m.value == 10.0
        assert m.is_valid is True

        m_zero = calculate_congestion_rate(50.0, 0.0)
        assert m_zero.is_valid is False

    def test_zone_transition_rate(self):
        # 12 transitions across 3 hours = 4.0 / hr
        m = calculate_zone_transition_rate(transitions_count=12, monitored_hours=3.0)
        assert m.value == 4.0
        assert m.is_valid is True

        m_zero = calculate_zone_transition_rate(10, 0.0)
        assert m_zero.is_valid is False

    def test_workstation_occupancy_rate(self):
        # 2700s occupied out of 3600s = 75.0%
        m = calculate_workstation_occupancy_rate(occupied_seconds=2700.0, monitored_seconds=3600.0)
        assert m.value == 75.0
        assert m.is_valid is True

        m_zero = calculate_workstation_occupancy_rate(1000.0, 0.0)
        assert m_zero.is_valid is False

    def test_output_effectiveness_composite(self):
        # 100% throughput, 100% quality, 100% timeliness = 100.0
        m = calculate_output_effectiveness_score(
            throughput_score=100.0,
            quality_score=100.0,
            timeliness_score=100.0
        )
        assert m.value == 100.0
        assert m.is_valid is True

        # Weighted calculation: 50% * 80 + 30% * 90 + 20% * 70 = 40 + 27 + 14 = 81.0
        m2 = calculate_output_effectiveness_score(
            throughput_score=80.0,
            quality_score=90.0,
            timeliness_score=70.0
        )
        assert m2.value == 81.0

        # None inputs when external pipeline unconfigured
        m_none = calculate_output_effectiveness_score(None, 90.0, 80.0)
        assert m_none.is_valid is False
        assert m_none.value is None


class TestScorecardEngine:
    """Validates Scorecards A, B, C, D synthesis and Anti-Surveillance guarantees."""

    def test_scorecard_a_synthesis(self):
        sc_a = ScorecardEngine.calculate_scorecard_a(
            interruption_events=2,
            focus_hours=2.0,
            waiting_seconds=120.0,
            operational_seconds=3600.0,
            congested_seconds=60.0,
            monitored_seconds=3600.0,
            transitions_count=6,
            monitored_hours=2.0
        )
        assert 0.0 <= sc_a.workflow_efficiency_score <= 100.0
        assert sc_a.interruption_frequency.value == 1.0
        assert sc_a.waiting_time_ratio.value > 0.0

    def test_scorecard_b_synthesis(self):
        activity_dist = {
            "ACT-01": 60.0,
            "ACT-02": 20.0,
            "ACT-03": 10.0,
            "ACT-04": 5.0,
            "ACT-05": 3.0,
            "ACT-06": 1.0,
            "ACT-07": 1.0
        }
        sc_b = ScorecardEngine.calculate_scorecard_b(
            activity_shares=activity_dist,
            interaction_ratio_pct=20.0,
            movement_ratio_pct=15.0,
            transition_rate=4.5,
            unknown_ratio_pct=1.0
        )
        assert sc_b.activity_shares["ACT-01"] == 60.0
        assert sc_b.classification_coverage_pct == 99.0

    def test_scorecard_c_synthesis(self):
        sc_c = ScorecardEngine.calculate_scorecard_c(
            occupied_seconds=2700.0,
            monitored_seconds=3600.0,
            total_presence_seconds=2700.0,
            away_time_ratio_pct=25.0
        )
        assert sc_c.workstation_occupancy_rate_pct == 75.0
        assert sc_c.away_time_ratio_pct == 25.0

    def test_scorecard_d_unavailable_when_external_missing(self):
        # When no external enterprise metrics are provided, Scorecard D MUST return REQUIRES_EXTERNAL_DATA
        sc_d = ScorecardEngine.calculate_scorecard_d()
        assert sc_d.output_effectiveness_score is None
        assert "unavailable" in sc_d.message.lower()

    def test_scorecard_d_active_with_verified_deliverables(self):
        sc_d = ScorecardEngine.calculate_scorecard_d(
            actual_units=105,
            target_units=100,
            accepted_units=100,
            assessed_units=105,
            on_time_units=98,
            total_deadline_units=105
        )
        assert sc_d.output_effectiveness_score is not None
        assert sc_d.output_effectiveness_score > 0.0

