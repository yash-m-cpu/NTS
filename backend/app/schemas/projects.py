from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

class ProjectCreate(BaseModel):
    name: str
    description: str | None = None

class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: str | None = None

class ProjectResponse(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    description: str | None = None
    created_by_user_id: UUID
    status: str
    created_at: datetime
    updated_at: datetime
