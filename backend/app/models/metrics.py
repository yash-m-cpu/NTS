import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID

from .base import Base


class BehavioralMetric(Base):
    __tablename__ = 'behavioral_metrics'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    participant_track_id = Column(UUID(as_uuid=True), ForeignKey('participant_tracks.id', ondelete='CASCADE'), nullable=False)
    metric_key = Column(Text, nullable=False)
    metric_category = Column(Text, nullable=False)
    window_start_ms = Column(Integer)
    window_end_ms = Column(Integer)
    value = Column(Numeric(12, 6), nullable=False)
    unit = Column(Text)
    computed_by_pipeline_version = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=__import__('sqlalchemy.sql').sql.func.now())
