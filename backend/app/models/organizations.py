import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import CITEXT, JSONB, UUID

from .base import Base, TimestampMixin


class Organization(Base, TimestampMixin):
    __tablename__ = 'organizations'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    slug = Column(CITEXT, unique=True, nullable=False)
    plan_tier = Column(Text, nullable=False, default='free')
    settings = Column(JSONB, nullable=False, server_default='{}')
    deleted_at = Column(DateTime(timezone=True))

class OrganizationMember(Base, TimestampMixin):
    __tablename__ = 'organization_members'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    role = Column(Text, nullable=False)
    invited_by_user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))
    joined_at = Column(DateTime(timezone=True), nullable=False, server_default=__import__('sqlalchemy.sql').sql.func.now())

    __table_args__ = (
        UniqueConstraint('organization_id', 'user_id', name='uq_org_member'),
    )
