import asyncio
from app.core.db import async_session_maker
from app.services.job_service import enqueue_job
from app.models.media import MediaAsset
from sqlalchemy import select

async def main():
    db = async_session_maker()
    async with db as session:
        ma = await session.scalar(select(MediaAsset).where(MediaAsset.storage_key.like('%efdb19d3%')))
        if not ma: return
        job = await enqueue_job(session, organization_id=ma.organization_id, meeting_id=ma.meeting_id, media_asset_id=ma.id, job_type='cv_extraction')
        print(job.id)
asyncio.run(main())
