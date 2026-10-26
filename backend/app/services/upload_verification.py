import filetype
from fastapi import HTTPException
from app.services.storage_service import get_s3_client
from app.core.config import settings

ALLOWED_MIME_TYPES = {
    "video/mp4",
    "video/quicktime",
    "video/webm",
    "audio/mpeg",
    "audio/wav"
}

async def verify_upload(storage_key: str, expected_content_type: str) -> str:
    """Verifies file type of an uploaded object by reading its first 2048 bytes."""
    async with get_s3_client() as s3:
        try:
            # Fetch first 2048 bytes for magic number analysis
            response = await s3.get_object(
                Bucket=settings.S3_BUCKET_NAME,
                Key=storage_key,
                Range="bytes=0-2047"
            )
            file_head = await response["Body"].read()
        except Exception as e:
            raise HTTPException(status_code=404, detail="File not found in storage")
            
    kind = filetype.guess(file_head)
    
    if not kind:
        # If filetype can't determine it, fallback or error out
        # Actually in strict mode, we should error out.
        raise HTTPException(status_code=422, detail="Unable to determine file type")
        
    actual_mime = kind.mime
    if actual_mime not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported media type detected: {actual_mime}"
        )
        
    return "verified"
