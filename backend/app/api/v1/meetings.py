import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_org, get_current_user, get_db
from app.core.config import settings
from app.models.meetings import Meeting
from app.models.users import User
from app.schemas.meetings import (
    AnalysisRequest,
    MeetingCreate,
    MeetingResponse,
    MeetingUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/meetings", tags=["meetings"])

def dump_meeting(meeting):
    return MeetingResponse.model_validate(meeting, from_attributes=True).model_dump()

@router.get("", response_model=dict)
async def list_meetings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_id: str = Depends(get_current_org),
    project_id: UUID | None = None,
    status: str | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    query = select(Meeting).where(Meeting.deleted_at.is_(None))
    if project_id:
        query = query.where(Meeting.project_id == project_id)
    if status:
        query = query.where(Meeting.status == status)
        
    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    meetings = result.scalars().all()
    
    count_query = select(func.count()).select_from(Meeting).where(Meeting.deleted_at.is_(None))
    if project_id:
        count_query = count_query.where(Meeting.project_id == project_id)
    if status:
        count_query = count_query.where(Meeting.status == status)
    
    total = await db.scalar(count_query)
    
    return {
        "data": [dump_meeting(m) for m in meetings],
        "pagination": {
            "limit": limit,
            "offset": offset,
            "total": total or 0,
            "next_cursor": None
        }
    }

@router.post("", response_model=dict, status_code=201)
async def create_meeting(
    meeting_in: MeetingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_id: str = Depends(get_current_org)
):
    meeting = Meeting(
        organization_id=UUID(org_id),
        project_id=meeting_in.project_id,
        title=meeting_in.title,
        source_type=meeting_in.source_type,
        scheduled_at=meeting_in.scheduled_at,
        created_by_user_id=current_user.id
    )
    db.add(meeting)
    await db.commit()
    
    if not meeting.id:
        from uuid import uuid4
        meeting.id = uuid4()
        
    return {"data": {"id": str(meeting.id), "status": meeting.status}}

@router.get("/{id}", response_model=dict)
async def get_meeting(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_id: str = Depends(get_current_org)
):
    meeting = await db.scalar(select(Meeting).where(Meeting.id == id, Meeting.deleted_at.is_(None)))
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return {"data": dump_meeting(meeting)}

@router.patch("/{id}", response_model=dict)
async def update_meeting(
    id: UUID,
    meeting_in: MeetingUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_id: str = Depends(get_current_org)
):
    meeting = await db.scalar(select(Meeting).where(Meeting.id == id, Meeting.deleted_at.is_(None)))
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
        
    if meeting_in.title is not None:
        meeting.title = meeting_in.title
    if meeting_in.status is not None:
        meeting.status = meeting_in.status
        
    await db.commit()
    
    if not meeting.updated_at:
        from datetime import datetime
        meeting.updated_at = datetime.now()
        
    return {"data": dump_meeting(meeting)}

@router.delete("/{id}", status_code=204)
async def delete_meeting(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_id: str = Depends(get_current_org)
):
    meeting = await db.scalar(select(Meeting).where(Meeting.id == id, Meeting.deleted_at.is_(None)))
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
        
    from datetime import datetime
    meeting.deleted_at = datetime.now()
    await db.commit()

@router.post("/{id}/analysis", response_model=dict, status_code=202)
async def analyze_meeting(
    id: UUID,
    request: AnalysisRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_id: str = Depends(get_current_org)
):
    meeting = await db.scalar(select(Meeting).where(Meeting.id == id, Meeting.deleted_at.is_(None)))
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
        
    # Find the latest media asset for this meeting
    from app.models.media import MediaAsset
    asset = await db.scalar(select(MediaAsset).where(MediaAsset.meeting_id == id, MediaAsset.asset_type == "video").order_by(MediaAsset.created_at.desc()))
    
    # We should enqueue a job using job_service
    from app.services.job_service import enqueue_job
    job = await enqueue_job(
        db=db,
        organization_id=UUID(org_id),
        meeting_id=id,
        media_asset_id=asset.id if asset else None,
        job_type="cv_extraction",
        model_version_id=request.model_version_id,
        extra_kwargs={"generate_annotated_video": request.generate_annotated_video},
    )
    
    return {
        "data": {
            "job_id": str(job.id),
            "status": job.status,
            "generate_annotated_video": request.generate_annotated_video,
            "created_at": job.created_at.isoformat() if job.created_at else None
        }
    }


@router.get("/{id}/annotated-video", response_model=dict)
async def get_annotated_video_status(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_id: str = Depends(get_current_org),
):
    """
    Returns the annotated video status for a meeting.
    If complete, returns a presigned download URL.
    """
    from app.models.media import MediaAsset
    from app.models.jobs import ProcessingJob

    asset = await db.scalar(
        select(MediaAsset).where(MediaAsset.meeting_id == id, MediaAsset.asset_type == "video").order_by(MediaAsset.created_at.desc())
    )
    if not asset:
        raise HTTPException(status_code=404, detail="No media asset found for this meeting")

    # Check if annotated video job is running/queued
    annotation_job = await db.scalar(
        select(ProcessingJob)
        .where(ProcessingJob.meeting_id == id, ProcessingJob.job_type == "annotated_video_generation")
        .order_by(ProcessingJob.created_at.desc())
    )

    status = "not_requested"
    if annotation_job:
        status = annotation_job.status  # queued, running, succeeded, failed

    annotated_url = None
    if asset.annotated_video_key:
        # Generate presigned URL for direct browser playback
        from app.services.storage_service import get_s3_client
        try:
            import time
            async with get_s3_client() as s3:
                annotated_url = await s3.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": settings.S3_BUCKET_NAME, "Key": asset.annotated_video_key},
                    ExpiresIn=3600,
                )
                # Append cache buster to bypass aggressive browser video caching
                annotated_url += f"&_t={int(time.time())}"
            status = "completed"
        except Exception as e:
            logger.warning("Could not generate presigned URL for annotated video: %s", e)

    return {
        "data": {
            "status": status,
            "annotated_video_url": annotated_url,
            "job_id": str(annotation_job.id) if annotation_job else None,
            "job_status": annotation_job.status if annotation_job else None,
            "error_message": annotation_job.error_message if annotation_job else None,
        }
    }

