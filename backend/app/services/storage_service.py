import uuid
from contextlib import asynccontextmanager
import aioboto3
from fastapi import HTTPException

from app.core.config import settings

session = aioboto3.Session()

@asynccontextmanager
async def get_s3_client():
    async with session.client(
        "s3",
        endpoint_url=settings.AWS_ENDPOINT_URL,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION_NAME
    ) as client:
        yield client

async def generate_presigned_upload_url(
    content_type: str, org_id: uuid.UUID, meeting_id: uuid.UUID, extension: str
) -> tuple[str, str]:
    """Generates a presigned URL and returns the URL and the storage_key."""
    file_id = uuid.uuid4()
    storage_key = f"orgs/{org_id}/meetings/{meeting_id}/raw/{file_id}.{extension}"
    
    async with get_s3_client() as s3:
        try:
            url = await s3.generate_presigned_url(
                ClientMethod="put_object",
                Params={
                    "Bucket": settings.S3_BUCKET_NAME,
                    "Key": storage_key,
                    "ContentType": content_type
                },
                ExpiresIn=900  # 15 minutes
            )
            return url, storage_key
        except Exception as e:
            # Note: logging could be added here
            raise HTTPException(status_code=500, detail="Failed to generate upload URL")

async def generate_presigned_download_url(storage_key: str) -> str:
    async with get_s3_client() as s3:
        try:
            url = await s3.generate_presigned_url(
                ClientMethod="get_object",
                Params={
                    "Bucket": settings.S3_BUCKET_NAME,
                    "Key": storage_key,
                },
                ExpiresIn=900
            )
            return url
        except Exception as e:
            raise HTTPException(status_code=500, detail="Failed to generate download URL")
