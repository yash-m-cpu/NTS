import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from .base import Base, TimestampMixin


class Dataset(Base, TimestampMixin):
    __tablename__ = 'datasets'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='SET NULL'))
    name = Column(Text, nullable=False)
    purpose = Column(Text, nullable=False)
    description = Column(Text)
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))

class DatasetSample(Base):
    __tablename__ = 'dataset_samples'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id = Column(UUID(as_uuid=True), ForeignKey('datasets.id', ondelete='CASCADE'), nullable=False)
    meeting_id = Column(UUID(as_uuid=True), ForeignKey('meetings.id', ondelete='SET NULL'))
    participant_track_id = Column(UUID(as_uuid=True), ForeignKey('participant_tracks.id', ondelete='SET NULL'))
    label = Column(JSONB)
    split = Column(Text)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=__import__('sqlalchemy.sql').sql.func.now())
