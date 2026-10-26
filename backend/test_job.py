import asyncio
import sys
import uuid
from app.core.db import async_session_maker
from app.services.job_service import enqueue_job
from app.models.jobs import ProcessingJob
from app.models.media import MediaAsset
from sqlalchemy import select, update
import aioboto3

MEETING_ID  = uuid.UUID('d4df0f47-dcb7-430b-8d26-f9c2525c72f2')
MEDIA_ID    = uuid.UUID('f50fb9b5-63ee-4ec8-b85d-552b40b4e695')
ORG_ID      = uuid.UUID('4402a01b-92c0-442a-8621-818993a16227')

async def main():
    # 1. Upload test video to minio
    session = aioboto3.Session()
    async with session.client('s3', endpoint_url='http://localhost:9000', aws_access_key_id='minioadmin', aws_secret_access_key='minioadmin') as s3:
        with open('/tmp/test_meeting.mp4', 'rb') as f:
            await s3.put_object(Bucket='nts-uploads', Key='test/test_meeting.mp4', Body=f)

    # 2. Update DB media asset to point to it
    async with async_session_maker() as db:
        await db.execute(update(MediaAsset).where(MediaAsset.id == MEDIA_ID).values(storage_key='test/test_meeting.mp4'))
        await db.commit()

        job = await enqueue_job(db, organization_id=ORG_ID, meeting_id=MEETING_ID, media_asset_id=MEDIA_ID, job_type='cv_extraction')
        print(f'Enqueued job {job.id} status={job.status}')
    
    for attempt in range(15):
        await asyncio.sleep(4)
        async with async_session_maker() as db:
            j = await db.scalar(select(ProcessingJob).where(ProcessingJob.id == job.id))
            print(f'  [{attempt+1}] status={j.status} error={j.error_message}')
            if j.status in ('succeeded', 'failed', 'cancelled'):
                break

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(main())
