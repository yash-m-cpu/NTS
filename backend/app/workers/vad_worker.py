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
from app.models.speech import PipelineRun, VadSegment
from app.services.storage_service import get_s3_client
from app.core.config import settings
from app.services.speech.vad import detect_speech, merge_close_intervals

logger = logging.getLogger(__name__)

async def handle_vad(ctx, db: AsyncSession, job_id: str, kwargs: dict):
    job = await db.scalar(select(ProcessingJob).where(ProcessingJob.id == UUID(job_id)))
    if not job:
        raise ValueError("Job not found")
        
    logger.info(f"[VAD] Starting job {job_id} for meeting {job.meeting_id}")

    # Resolve audio asset
    asset = await db.scalar(
        select(MediaAsset)
        .where(MediaAsset.meeting_id == job.meeting_id)
        .where(MediaAsset.asset_type == 'audio')
        .order_by(MediaAsset.created_at.desc())
    )
    if not asset:
        raise ValueError(f"No audio media asset found for meeting {job.meeting_id}. Ensure audio_preprocess ran.")
        
    params = {
        "threshold": 0.5,
        "min_speech_ms": 250,
        "min_silence_ms": 300,
        "pad_ms": 100,
        "merge_gap_ms": 200
    }
    params_hash = hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest()
    
    # Idempotency check
    existing_run = await db.scalar(
        select(PipelineRun).where(
            PipelineRun.meeting_id == job.meeting_id,
            PipelineRun.stage == "vad",
            PipelineRun.params_hash == params_hash,
            PipelineRun.status == "succeeded"
        )
    )
    if existing_run:
        logger.info(f"[VAD] Idempotent hit: run {existing_run.id} already succeeded.")
        return {"run_id": str(existing_run.id), "status": "succeeded", "cached": True}
        
    run = PipelineRun(
        meeting_id=job.meeting_id,
        stage="vad",
        status="running",
        params=params,
        params_hash=params_hash,
        code_version="v1",
        model_versions={"silero_vad": "v3"},
        input_run_ids={},
        started_at=datetime.now(timezone.utc)
    )
    db.add(run)
    await db.flush()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        audio_path = os.path.join(temp_dir, "audio.wav")
        
        try:
            logger.info(f"[VAD] Downloading audio: {asset.storage_key}")
            async with get_s3_client() as s3:
                await s3.download_file(settings.S3_BUCKET_NAME, asset.storage_key, audio_path)
                
            # Run VAD in executor
            loop = asyncio.get_running_loop()
            raw_intervals = await loop.run_in_executor(
                None, 
                lambda: detect_speech(
                    audio_path, 
                    threshold=params["threshold"], 
                    min_speech_ms=params["min_speech_ms"],
                    min_silence_ms=params["min_silence_ms"],
                    pad_ms=params["pad_ms"]
                )
            )
            
            intervals = merge_close_intervals(raw_intervals, gap_ms=params["merge_gap_ms"])
            
            vad_segments = []
            for inv in intervals:
                vad_segments.append(VadSegment(
                    meeting_id=job.meeting_id,
                    run_id=run.id,
                    start_ms=inv.start_ms,
                    end_ms=inv.end_ms,
                    mean_prob=inv.mean_prob,
                    method="silero_vad_v3"
                ))
                
            if vad_segments:
                db.add_all(vad_segments)
                
            run.status = "succeeded"
            run.finished_at = datetime.now(timezone.utc)
            await db.commit()
            
            logger.info(f"[VAD] Success. Extracted {len(vad_segments)} segments.")
            return {
                "run_id": str(run.id),
                "status": "succeeded",
                "segment_count": len(vad_segments)
            }
            
        except Exception as e:
            logger.exception("[VAD] Failed")
            run.status = "failed"
            run.finished_at = datetime.now(timezone.utc)
            run.error = str(e)
            await db.commit()
            raise
