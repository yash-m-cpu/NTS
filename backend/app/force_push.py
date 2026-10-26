import asyncio
from uuid import UUID
from app.core.db import async_session_maker
from sqlalchemy import select
from app.models.jobs import ProcessingJob
from app.services.job_service import get_arq_pool

async def force_push():
    async with async_session_maker() as db:
        jobs = await db.scalars(select(ProcessingJob).where(ProcessingJob.status == 'queued'))
        pool = await get_arq_pool()
        for j in jobs:
            print(f"Force pushing {j.id} to ARQ")
            await pool.enqueue_job("process_job", job_id=str(j.id), _job_id=str(j.id))

asyncio.run(force_push())
