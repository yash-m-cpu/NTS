import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID

from .base import Base, TimestampMixin


class Meeting(Base, TimestampMixin):
    __tablename__ = 'meetings'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    title = Column(Text, nullable=False)
    source_type = Column(Text, nullable=False)
    scheduled_at = Column(DateTime(timezone=True))
    started_at = Column(DateTime(timezone=True))
    ended_at = Column(DateTime(timezone=True))
    duration_seconds = Column(Integer)
    status = Column(Text, nullable=False, default='scheduled')
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='RESTRICT'), nullable=False)
    deleted_at = Column(DateTime(timezone=True))
    speech_status = Column(Text, nullable=True)  # Added in Phase 2
