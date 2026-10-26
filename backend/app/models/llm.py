import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from .base import Base


class LlmGeneration(Base):
    __tablename__ = 'llm_generations'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    report_section_id = Column(UUID(as_uuid=True), ForeignKey('report_sections.id', ondelete='SET NULL'))
    nts_score_id = Column(UUID(as_uuid=True), ForeignKey('nts_scores.id', ondelete='SET NULL'))
    model_version_id = Column(UUID(as_uuid=True), ForeignKey('model_versions.id', ondelete='RESTRICT'), nullable=False)
    prompt_template_key = Column(Text, nullable=False)
    prompt_tokens = Column(Integer)
    completion_tokens = Column(Integer)
    input_context = Column(JSONB)
    output_text = Column(Text, nullable=False)
    latency_ms = Column(Integer)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=__import__('sqlalchemy.sql').sql.func.now())
