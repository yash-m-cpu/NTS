import asyncio
import logging
import os
import tempfile
from uuid import UUID
from datetime import datetime, timezone
import hashlib
import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.jobs import ProcessingJob
from app.models.media import MediaAsset
from app.models.speech import PipelineRun, MouthActivity
from app.models.features import FeatureExtraction
from app.models.participants import ParticipantTrack
from app.services.storage_service import get_s3_client
from app.core.config import settings
from app.services.speech.mouth_activity import extract_mouth_activity_from_video

logger = logging.getLogger(__name__)

async def handle_mouth_activity(ctx, db: AsyncSession, job_id: str, kwargs: dict):
    job = await db.scalar(select(ProcessingJob).where(ProcessingJob.id == UUID(job_id)))
    if not job:
        raise ValueError("Job not found")
        
    logger.info(f"[Mouth Activity] Starting job {job_id} for meeting {job.meeting_id}")

    # Resolve raw video asset
    asset = await db.scalar(
        select(MediaAsset)
        .where(MediaAsset.meeting_id == job.meeting_id)
        .where(MediaAsset.asset_type == 'video')
        .order_by(MediaAsset.created_at.desc())
    )
    if not asset:
        asset = await db.scalar(select(MediaAsset).where(MediaAsset.id == job.media_asset_id))
    if not asset:
        raise ValueError(f"No video asset found for meeting {job.meeting_id}.")
        
    params = {"method": "mediapipe_face_mesh_v1"}
    params_hash = hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest()
    
    from sqlalchemy import delete

    # Delete previous mouth activities for this meeting to ensure clean state
    await db.execute(delete(MouthActivity).where(MouthActivity.meeting_id == job.meeting_id))
    await db.flush()
        
    run = PipelineRun(
        meeting_id=job.meeting_id,
        stage="mouth_activity",
        status="running",
        params=params,
        params_hash=params_hash,
        code_version="v1",
        model_versions={"mediapipe_face_mesh": "v1"},
        input_run_ids={},
        started_at=datetime.now(timezone.utc)
    )
    db.add(run)
    await db.flush()
    
    # 1. Fetch tracks and bounding boxes from DB (latest cv_extraction job)
    tracks_bboxes = {} # track_id (UUID string) -> list of {"frame", "box", "timestamp_ms"}
    
    latest_cv_job = await db.scalar(
        select(ProcessingJob)
        .where(
            ProcessingJob.meeting_id == job.meeting_id,
            ProcessingJob.job_type == "cv_extraction",
            ProcessingJob.status == "succeeded"
        )
        .order_by(ProcessingJob.finished_at.desc())
    )
    
    if latest_cv_job:
        tracks_q = await db.execute(
            select(ParticipantTrack).where(ParticipantTrack.processing_job_id == latest_cv_job.id)
        )
    else:
        tracks_q = await db.execute(
            select(ParticipantTrack)
            .where(ParticipantTrack.media_asset_id == asset.id)
            .where(ParticipantTrack.track_label.like("person_%"))
        )
    tracks = tracks_q.scalars().all()
    
    for track in tracks:
        # Fetch face_pose features (which contain bounding boxes)
        features_q = await db.execute(
            select(FeatureExtraction)
            .where(FeatureExtraction.participant_track_id == track.id)
            .where(FeatureExtraction.feature_type == 'face_pose')
            .order_by(FeatureExtraction.frame_index)
        )
        features = features_q.scalars().all()
        
        bboxes = []
        for feat in features:
            box = feat.values.get("box")
            if box and feat.frame_index is not None:
                bboxes.append({
                    "frame": feat.frame_index,
                    "box": box,
                    "timestamp_ms": feat.timestamp_ms
                })
        
        if bboxes:
            tracks_bboxes[str(track.id)] = bboxes

    if not tracks_bboxes:
        logger.warning(f"[Mouth Activity] No tracks or bounding boxes found for meeting {job.meeting_id}")
        run.status = "succeeded"
        run.finished_at = datetime.now(timezone.utc)
        await db.commit()
        return {"run_id": str(run.id), "status": "succeeded", "count": 0}

    with tempfile.TemporaryDirectory() as temp_dir:
        video_path = os.path.join(temp_dir, "video.mp4")
        
        try:
            logger.info(f"[Mouth Activity] Downloading video: {asset.storage_key}")
            async with get_s3_client() as s3:
                await s3.download_file(settings.S3_BUCKET_NAME, asset.storage_key, video_path)
                
            # Run extraction in executor
            loop = asyncio.get_running_loop()
            results = await loop.run_in_executor(
                None, 
                lambda: extract_mouth_activity_from_video(video_path, tracks_bboxes)
            )
            
            mouth_activities = []
            for track_id, activities in results.items():
                for act in activities:
                    mouth_activities.append(MouthActivity(
                        meeting_id=job.meeting_id,
                        run_id=run.id,
                        participant_track_id=UUID(track_id),
                        t_ms=act["timestamp_ms"],
                        mar=act["mouth_open_ratio"], visible=True
                    ))
                    
            if mouth_activities:
                db.add_all(mouth_activities)
                
            run.status = "succeeded"
            run.finished_at = datetime.now(timezone.utc)
            await db.commit()
            
            logger.info(f"[Mouth Activity] Success. Extracted {len(mouth_activities)} data points.")
            return {
                "run_id": str(run.id),
                "status": "succeeded",
                "count": len(mouth_activities)
            }
            
        except Exception as e:
            logger.exception("[Mouth Activity] Failed")
            run.status = "failed"
            run.finished_at = datetime.now(timezone.utc)
            run.error = str(e)
            await db.commit()
            raise
