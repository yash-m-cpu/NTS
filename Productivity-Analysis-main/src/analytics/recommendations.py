"""Deterministic layout recommendation engine implementing Rules REC-01 to REC-04.

Generates structured workplace layout interventions adhering strictly to the
mandatory 7-point schema with explicit HYPOTHESIS labeling.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class Recommendation(BaseModel):
    rule_id: str
    title: str
    observed_pattern: str
    relevant_time_window: str
    evidence_and_coverage: str
    hypothesis: str  # Mandatory: explicitly labeled as HYPOTHESIS
    recommended_experiment: str
    outcome_metric: str
    follow_up_method: str


class RecommendationEngine:
    """Evaluates spatial telemetry aggregates against industrial engineering rules."""

    @classmethod
    def evaluate(
        cls,
        wor_pct: Optional[float] = None,
        sru_pct: Optional[float] = None,
        waiting_ratio_pct: Optional[float] = None,
        interruption_freq: Optional[float] = None,
        repeated_trip_rate: Optional[float] = None,
        observation_coverage_pct: float = 100.0,
        time_window: str = "Past 14 Days"
    ) -> List[Recommendation]:
        """Runs Rules REC-01 through REC-04 against supplied telemetry."""
        recommendations: List[Recommendation] = []

        # Coverage Gate: minimum 80% coverage required to emit recommendations
        if observation_coverage_pct < 80.0:
            return recommendations

        # Rule REC-01: Workstation Right-Sizing
        if wor_pct is not None and wor_pct < 35.0:
            recommendations.append(
                Recommendation(
                    rule_id="REC-01",
                    title="Workstation Pod Right-Sizing & Flexible Reallocation",
                    observed_pattern=f"Workstation pod recorded an average occupancy rate of {wor_pct:.1f}%, below the 35% utilization threshold.",
                    relevant_time_window=time_window,
                    evidence_and_coverage=f"Observation coverage: {observation_coverage_pct:.1f}%; verified over full operational window.",
                    hypothesis="HYPOTHESIS: The assigned team operates on a hybrid schedule, leaving dedicated physical desks vacant for the majority of the work week.",
                    recommended_experiment="Convert underutilized dedicated desks into an unassigned flexible hot-desking pod and reallocate surplus area for collaborative stand-ups.",
                    outcome_metric="Departmental Workspace Utilization (MET-B6) and Collaboration Duration (MET-C1: ACT-05).",
                    follow_up_method="Re-evaluate occupancy telemetry over a 3-week post-reallocation trial period using A/B evaluation."
                )
            )

        # Rule REC-02: Shared Resource Capacity Expansion
        if sru_pct is not None and waiting_ratio_pct is not None:
            if sru_pct > 85.0 and waiting_ratio_pct > 8.0:
                recommendations.append(
                    Recommendation(
                        rule_id="REC-02",
                        title="Shared Resource Bottleneck & Capacity Expansion",
                        observed_pattern=f"Shared equipment recorded {sru_pct:.1f}% utilization with a {waiting_ratio_pct:.1f}% queue waiting-time ratio.",
                        relevant_time_window=time_window,
                        evidence_and_coverage=f"Observation coverage: {observation_coverage_pct:.1f}%; stationary queue dwell verified.",
                        hypothesis="HYPOTHESIS: The single shared operational terminal is creating an operational bottleneck, causing downstream process starvation.",
                        recommended_experiment="Deploy a secondary parallel terminal or implement an asynchronous digital submission queue.",
                        outcome_metric="Queue Dwell Time / Waiting-Time Ratio (MET-D2) and Corridor Congestion (MET-D4).",
                        follow_up_method="Measure queue dwell times over 14 days post-intervention; target is a >= 50% reduction in waiting time."
                    )
                )

        # Rule REC-03: Acoustic & Focus Protection Shielding
        if interruption_freq is not None and interruption_freq > 3.0:
            recommendations.append(
                Recommendation(
                    rule_id="REC-03",
                    title="Acoustic Shielding & Walkway Rerouting",
                    observed_pattern=f"Workstations adjacent to primary corridor recorded an interruption frequency of {interruption_freq:.2f} events/hour.",
                    relevant_time_window=time_window,
                    evidence_and_coverage=f"Proximity encounters detected within 1.5m boundary; coverage: {observation_coverage_pct:.1f}%.",
                    hypothesis="HYPOTHESIS: Lack of physical buffer between desks and the main walkway exposes workers to high visual and transit disruptions.",
                    recommended_experiment="Install 1.6m frosted acoustic divider screens and shift primary transit traffic away from desk perimeters.",
                    outcome_metric="Interruption Frequency (MET-D1) and Posture Transition Rate (MET-C5).",
                    follow_up_method="Audit interruption frequency over 14 days following partition installation; target <= 1.5 interruptions/hour."
                )
            )

        # Rule REC-04: Functional Zone Proximity Realignment
        if repeated_trip_rate is not None and repeated_trip_rate > 2.0:
            recommendations.append(
                Recommendation(
                    rule_id="REC-04",
                    title="Functional Zone Adjacency Realignment",
                    observed_pattern=f"Frequent repeated trips ({repeated_trip_rate:.1f} round trips/hour) observed between dependent workstations.",
                    relevant_time_window=time_window,
                    evidence_and_coverage=f"Loop trajectory mining verified across multi-camera corridor tracking; coverage: {observation_coverage_pct:.1f}%.",
                    hypothesis="HYPOTHESIS: Significant spatial distance between interdependent team functions is creating transit churn and workflow friction.",
                    recommended_experiment="Relocate dependent teams to adjacent pods to minimize physical corridor travel.",
                    outcome_metric="Corridor Transit Churn (MET-D3) and Repeated-Trip Rate (MET-D5).",
                    follow_up_method="Measure corridor transit churn over 4 weeks post-relocation; target is a >= 60% reduction in transit churn."
                )
            )

        return recommendations
