from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

class MeetingCreate(BaseModel):
    project_id: UUID
    title: str
    source_type: str
    scheduled_at: datetime | None = None

class MeetingUpdate(BaseModel):
    title: str | None = None
    status: str | None = None

class MeetingResponse(BaseModel):
    id: UUID
    organization_id: UUID
    project_id: UUID
    title: str
    source_type: str
    scheduled_at: datetime | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    duration_seconds: int | None = None
    status: str
    created_by_user_id: UUID
    created_at: datetime
    updated_at: datetime

class AnalysisRequest(BaseModel):
    pipeline: str = "full"
    model_version_id: UUID | None = None
    generate_annotated_video: bool = False
