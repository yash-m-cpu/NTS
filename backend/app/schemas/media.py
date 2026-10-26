from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

class UploadInitiateRequest(BaseModel):
    meeting_id: UUID
    asset_type: str
    content_type: str
    size_bytes: int
    checksum_sha256: str | None = None

class UploadInitiateResponse(BaseModel):
    media_asset_id: UUID
    upload_url: str
    upload_method: str = "PUT"
    expires_in: int

class UploadCompleteResponse(BaseModel):
    status: str

class MediaAssetResponse(BaseModel):
    id: UUID
    organization_id: UUID
    meeting_id: UUID
    asset_type: str
    content_type: str
    size_bytes: int | None = None
    duration_seconds: float | None = None
    upload_status: str
    uploaded_by_user_id: UUID | None = None
    created_at: datetime