@router.get("/{id}/features", response_model=dict)
async def get_meeting_features(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_id: str = Depends(get_current_org),
    participant_track_id: UUID | None = None,
    feature_type: str | None = None,
    limit: int = Query(1000, ge=1, le=10000),
    offset: int = Query(0, ge=0)
):
    from app.models.features import FeatureExtraction
    from app.models.participants import ParticipantTrack
    from app.models.media import MediaAsset
    
    query = select(FeatureExtraction).join(
        ParticipantTrack, ParticipantTrack.id == FeatureExtraction.participant_track_id
    ).join(
        MediaAsset, MediaAsset.id == ParticipantTrack.media_asset_id
    ).where(MediaAsset.meeting_id == id)
    
    if participant_track_id:
        query = query.where(FeatureExtraction.participant_track_id == participant_track_id)
    else:
        from app.models.jobs import ProcessingJob
        latest_job_result = await db.execute(
            select(ProcessingJob.id)
            .where(ProcessingJob.meeting_id == id, ProcessingJob.job_type == "cv_extraction", ProcessingJob.status == "succeeded")
            .order_by(ProcessingJob.finished_at.desc())
            .limit(1)
        )
        latest_job_id = latest_job_result.scalar()
        if latest_job_id:
            query = query.where(FeatureExtraction.processing_job_id == latest_job_id)
            
    if feature_type:
        query = query.where(FeatureExtraction.feature_type == feature_type)
        
    query = query.order_by(FeatureExtraction.timestamp_ms).limit(limit).offset(offset)
    
    result = await db.execute(query)
    features = result.scalars().all()
    
    data = []
    for f in features:
        data.append({
            "id": str(f.id),
            "participant_track_id": str(f.participant_track_id),
            "feature_type": f.feature_type,
            "timestamp_ms": f.timestamp_ms,
            "confidence": float(f.confidence) if f.confidence is not None else None,
            "values": f.values
        })
        
    return {
        "data": data,
        "pagination": {
            "limit": limit,
            "offset": offset,
            "next_cursor": None
        }
    }

