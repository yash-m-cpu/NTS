import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID

from .base import Base


class NtsScore(Base):
    __tablename__ = 'nts_scores'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    meeting_id = Column(UUID(as_uuid=True), ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False)
    participant_track_id = Column(UUID(as_uuid=True), ForeignKey('participant_tracks.id', ondelete='CASCADE'))
    model_version_id = Column(UUID(as_uuid=True), ForeignKey('model_versions.id', ondelete='RESTRICT'), nullable=False)
    processing_job_id = Column(UUID(as_uuid=True), ForeignKey('processing_jobs.id', ondelete='RESTRICT'), nullable=False)
    nts_score = Column(Numeric(6, 3), nullable=False)
    confidence_interval_low = Column(Numeric(6, 3))
    confidence_interval_high = Column(Numeric(6, 3))
    component_scores = Column(JSONB, nullable=False)
    input_metric_ids = Column(ARRAY(UUID(as_uuid=True)))
    computed_at = Column(DateTime(timezone=True), nullable=False, server_default=__import__('sqlalchemy.sql').sql.func.now())
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=__import__('sqlalchemy.sql').sql.func.now())

class ModelPrediction(Base):
    __tablename__ = 'model_predictions'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    model_version_id = Column(UUID(as_uuid=True), ForeignKey('model_versions.id', ondelete='RESTRICT'), nullable=False)
    nts_score_id = Column(UUID(as_uuid=True), ForeignKey('nts_scores.id', ondelete='CASCADE'))
    subject_type = Column(Text, nullable=False)
    subject_id = Column(UUID(as_uuid=True), nullable=False)
    prediction_type = Column(Text, nullable=False)
    payload = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=__import__('sqlalchemy.sql').sql.func.now())
