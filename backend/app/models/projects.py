import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from .base import Base, TimestampMixin


class Project(Base, TimestampMixin):
    __tablename__ = 'projects'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    name = Column(Text, nullable=False)
    description = Column(Text)
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='RESTRICT'), nullable=False)
    status = Column(Text, nullable=False, default='active')
    deleted_at = Column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint('organization_id', 'name', name='uq_project_org_name'),
    )
