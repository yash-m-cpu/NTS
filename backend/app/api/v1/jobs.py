from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_org, get_current_user, get_db
from app.models.jobs import ProcessingJob, ProcessingJobEvent
from app.models.users import User
from app.schemas.jobs import (
    JobCancelRequest,
    ProcessingJobEventResponse,
    ProcessingJobResponse,
)

router = APIRouter(prefix="/jobs", tags=["jobs"])

def dump_job(job):
    return ProcessingJobResponse.model_validate(job, from_attributes=True).model_dump()

def dump_event(event):
    return ProcessingJobEventResponse.model_validate(event, from_attributes=True).model_dump()

@router.get("/{id}", response_model=dict)
async def get_job(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_id: str = Depends(get_current_org)
):
    job = await db.scalar(select(ProcessingJob).where(ProcessingJob.id == id))
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"data": dump_job(job)}

@router.get("", response_model=dict)
async def list_jobs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_id: str = Depends(get_current_org),
    meeting_id: UUID | None = None,
    status: str | None = None,
    job_type: str | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    query = select(ProcessingJob)
    if meeting_id:
        query = query.where(ProcessingJob.meeting_id == meeting_id)
    if status:
        query = query.where(ProcessingJob.status == status)
    if job_type:
        query = query.where(ProcessingJob.job_type == job_type)
        
    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    jobs = result.scalars().all()
    
    count_query = select(func.count()).select_from(ProcessingJob)
    if meeting_id:
        count_query = count_query.where(ProcessingJob.meeting_id == meeting_id)
    if status:
        count_query = count_query.where(ProcessingJob.status == status)
    if job_type:
        count_query = count_query.where(ProcessingJob.job_type == job_type)
        
    total = await db.scalar(count_query)
    
    return {
        "data": [dump_job(j) for j in jobs],
        "pagination": {
            "limit": limit,
            "offset": offset,
            "total": total or 0,
            "next_cursor": None
        }
    }

@router.post("/{id}/cancel", response_model=dict)
async def cancel_job(
    id: UUID,
    request: JobCancelRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_id: str = Depends(get_current_org)
):
    job = await db.scalar(select(ProcessingJob).where(ProcessingJob.id == id))
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    if job.status in ["succeeded", "failed", "cancelled"]:
        raise HTTPException(status_code=409, detail="Job already finished")
        
    job.status = "cancelled"
    
    event = ProcessingJobEvent(
        processing_job_id=job.id,
        event_type="cancelled",
        payload={}
    )
    db.add(event)
    await db.commit()
    return {"data": dump_job(job)}

@router.get("/{id}/events", response_model=dict)
async def get_job_events(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_id: str = Depends(get_current_org),
    since: str | None = None
):
    job = await db.scalar(select(ProcessingJob).where(ProcessingJob.id == id))
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    query = select(ProcessingJobEvent).where(ProcessingJobEvent.processing_job_id == id).order_by(ProcessingJobEvent.occurred_at)
    if since:
        # assume since is ISO timestamp
        from datetime import datetime
        since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
        query = query.where(ProcessingJobEvent.occurred_at > since_dt)
        
    result = await db.execute(query)
    events = result.scalars().all()
    
    return {"data": [dump_event(e) for e in events]}
