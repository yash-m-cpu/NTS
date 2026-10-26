"""Data access repository for WBPIS storage operations."""

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from src.core.schemas import OperationalOutcomeBatch
from src.storage.models import (
    ActivityEventModel,
    AuditLogModel,
    CameraModel,
    HourlyMetricModel,
    OperationalOutcomeModel,
    ZoneModel,
    ZoneOccupancyEventModel
)


class TelemetryRepository:
    """Provides structured data access routines for telemetry, metrics, and logs."""

    @staticmethod
    def ensure_camera(db: Session, camera_id: str, name: str = "Primary Office Camera") -> CameraModel:
        """Ensures a camera record exists in dim_cameras."""
        cam = db.query(CameraModel).filter(CameraModel.camera_id == camera_id).first()
        if not cam:
            cam = CameraModel(
                camera_id=camera_id,
                name=name,
                location="Main Open Office Pod",
                frame_width=1920,
                frame_height=1080,
                calibrated_fps=15.0,
                is_active=True
            )
            db.add(cam)
            db.commit()
            db.refresh(cam)
        return cam

    @staticmethod
    def record_occupancy_event(
        db: Session,
        zone_id: str,
        track_hash: str,
        state: str,
        duration_seconds: float
    ) -> ZoneOccupancyEventModel:
        """Appends an occupancy transition event."""
        event = ZoneOccupancyEventModel(
            zone_id=zone_id,
            track_hash=track_hash,
            state=state,
            duration_seconds=duration_seconds,
            timestamp=datetime.now(timezone.utc)
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        return event

    @staticmethod
    def record_activity_event(
        db: Session,
        track_hash: str,
        zone_id: Optional[str],
        activity_code: str,
        confidence: float,
        duration_seconds: float = 0.0
    ) -> ActivityEventModel:
        """Appends a debounced activity event."""
        event = ActivityEventModel(
            track_hash=track_hash,
            zone_id=zone_id,
            activity_code=activity_code,
            confidence=confidence,
            duration_seconds=duration_seconds,
            timestamp=datetime.now(timezone.utc)
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        return event

    @staticmethod
    def record_hourly_metric(
        db: Session,
        hour_bucket: datetime,
        zone_id: str,
        occupancy_rate_pct: float,
        interaction_ratio_pct: Optional[float] = None,
        transition_count: int = 0,
        interruption_count: int = 0,
        coverage_pct: float = 100.0
    ) -> HourlyMetricModel:
        """Appends an hourly metric aggregation row."""
        metric = HourlyMetricModel(
            hour_bucket=hour_bucket,
            zone_id=zone_id,
            occupancy_rate_pct=occupancy_rate_pct,
            interaction_ratio_pct=interaction_ratio_pct,
            transition_count=transition_count,
            interruption_count=interruption_count,
            observation_coverage_pct=coverage_pct,
            is_valid=True
        )
        db.add(metric)
        db.commit()
        db.refresh(metric)
        return metric

    @staticmethod
    def record_operational_outcomes(db: Session, data: OperationalOutcomeBatch) -> OperationalOutcomeModel:
        """Saves ingested external operational outcome records."""
        # Calculate derived output effectiveness score
        thru = 100.0 * (data.actual_completed_units / data.target_planned_units) if data.target_planned_units > 0 else 0.0
        qual = 100.0 * (data.quality_accepted_units / data.quality_assessed_units) if data.quality_assessed_units > 0 else 0.0
        time_pct = 100.0 * (data.on_time_units / data.total_deadline_units) if data.total_deadline_units > 0 else 0.0
        rework_pct = 100.0 * (data.rework_units / data.quality_assessed_units) if data.quality_assessed_units > 0 else 0.0

        output_score = 0.50 * min(100.0, thru) + 0.30 * min(100.0, qual) + 0.20 * min(100.0, time_pct)

        outcome = OperationalOutcomeModel(
            report_date=data.report_date,
            department_code=data.department_code,
            actual_output=data.actual_completed_units,
            target_output=data.target_planned_units,
            quality_rate_pct=round(qual, 1),
            timeliness_rate_pct=round(time_pct, 1),
            rework_rate_pct=round(rework_pct, 1),
            output_effectiveness_score=round(output_score, 1),
            source_system=data.source_system
        )
        db.add(outcome)
        db.commit()
        db.refresh(outcome)
        return outcome

    @staticmethod
    def get_latest_outcomes(db: Session, department_code: str = "ENG") -> Optional[OperationalOutcomeModel]:
        """Queries the most recent operational outcome record for a department."""
        return (
            db.query(OperationalOutcomeModel)
            .filter(OperationalOutcomeModel.department_code == department_code)
            .order_by(OperationalOutcomeModel.id.desc())
            .first()
        )

    @staticmethod
    def get_recent_audit_logs(db: Session, limit: int = 50) -> List[AuditLogModel]:
        """Queries the most recent audit logs."""
        return (
            db.query(AuditLogModel)
            .order_by(AuditLogModel.log_id.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_recent_hourly_metrics(
        db: Session,
        zone_id: Optional[str] = None,
        limit: int = 24
    ) -> List[HourlyMetricModel]:
        """Queries the most recent hourly metrics optionally filtered by zone."""
        query = db.query(HourlyMetricModel)
        if zone_id:
            query = query.filter(HourlyMetricModel.zone_id == zone_id)
        return (
            query.order_by(HourlyMetricModel.id.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def log_audit(
        db: Session,
        user_id: str,
        user_role: str,
        action_type: str,
        resource_id: str,
        client_ip: Optional[str] = "127.0.0.1",
        status_code: int = 200,
        payload: Optional[Any] = None
    ) -> AuditLogModel:
        """Appends an immutable security and privacy audit record."""
        payload_str = json.dumps(payload, default=str) if payload is not None else ""
        payload_hash = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()

        audit = AuditLogModel(
            user_id=user_id,
            user_role=user_role,
            action_type=action_type,
            resource_id=resource_id,
            client_ip=client_ip,
            status_code=status_code,
            payload_hash=payload_hash,
            details=payload_str[:1000] if payload_str else None,
            timestamp=datetime.now(timezone.utc)
        )
        db.add(audit)
        db.commit()
        db.refresh(audit)
        return audit


