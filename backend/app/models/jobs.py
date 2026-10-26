import uuid

from sqlalchemy import Column, DateTime, ForeignKey, SmallInteger, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from .base import Base, TimestampMixin


class ProcessingJob(Base, TimestampMixin):
    __tablename__ = 'processing_jobs'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    meeting_id = Column(UUID(as_uuid=True), ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False)
    media_asset_id = Column(UUID(as_uuid=True), ForeignKey('media_assets.id', ondelete='SET NULL'))
    job_type = Column(Text, nullable=False)
    model_version_id = Column(UUID(as_uuid=True), ForeignKey('model_versions.id', ondelete='RESTRICT'))
    status = Column(Text, nullable=False, default='queued')
    priority = Column(SmallInteger, nullable=False, default=0)
    queue_name = Column(Text, nullable=False, default='default')
    attempt_count = Column(SmallInteger, nullable=False, default=0)
    max_attempts = Column(SmallInteger, nullable=False, default=3)
    progress_pct = Column(SmallInteger)
    error_message = Column(Text)
    error_detail = Column(JSONB)
    started_at = Column(DateTime(timezone=True))
    finished_at = Column(DateTime(timezone=True))

class ProcessingJobEvent(Base):
    __tablename__ = 'processing_job_events'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    processing_job_id = Column(UUID(as_uuid=True), ForeignKey('processing_jobs.id', ondelete='CASCADE'), nullable=False)
    event_type = Column(Text, nullable=False)
    payload = Column(JSONB, nullable=False, server_default='{}')
    occurred_at = Column(DateTime(timezone=True), nullable=False, server_default=__import__('sqlalchemy.sql').sql.func.now())
