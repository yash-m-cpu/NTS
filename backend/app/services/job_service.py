from uuid import UUID

from arq import create_pool
from arq.connections import RedisSettings
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.jobs import ProcessingJob, ProcessingJobEvent

_arq_pool = None

async def get_arq_pool():
    global _arq_pool
    if _arq_pool is None:
        _arq_pool = await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))
    return _arq_pool

async def enqueue_job(
    db: AsyncSession,
    organization_id: UUID,
    meeting_id: UUID,
    job_type: str,
    media_asset_id: UUID | None = None,
    model_version_id: UUID | None = None,
    queue_name: str = "default",
    max_attempts: int = 3,
    extra_kwargs: dict | None = None,
) -> ProcessingJob:
    query = select(ProcessingJob).where(
        ProcessingJob.meeting_id == meeting_id,
        ProcessingJob.job_type == job_type,
        ProcessingJob.status.in_(["queued", "running"])
    )
    existing_job = await db.scalar(query)
    
    if existing_job:
        return existing_job
        
    job = ProcessingJob(
        organization_id=organization_id,
        meeting_id=meeting_id,
        media_asset_id=media_asset_id,
        job_type=job_type,
        model_version_id=model_version_id,
        status="queued",
        queue_name=queue_name,
        max_attempts=max_attempts
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    
    event = ProcessingJobEvent(
        processing_job_id=job.id,
        event_type="queued",
        payload={}
    )
    db.add(event)
    await db.commit()
    
    pool = await get_arq_pool()
    enqueue_kwargs = {"job_id": str(job.id), "_job_id": str(job.id)}
    if extra_kwargs:
        enqueue_kwargs.update(extra_kwargs)
    await pool.enqueue_job("process_job", **enqueue_kwargs)
    
    return job
