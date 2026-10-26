import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, Numeric, Text
from sqlalchemy.dialects.postgresql import CITEXT, UUID

from .base import Base, TimestampMixin


class Participant(Base, TimestampMixin):
    __tablename__ = 'participants'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    display_name = Column(Text, nullable=False)
    external_reference = Column(Text)
    deleted_at = Column(DateTime(timezone=True))

class MeetingParticipant(Base, TimestampMixin):
    __tablename__ = 'meeting_participants'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_id = Column(UUID(as_uuid=True), ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False)
    display_name = Column(Text, nullable=False)
    email = Column(CITEXT)
    role_in_meeting = Column(Text)
    external_platform_id = Column(Text)
    joined_at = Column(DateTime(timezone=True))
    left_at = Column(DateTime(timezone=True))

    __table_args__ = (
        Index('uq_meeting_participants_platform', 'meeting_id', 'external_platform_id', unique=True, postgresql_where=__import__('sqlalchemy.sql').text('external_platform_id IS NOT NULL')),
    )

class ParticipantTrack(Base, TimestampMixin):
    __tablename__ = 'participant_tracks'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    media_asset_id = Column(UUID(as_uuid=True), ForeignKey('media_assets.id', ondelete='CASCADE'), nullable=False)
    meeting_participant_id = Column(UUID(as_uuid=True), ForeignKey('meeting_participants.id', ondelete='SET NULL'))
    participant_id = Column(UUID(as_uuid=True), ForeignKey('participants.id', ondelete='SET NULL'))
    processing_job_id = Column(UUID(as_uuid=True), ForeignKey('processing_jobs.id', ondelete='RESTRICT'), nullable=False)
    track_label = Column(Text, nullable=False)
    first_seen_at_ms = Column(Integer, nullable=False)
    last_seen_at_ms = Column(Integer, nullable=False)
    detection_frame_count = Column(Integer)
    avg_detection_confidence = Column(Numeric(5, 4))
