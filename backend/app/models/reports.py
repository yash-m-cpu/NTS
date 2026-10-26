import uuid

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    SmallInteger,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID

from .base import Base, TimestampMixin


class Report(Base, TimestampMixin):
    __tablename__ = 'reports'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    meeting_id = Column(UUID(as_uuid=True), ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False)
    generated_by_user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))
    processing_job_id = Column(UUID(as_uuid=True), ForeignKey('processing_jobs.id', ondelete='SET NULL'))
    title = Column(Text, nullable=False)
    status = Column(Text, nullable=False)
    export_format = Column(Text)
    storage_bucket = Column(Text)
    storage_key = Column(Text)
    deleted_at = Column(DateTime(timezone=True))

class ReportSection(Base, TimestampMixin):
    __tablename__ = 'report_sections'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id = Column(UUID(as_uuid=True), ForeignKey('reports.id', ondelete='CASCADE'), nullable=False)
    section_key = Column(Text, nullable=False)
    title = Column(Text, nullable=False)
    order_index = Column(SmallInteger, nullable=False)
    content_markdown = Column(Text)
    content_source = Column(Text, nullable=False)

    __table_args__ = (
        UniqueConstraint('report_id', 'section_key', name='uq_report_sections_report_key'),
    )
