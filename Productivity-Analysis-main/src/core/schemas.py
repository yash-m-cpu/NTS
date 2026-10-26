"""Canonical Pydantic schemas for the WBPIS system.

Strictly adheres to Phase 04-Phase 12 specifications, defining typed
contracts for detections, tracks, zones, activities, metrics, and scorecards.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union
from pydantic import BaseModel, Field, field_validator, model_validator


# ============================================================================
# 1. ENUMERATIONS & CANONICAL STATUSES
# ============================================================================

class MetricStatus(str, Enum):
    EXISTING_VERIFIED = "EXISTING_VERIFIED"
    EXISTING_UNVERIFIED = "EXISTING_UNVERIFIED"
    PROPOSED = "PROPOSED"
    REQUIRES_EXTERNAL_DATA = "REQUIRES_EXTERNAL_DATA"
    UNAVAILABLE = "UNAVAILABLE"


class ZoneType(str, Enum):
    WORKSTATION = "WORKSTATION"
    COLLABORATION = "COLLABORATION"
    MEETING = "MEETING"
    CORRIDOR = "CORRIDOR"
    SHARED_RESOURCE = "SHARED_RESOURCE"
    COMMON_AREA = "COMMON_AREA"


class OccupancyState(str, Enum):
    VACANT = "VACANT"
    OCCUPIED = "OCCUPIED"
    TRANSITORY_ABSENCE = "TRANSITORY_ABSENCE"
    PROLONGED_ABSENCE = "PROLONGED_ABSENCE"


class ActivityCode(str, Enum):
    ACT_01 = "ACT-01: Seated at Workstation"
    ACT_02 = "ACT-02: Standing at Workstation"
    ACT_03 = "ACT-03: Walking / In Transit"
    ACT_04 = "ACT-04: Workstation Interaction"
    ACT_05 = "ACT-05: Active Collaboration"
    ACT_06 = "ACT-06: Away from Monitored Desk"
    ACT_07 = "ACT-07: Unknown / Unclassified"


class TrackLifecycle(str, Enum):
    TENTATIVE = "TENTATIVE"
    CONFIRMED = "CONFIRMED"
    LOST = "LOST"
    EXPIRED = "EXPIRED"


# ============================================================================
# 2. GEOMETRY & ZONE SCHEMAS
# ============================================================================

class Point2D(BaseModel):
    x: float
    y: float


class BoundingBox(BaseModel):
    """Normalized bounding box coordinates in [0.0, 1.0]."""
    x1: float = Field(ge=0.0, le=1.0)
    y1: float = Field(ge=0.0, le=1.0)
    x2: float = Field(ge=0.0, le=1.0)
    y2: float = Field(ge=0.0, le=1.0)

    @property
    def footprint(self) -> Point2D:
        """Bottom-center point representing ground plane contact."""
        return Point2D(x=(self.x1 + self.x2) / 2.0, y=self.y2)

    @property
    def center(self) -> Point2D:
        return Point2D(x=(self.x1 + self.x2) / 2.0, y=(self.y1 + self.y2) / 2.0)

    @property
    def width(self) -> float:
        return abs(self.x2 - self.x1)

    @property
    def height(self) -> float:
        return abs(self.y2 - self.y1)


class ZoneCreate(BaseModel):
    """Schema for registering a new spatial zone."""
    zone_id: str
    camera_id: str
    name: str
    zone_type: ZoneType
    polygon_normalized: List[List[float]] = Field(
        ...,
        description="List of [x, y] coordinates in [0.0, 1.0]"
    )
    capacity: int = 1
    area_sq_meters: Optional[float] = None

    @model_validator(mode="before")
    @classmethod
    def normalize_polygon_input(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "polygon_coords" in data and "polygon_normalized" not in data:
                data["polygon_normalized"] = data["polygon_coords"]
        return data

    @property
    def polygon_coords(self) -> List[List[float]]:
        return self.polygon_normalized

    @field_validator("polygon_normalized")
    @classmethod
    def validate_polygon_vertices(cls, v: List[List[float]]) -> List[List[float]]:
        if len(v) < 3:
            raise ValueError("Polygon must contain at least 3 vertices")
        for pt in v:
            if len(pt) != 2:
                raise ValueError("Each vertex must be a 2-element [x, y] array")
            if not (0.0 <= pt[0] <= 1.0 and 0.0 <= pt[1] <= 1.0):
                raise ValueError(f"Vertex coordinates must be normalized in [0.0, 1.0], got {pt}")
        return v



class ZoneRead(ZoneCreate):
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ============================================================================
# 3. DETECTION & TRACKING SCHEMAS
# ============================================================================

class Detection(BaseModel):
    box: BoundingBox
    confidence: float = Field(ge=0.0, le=1.0)
    class_id: int = 0
    class_name: str = "person"


class TrackObservation(BaseModel):
    track_id: int
    ephemeral_hash: str
    camera_id: str
    box: BoundingBox
    footprint: Point2D
    detection_confidence: float
    tracking_state: TrackLifecycle
    current_zone_id: Optional[str] = None
    activity_code: ActivityCode = ActivityCode.ACT_07
    first_seen: datetime
    last_seen: datetime
    total_frames: int = 1
    consecutive_invisible_frames: int = 0
    velocity: float = 0.0
    dwell_duration_seconds: float = 0.0
    transitions_count: int = 0
    interruption_events: int = 0
    waiting_seconds: float = 0.0
    activity_breakdown: Dict[str, float] = Field(default_factory=dict)


# ============================================================================
# 4. METRIC & SCORECARD SCHEMAS
# ============================================================================

class MetricValue(BaseModel):
    metric_id: str
    display_name: str
    status: MetricStatus
    value: Optional[float] = None
    unit: str
    observation_coverage_pct: float = Field(default=100.0, ge=0.0, le=100.0)
    aggregation_window_seconds: int = 300
    is_valid: bool = True
    note: Optional[str] = None


class ScorecardA_WorkflowEfficiency(BaseModel):
    scorecard_name: str = "Workflow Efficiency"
    status: MetricStatus = MetricStatus.PROPOSED
    workflow_efficiency_score: Optional[float] = None  # Scale 0 - 100
    bottleneck_risk_index: Optional[float] = None      # Scale 0 - 100
    interruption_frequency: Optional[MetricValue] = None
    waiting_time_ratio: Optional[MetricValue] = None
    congestion_rate: Optional[MetricValue] = None
    zone_transition_rate: Optional[MetricValue] = None
    repeated_trip_rate: Optional[MetricValue] = None
    shared_resource_utilization: Optional[MetricValue] = None


class ScorecardB_ActivityAnalytics(BaseModel):
    scorecard_name: str = "Activity & Time Distribution"
    status: MetricStatus = MetricStatus.PROPOSED
    activity_shares: Dict[str, float] = Field(default_factory=dict)
    interaction_ratio_pct: Optional[float] = None
    movement_ratio_pct: Optional[float] = None
    activity_transition_rate: Optional[float] = None
    classification_coverage_pct: float = 100.0
    unknown_state_ratio_pct: float = 0.0


class ScorecardC_OccupancyPresence(BaseModel):
    scorecard_name: str = "Occupancy & Presence"
    status: MetricStatus = MetricStatus.PROPOSED
    workstation_occupancy_rate_pct: Optional[float] = None
    workspace_utilization_pct: Optional[float] = None
    observed_presence_seconds: float = 0.0
    away_time_ratio_pct: Optional[float] = None
    occupancy_variation_std: Optional[float] = None
    schedule_adherence_pct: Optional[float] = None
    observation_coverage_pct: float = 100.0


class ScorecardD_OutputEffectiveness(BaseModel):
    scorecard_name: str = "Output Effectiveness"
    status: MetricStatus = MetricStatus.REQUIRES_EXTERNAL_DATA
    output_effectiveness_score: Optional[float] = None
    throughput_attainment_pct: Optional[float] = None
    quality_rate_pct: Optional[float] = None
    timeliness_rate_pct: Optional[float] = None
    rework_rate_pct: Optional[float] = None
    message: str = "Outcome data unavailable. CCTV data is never used to infer work output."


class ScorecardSuite(BaseModel):
    camera_id: str
    department_code: str = "ALL"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    observation_coverage_pct: float = 100.0
    scorecard_a: ScorecardA_WorkflowEfficiency
    scorecard_b: ScorecardB_ActivityAnalytics
    scorecard_c: ScorecardC_OccupancyPresence
    scorecard_d: ScorecardD_OutputEffectiveness


# ============================================================================
# 5. WEBSOCKET & API TELEMETRY SCHEMAS
# ============================================================================

class TrackTelemetry(BaseModel):
    track_id: str
    box: List[int]
    footprint: List[int]
    zone_id: Optional[str] = None
    activity: str
    confidence: float
    rolling_wor_pct: Optional[float] = None
    rolling_interaction_pct: Optional[float] = None
    velocity: float = 0.0
    dwell_duration_seconds: float = 0.0
    transitions_count: int = 0
    interruption_events: int = 0
    waiting_seconds: float = 0.0
    activity_breakdown: Dict[str, float] = Field(default_factory=dict)


class LiveTelemetryMessage(BaseModel):
    timestamp: str
    camera_id: str
    fps: float
    active_tracks: List[TrackTelemetry]
    zones_occupancy: Dict[str, str]
    observation_coverage_pct: float = 100.0


class OperationalOutcomeBatch(BaseModel):
    report_date: str
    department_code: str
    actual_completed_units: int
    target_planned_units: int
    quality_accepted_units: int
    quality_assessed_units: int
    on_time_units: int
    total_deadline_units: int
    rework_units: int = 0
    source_system: str
    auth_signature: Optional[str] = None