@router.get("/{id}/tracks", response_model=dict)
async def get_meeting_tracks(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_id: str = Depends(get_current_org)
):
    from app.models.participants import ParticipantTrack
    from app.models.media import MediaAsset
    from app.models.jobs import ProcessingJob
    
    # Get the latest successful cv_extraction job for this meeting
    latest_job_result = await db.execute(
        select(ProcessingJob.id)
        .where(ProcessingJob.meeting_id == id, ProcessingJob.job_type == "cv_extraction", ProcessingJob.status == "succeeded")
        .order_by(ProcessingJob.finished_at.desc())
        .limit(1)
    )
    latest_job_id = latest_job_result.scalar()

    if not latest_job_id:
        return {"data": []}

    # Fetch tracks only for this latest job
    tracks_result = await db.execute(
        select(ParticipantTrack)
        .where(ParticipantTrack.processing_job_id == latest_job_id)
        .order_by(ParticipantTrack.track_label)
    )
    tracks = tracks_result.scalars().all()
    
    return {"data": [{
        "id": str(t.id),
        "track_label": t.track_label,
        "first_seen_at_ms": t.first_seen_at_ms,
        "last_seen_at_ms": t.last_seen_at_ms,
        "detection_frame_count": t.detection_frame_count,
        "avg_detection_confidence": float(t.avg_detection_confidence) if t.avg_detection_confidence else None,
    } for t in tracks]}

@router.get("/{id}/metrics", response_model=dict)
async def get_meeting_metrics(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_id: str = Depends(get_current_org),
    participant_track_id: UUID | None = None
):
    from app.models.metrics import BehavioralMetric
    from app.models.speech import SpeechMetric
    from app.models.participants import ParticipantTrack
    from app.models.media import MediaAsset

    bm_query = select(BehavioralMetric).join(
        ParticipantTrack, ParticipantTrack.id == BehavioralMetric.participant_track_id
    ).join(
        MediaAsset, MediaAsset.id == ParticipantTrack.media_asset_id
    ).where(MediaAsset.meeting_id == id)
    
    sm_query = select(SpeechMetric).where(SpeechMetric.meeting_id == id)
    
    if participant_track_id:
        bm_query = bm_query.where(BehavioralMetric.participant_track_id == participant_track_id)
        sm_query = sm_query.where(SpeechMetric.participant_track_id == participant_track_id)
        
    bm_result = await db.execute(bm_query)
    behavioral_metrics = bm_result.scalars().all()
    
    sm_result = await db.execute(sm_query)
    speech_metrics = sm_result.scalars().all()
    
    data = []
    for m in behavioral_metrics:
        data.append({
            "id": str(m.id),
            "participant_track_id": str(m.participant_track_id),
            "metric_key": m.metric_key,
            "value": float(m.value) if m.value is not None else None,
            "unit": m.unit,
            "metric_category": m.metric_category
        })
        
    for m in speech_metrics:
        data.append({
            "id": str(m.id),
            "participant_track_id": str(m.participant_track_id) if m.participant_track_id else None,
            "metric_key": m.metric_key,
            "value": float(m.value) if m.value is not None else None,
            "unit": m.unit,
            "metric_category": "speech_prosody" if "pitch" in m.metric_key or "wpm" in m.metric_key else "listener_behavior"
        })
    
    return {"data": data}

