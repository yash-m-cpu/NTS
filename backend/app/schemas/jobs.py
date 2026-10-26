from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class JobCancelRequest(BaseModel):
    status: str = "cancelled"

class ProcessingJobEventResponse(BaseModel):
    id: UUID
    processing_job_id: UUID
    event_type: str
    payload: dict[str, Any]
    occurred_at: datetime

class ProcessingJobResponse(BaseModel):
    id: UUID
    organization_id: UUID
    meeting_id: UUID
    media_asset_id: UUID | None = None
    job_type: str
    model_version_id: UUID | None = None
    status: str
    priority: int
    queue_name: str
    attempt_count: int
    max_attempts: int
    progress_pct: int | None = None
    error_message: str | None = None
    error_detail: dict[str, Any] | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
