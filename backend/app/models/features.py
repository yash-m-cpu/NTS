import uuid

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from .base import Base


class FeatureExtraction(Base):
    __tablename__ = 'feature_extractions'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    participant_track_id = Column(UUID(as_uuid=True), ForeignKey('participant_tracks.id', ondelete='CASCADE'), nullable=False)
    media_asset_id = Column(UUID(as_uuid=True), ForeignKey('media_assets.id', ondelete='CASCADE'), nullable=False)
    processing_job_id = Column(UUID(as_uuid=True), ForeignKey('processing_jobs.id', ondelete='RESTRICT'), nullable=False)
    model_version_id = Column(UUID(as_uuid=True), ForeignKey('model_versions.id', ondelete='RESTRICT'), nullable=False)
    extraction_pipeline_version = Column(Text, nullable=False)
    feature_type = Column(Text, nullable=False)
    timestamp_ms = Column(Integer, nullable=False)
    frame_index = Column(Integer)
    confidence = Column(Numeric(5, 4))
    values = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=__import__('sqlalchemy.sql').sql.func.now())

class FeatureWindow(Base):
    __tablename__ = 'feature_windows'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    participant_track_id = Column(UUID(as_uuid=True), ForeignKey('participant_tracks.id', ondelete='CASCADE'), nullable=False)
    feature_type = Column(Text, nullable=False)
    window_start_ms = Column(Integer, nullable=False)
    window_end_ms = Column(Integer, nullable=False)
    aggregation = Column(JSONB, nullable=False)
    source_extraction_count = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=__import__('sqlalchemy.sql').sql.func.now())

    __table_args__ = (
        UniqueConstraint('participant_track_id', 'feature_type', 'window_start_ms', 'window_end_ms', name='uq_feature_windows_track_feature_time'),
    )
