import uuid
from sqlalchemy import Column, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func
from .base import Base

class InteractionGraph(Base):
    __tablename__ = 'interaction_graphs'
    __table_args__ = (UniqueConstraint('meeting_id', name='uq_interaction_graphs_meeting_id'),)
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    meeting_id = Column(UUID(as_uuid=True), ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False)
    processing_job_id = Column(UUID(as_uuid=True), ForeignKey('processing_jobs.id'), nullable=True)
    graph_data = Column(JSONB, nullable=False)
    computed_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
