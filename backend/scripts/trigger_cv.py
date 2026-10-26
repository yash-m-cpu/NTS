import asyncio
import uuid
from app.core.db import async_session_maker
from app.services.job_service import enqueue_job

async def trigger():
    org_id = uuid.UUID('4402a01b-92c0-442a-8621-818993a16227')
    meeting_id = uuid.UUID('ee46846e-d1fb-409d-88ea-5026342abe2b')
    media_asset_id = uuid.UUID('b51e942a-ff7c-4db2-b54a-7296d42442f8')
    
    async with async_session_maker() as db:
        job = await enqueue_job(
            db, 
            org_id, 
            meeting_id, 
            "cv_extraction", 
            media_asset_id,
            extra_kwargs={"generate_annotated_video": True}
        )
        print("Enqueued cv_extraction job:", job.id)

if __name__ == "__main__":
    asyncio.run(trigger())
