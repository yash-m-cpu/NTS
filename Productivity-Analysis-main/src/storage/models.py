"""SQLAlchemy ORM models for WBPIS storage tier.

Implements dimension tables, time-series telemetry event tables,
hourly metrics rollups, and immutable security audit logs.
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Index
)
from sqlalchemy.orm import relationship

from src.storage.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CameraModel(Base):
    __tablename__ = "dim_cameras"

    camera_id = Column(String(64), primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    rtsp_vault_key = Column(String(128), nullable=True)
    location = Column(String(255), nullable=True)
    frame_width = Column(Integer, default=1920)
    frame_height = Column(Integer, default=1080)
    calibrated_fps = Column(Float, default=15.0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)

    zones = relationship("ZoneModel", back_populates="camera", cascade="all, delete-orphan")


class ZoneModel(Base):
    __tablename__ = "dim_zones"

    zone_id = Column(String(64), primary_key=True, index=True)
    camera_id = Column(String(64), ForeignKey("dim_cameras.camera_id", ondelete="CASCADE"), nullable=False)
    name = Column(String(128), nullable=False)
    zone_type = Column(String(32), nullable=False)  # WORKSTATION, CORRIDOR, SHARED_RESOURCE, etc.
    polygon_json = Column(Text, nullable=False)    # JSON string of normalized vertices
    area_sq_meters = Column(Float, nullable=True)
    capacity = Column(Integer, default=1)
    created_at = Column(DateTime, default=utc_now)

    camera = relationship("CameraModel", back_populates="zones")


class ZoneOccupancyEventModel(Base):
    __tablename__ = "fact_zone_occupancy_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=utc_now, index=True, nullable=False)
    zone_id = Column(String(64), index=True, nullable=False)
    track_hash = Column(String(64), index=True, nullable=False)
    state = Column(String(32), nullable=False)  # OCCUPIED, TRANSITORY_ABSENCE, VACANT
    duration_seconds = Column(Float, nullable=False)

    __table_args__ = (
        Index("idx_occupancy_zone_time", "zone_id", "timestamp"),
    )


class ActivityEventModel(Base):
    __tablename__ = "fact_activity_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=utc_now, index=True, nullable=False)
    track_hash = Column(String(64), index=True, nullable=False)
    zone_id = Column(String(64), index=True, nullable=True)
    activity_code = Column(String(64), nullable=False)
    confidence = Column(Float, nullable=False)
    duration_seconds = Column(Float, default=0.0)

    __table_args__ = (
        Index("idx_activity_track_time", "track_hash", "timestamp"),
    )


class HourlyMetricModel(Base):
    __tablename__ = "fact_workstation_hourly_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    hour_bucket = Column(DateTime, index=True, nullable=False)
    zone_id = Column(String(64), index=True, nullable=False)
    occupancy_rate_pct = Column(Float, nullable=False)
    interaction_ratio_pct = Column(Float, nullable=True)
    transition_count = Column(Integer, default=0)
    interruption_count = Column(Integer, default=0)
    observation_coverage_pct = Column(Float, default=100.0)
    is_valid = Column(Boolean, default=True)

    __table_args__ = (
        Index("idx_hourly_metrics_zone_time", "zone_id", "hour_bucket"),
    )


class OperationalOutcomeModel(Base):
    __tablename__ = "fact_operational_outcomes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_date = Column(String(16), index=True, nullable=False)
    department_code = Column(String(32), index=True, nullable=False)
    actual_output = Column(Integer, nullable=False)
    target_output = Column(Integer, nullable=False)
    quality_rate_pct = Column(Float, nullable=False)
    timeliness_rate_pct = Column(Float, nullable=False)
    rework_rate_pct = Column(Float, default=0.0)
    output_effectiveness_score = Column(Float, nullable=True)
    source_system = Column(String(64), default="EXTERNAL_WEBHOOK")
    created_at = Column(DateTime, default=utc_now)


class AuditLogModel(Base):
    __tablename__ = "dim_audit_logs"

    log_id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=utc_now, index=True, nullable=False)
    user_id = Column(String(64), nullable=False)
    user_role = Column(String(32), nullable=False)
    action_type = Column(String(64), nullable=False)
    resource_id = Column(String(128), nullable=False)
    client_ip = Column(String(45), nullable=True)
    status_code = Column(Integer, nullable=False)
    payload_hash = Column(String(64), nullable=False)
    details = Column(Text, nullable=True)
