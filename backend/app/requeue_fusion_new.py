import asyncio
from uuid import UUID
from app.core.db import async_session_maker
from sqlalchemy import select
from app.models.media import MediaAsset
from app.services.job_service import enqueue_job
from app.models.jobs import ProcessingJob

async def main():
    async with async_session_maker() as db:
        meeting_id = UUID('d43ddc80-5924-4517-b41d-db7a3fdb975a')
        asset = await db.scalar(select(MediaAsset).where(MediaAsset.meeting_id == meeting_id).order_by(MediaAsset.created_at.desc()))
        
        # First, fail old queued jobs so enqueue_job doesn't return them
        jobs = await db.scalars(select(ProcessingJob).where(ProcessingJob.status == 'queued'))
        for j in jobs:
            j.status = 'failed'
            j.error_message = 'Reset to unblock queue'
        await db.commit()
        
        job = await enqueue_job(
            db=db,
            organization_id=asset.organization_id,
            meeting_id=meeting_id,
            media_asset_id=asset.id,
            job_type="feature_fusion",
            model_version_id=None
        )
        print(f"Enqueued {job.id}")

asyncio.run(main())
