import asyncio
import os
import aioboto3
from app.core.config import settings

async def check():
    session = aioboto3.Session()
    async with session.client('s3', endpoint_url=settings.AWS_ENDPOINT_URL, aws_access_key_id=settings.AWS_ACCESS_KEY_ID, aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY) as s3:
        res = await s3.list_objects_v2(Bucket=settings.S3_BUCKET_NAME, Prefix='annotated/')
        for obj in res.get('Contents', []):
            print(f"{obj['Key']} - {obj['Size'] / 1024 / 1024:.2f} MB")

if __name__ == "__main__":
    asyncio.run(check())
