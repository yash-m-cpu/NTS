import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Numeric, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from .base import Base, TimestampMixin


class Archetype(Base, TimestampMixin):
    __tablename__ = 'archetypes'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key = Column(Text, unique=True, nullable=False)
    display_name = Column(Text, nullable=False)
    description = Column(Text)

class ParticipantArchetype(Base):
    __tablename__ = 'participant_archetypes'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    participant_track_id = Column(UUID(as_uuid=True), ForeignKey('participant_tracks.id', ondelete='CASCADE'), nullable=False)
    archetype_id = Column(UUID(as_uuid=True), ForeignKey('archetypes.id', ondelete='RESTRICT'), nullable=False)
    model_version_id = Column(UUID(as_uuid=True), ForeignKey('model_versions.id', ondelete='RESTRICT'), nullable=False)
    confidence = Column(Numeric(5, 4))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=__import__('sqlalchemy.sql').sql.func.now())

    __table_args__ = (
        UniqueConstraint('participant_track_id', 'model_version_id', name='uq_participant_archetype_track_model'),
    )