@router.get("/{id}/speaking-summary", response_model=dict)
async def get_speaking_summary(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_id: str = Depends(get_current_org)
):
    from app.models.participants import ParticipantTrack
    from app.models.media import MediaAsset
    from app.models.metrics import BehavioralMetric
    from app.models.speech import SpeechSegment
    from app.models.jobs import ProcessingJob
    
    # Get active tracks for this meeting (match get_meeting_tracks)
    latest_job = await db.scalar(
        select(ProcessingJob)
        .where(
            ProcessingJob.meeting_id == id,
            ProcessingJob.job_type == "cv_extraction",
            ProcessingJob.status == "succeeded"
        )
        .order_by(ProcessingJob.finished_at.desc())
    )
    if latest_job:
        tracks_result = await db.execute(
            select(ParticipantTrack)
            .where(ParticipantTrack.processing_job_id == latest_job.id)
            .order_by(ParticipantTrack.track_label)
        )
        tracks = tracks_result.scalars().all()
    else:
        tracks_result = await db.execute(
            select(ParticipantTrack)
            .join(MediaAsset, MediaAsset.id == ParticipantTrack.media_asset_id)
            .where(MediaAsset.meeting_id == id)
            .order_by(ParticipantTrack.track_label)
        )
        tracks = tracks_result.scalars().all()
    
    summary = []
    for track in tracks:
        # Get metrics
        metrics_result = await db.execute(
            select(BehavioralMetric)
            .where(BehavioralMetric.participant_track_id == track.id)
        )
        metrics = metrics_result.scalars().all()
        metric_dict = {m.metric_key: float(m.value) if m.value is not None else None for m in metrics}
        
        # Get turns from SpeechSegment
        features_result = await db.execute(
            select(SpeechSegment)
            .where(
                SpeechSegment.participant_track_id == track.id,
                SpeechSegment.meeting_id == id
            )
            .order_by(SpeechSegment.start_ms)
        )
        features = features_result.scalars().all()
        
        turns = []
        seg_speaking_time = 0.0
        for f in features:
            s_sec = (f.start_ms / 1000.0) if f.start_ms is not None else 0.0
            e_sec = (f.end_ms / 1000.0) if f.end_ms is not None else 0.0
            seg_speaking_time += max(0.0, e_sec - s_sec)
            turns.append({
                "start": s_sec,
                "end": e_sec,
                "text": f.text or ""
            })
            
        spk_time = metric_dict.get("speaking_time_seconds")
        if spk_time is None and turns:
            spk_time = round(seg_speaking_time, 1)
            
        turn_cnt = metric_dict.get("turn_count")
        if turn_cnt is None and turns:
            turn_cnt = len(turns)
            
        avg_turn = metric_dict.get("avg_turn_duration_seconds")
        if avg_turn is None and turn_cnt:
            avg_turn = round(spk_time / turn_cnt, 1) if turn_cnt > 0 else 0.0

        summary.append({
            "track_id": str(track.id),
            "track_label": track.track_label,
            "speaking_time_seconds": spk_time,
            "speech_ratio": metric_dict.get("speech_ratio"),
            "turn_count": turn_cnt,
            "avg_turn_duration_seconds": avg_turn,
            "turns": turns
        })
        
    return {"data": summary}

@router.get("/{id}/interaction-graph", response_model=dict)
async def get_interaction_graph(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_id: str = Depends(get_current_org)
):
    from app.models.interactions import InteractionGraph
    graph = await db.scalar(
        select(InteractionGraph).where(InteractionGraph.meeting_id == id)
    )
    
    if not graph:
        return {"data": None, "message": "Not yet computed"}
        
    return {"data": graph.graph_data}

@router.get("/{id}/prosody", response_model=dict)
async def get_meeting_prosody(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_id: str = Depends(get_current_org),
    participant_track_id: UUID | None = None
):
    from app.models.speech import ProsodyWindow
    query = select(ProsodyWindow).where(ProsodyWindow.meeting_id == id)
    if participant_track_id:
        query = query.where(ProsodyWindow.participant_track_id == participant_track_id)
        
    query = query.order_by(ProsodyWindow.t_ms)
    
    result = await db.execute(query)
    windows = result.scalars().all()
    
    data = [{
        "t_ms": w.t_ms,
        "participant_track_id": str(w.participant_track_id) if w.participant_track_id else None,
        "f0_hz": w.f0_hz,
        "voiced": w.voiced,
        "rms_db": w.rms_db
    } for w in windows]
    
    return {"data": data}
