from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from app.api.deps import get_current_user, get_current_org, get_db
from app.models.media import MediaAsset
from app.models.meetings import Meeting
from app.models.users import User
from app.schemas.media import UploadInitiateRequest, UploadInitiateResponse
from app.services.storage_service import generate_presigned_upload_url, generate_presigned_download_url
from app.services.upload_verification import verify_upload

router = APIRouter(prefix="/media", tags=["media"])

@router.post("/uploads/initiate", response_model=dict, status_code=201)
async def initiate_upload(
    upload_in: UploadInitiateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_id: str = Depends(get_current_org)
):
    # Verify meeting exists
    meeting = await db.scalar(select(Meeting).where(Meeting.id == upload_in.meeting_id, Meeting.deleted_at.is_(None)))
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
        
    # Content type check
    allowed_types = ["video/mp4", "video/quicktime", "video/webm", "audio/mpeg", "audio/wav"]
    if upload_in.content_type not in allowed_types:
        raise HTTPException(status_code=415, detail="Unsupported media type")
        
    # Size check (e.g., 5GB limit)
    MAX_UPLOAD_BYTES = 5 * 1024 * 1024 * 1024
    if upload_in.size_bytes > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="File too large")
        
    ext = upload_in.content_type.split("/")[-1]
    if ext == "quicktime":
        ext = "mov"
        
    url, storage_key = await generate_presigned_upload_url(
        content_type=upload_in.content_type,
        org_id=UUID(org_id),
        meeting_id=upload_in.meeting_id,
        extension=ext
    )
    
    asset = MediaAsset(
        organization_id=UUID(org_id),
        meeting_id=upload_in.meeting_id,
        asset_type=upload_in.asset_type,
        storage_bucket="nts-uploads",
        storage_key=storage_key,
        storage_provider="s3",
        content_type=upload_in.content_type,
        size_bytes=upload_in.size_bytes,
        checksum_sha256=upload_in.checksum_sha256,
        uploaded_by_user_id=current_user.id
    )
    db.add(asset)
    await db.commit()
    await db.refresh(asset)
    
    return {
        "data": {
            "media_asset_id": asset.id,
            "upload_url": url,
            "upload_method": "PUT",
            "expires_in": 900
        }
    }

@router.post("/uploads/{media_asset_id}/complete", response_model=dict)
async def complete_upload(
    media_asset_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_id: str = Depends(get_current_org)
):
    asset = await db.scalar(select(MediaAsset).where(MediaAsset.id == media_asset_id))
    if not asset:
        raise HTTPException(status_code=404, detail="Media asset not found")
        
    status = await verify_upload(asset.storage_key, asset.content_type)
    
    asset.upload_status = status
    await db.commit()
    
    return {"data": {"status": status}}

@router.get("/{id}", response_model=dict)
async def get_media(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_id: str = Depends(get_current_org)
):
    asset = await db.scalar(select(MediaAsset).where(MediaAsset.id == id, MediaAsset.deleted_at.is_(None)))
    if not asset:
        raise HTTPException(status_code=404, detail="Media asset not found")
        
    # Returns presigned download URL
    url = await generate_presigned_download_url(asset.storage_key)
    
    # We should return a dict with asset metadata and the URL
    asset_dict = {
        "id": asset.id,
        "meeting_id": asset.meeting_id,
        "content_type": asset.content_type,
        "upload_status": asset.upload_status,
        "download_url": url
    }
    
    return {"data": asset_dict}
