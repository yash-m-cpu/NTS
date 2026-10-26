import uuid
from sqlalchemy import Column, DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from .base import Base


class NtsVisualReport(Base):
    __tablename__ = "nts_visual_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    meeting_id = Column(UUID(as_uuid=True), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    participant_track_id = Column(UUID(as_uuid=True), ForeignKey("participant_tracks.id", ondelete="CASCADE"), nullable=False)
    input_hash = Column(Text, nullable=False)
    prompt_version = Column(Text, nullable=False, default="1.0")
    model_name = Column(Text, nullable=False)
    status = Column(Text, nullable=False, default="pending")
    report_json = Column(JSONB)
    pdf_bucket = Column(Text)
    pdf_key = Column(Text)
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
