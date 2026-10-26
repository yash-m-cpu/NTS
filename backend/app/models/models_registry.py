import uuid

from sqlalchemy import Column, DateTime, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID

from .base import Base, TimestampMixin


class ModelVersion(Base, TimestampMixin):
    __tablename__ = 'model_versions'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_family = Column(Text, nullable=False)
    name = Column(Text, nullable=False)
    version = Column(Text, nullable=False)
    artifact_uri = Column(Text)
    training_dataset_id = Column(UUID(as_uuid=True)) # no FK initially to avoid circular dependency
    hyperparameters = Column(JSONB)
    metrics = Column(JSONB)
    status = Column(Text, nullable=False, default='staging')
    released_at = Column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint('model_family', 'name', 'version', name='uq_model_version_family_name_ver'),
    )
