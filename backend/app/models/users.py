import uuid

from sqlalchemy import Column, DateTime, Text
from sqlalchemy.dialects.postgresql import CITEXT, UUID

from .base import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = 'users'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(CITEXT, unique=True, nullable=False)
    password_hash = Column(Text, nullable=False)
    full_name = Column(Text, nullable=False)
    status = Column(Text, nullable=False, default='invited')
    email_verified_at = Column(DateTime(timezone=True))
    last_login_at = Column(DateTime(timezone=True))
    deleted_at = Column(DateTime(timezone=True))
