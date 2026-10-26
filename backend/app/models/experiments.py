import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from .base import Base, TimestampMixin


class Experiment(Base, TimestampMixin):
    __tablename__ = 'experiments'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id = Column(UUID(as_uuid=True), ForeignKey('datasets.id', ondelete='RESTRICT'), nullable=False)
    resulting_model_version_id = Column(UUID(as_uuid=True), ForeignKey('model_versions.id', ondelete='SET NULL'))
    name = Column(Text, nullable=False)
    config = Column(JSONB)
    status = Column(Text, nullable=False)
    metrics = Column(JSONB)
    started_at = Column(DateTime(timezone=True))
    finished_at = Column(DateTime(timezone=True))
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))
