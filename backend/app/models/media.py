import uuid

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    Numeric,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID

from .base import Base, TimestampMixin


class MediaAsset(Base, TimestampMixin):
    __tablename__ = 'media_assets'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    meeting_id = Column(UUID(as_uuid=True), ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False)
    asset_type = Column(Text, nullable=False)
    storage_bucket = Column(Text, nullable=False)
    storage_key = Column(Text, nullable=False)
    storage_provider = Column(Text, nullable=False)
    content_type = Column(Text, nullable=False)
    size_bytes = Column(BigInteger)
    duration_seconds = Column(Numeric(10, 3))
    checksum_sha256 = Column(Text)
    resolution = Column(Text)
    codec = Column(Text)
    upload_status = Column(Text, nullable=False, default='pending')
    uploaded_by_user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))
    deleted_at = Column(DateTime(timezone=True))
    annotated_video_key = Column(Text, nullable=True)  # MinIO key for the annotated video output
    
    # Audio-visual sync offsets (added in Phase 2)
    audio_start_offset_ms = Column(BigInteger, nullable=True)
    video_start_offset_ms = Column(BigInteger, nullable=True)
    av_offset_ms = Column(BigInteger, nullable=True)

    __table_args__ = (
        UniqueConstraint('storage_bucket', 'storage_key', name='uq_media_asset_storage'),
    )
