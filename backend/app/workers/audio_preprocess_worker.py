import asyncio
import logging
import os
import tempfile
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.jobs import ProcessingJob
from app.models.media import MediaAsset
from app.models.speech import PipelineRun
from app.services.storage_service import get_s3_client
from app.core.config import settings
from app.services.audio.ffmpeg_utils import probe_streams, compute_av_offset_ms, extract_audio
from datetime import datetime, timezone
import hashlib
import json

logger = logging.getLogger(__name__)

async def handle_audio_preprocess(ctx, db: AsyncSession, job_id: str, kwargs: dict):
    job = await db.scalar(select(ProcessingJob).where(ProcessingJob.id == UUID(job_id)))
    if not job:
        raise ValueError("Job not found")
        
    logger.info(f"[Audio Preprocess] Starting job {job_id} for meeting {job.meeting_id}")

    # Resolve media asset
    media_asset_id = job.media_asset_id
    if not media_asset_id:
        asset = await db.scalar(
            select(MediaAsset)
            .where(MediaAsset.meeting_id == job.meeting_id)
            .where(MediaAsset.asset_type == 'video')
            .order_by(MediaAsset.created_at.desc())
        )
        if not asset:
            raise ValueError(f"No video media asset for meeting {job.meeting_id}")
        media_asset_id = asset.id
        storage_key = asset.storage_key
    else:
        asset = await db.scalar(select(MediaAsset).where(MediaAsset.id == media_asset_id))
        if not asset:
            raise ValueError(f"MediaAsset {media_asset_id} not found")
        storage_key = asset.storage_key
        
    params = {"sample_rate": 16000, "mono": True}
    params_hash = hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest()
        
    # Check for existing successful pipeline run to ensure idempotency
    existing_run = await db.scalar(
        select(PipelineRun).where(
            PipelineRun.meeting_id == job.meeting_id,
            PipelineRun.stage == "audio_preprocess",
            PipelineRun.params_hash == params_hash,
            PipelineRun.status == "succeeded"
        )
    )
    if existing_run:
        logger.info(f"[Audio Preprocess] Idempotent hit: run {existing_run.id} already succeeded.")
        return {"run_id": str(existing_run.id), "status": "succeeded", "cached": True}

    run = PipelineRun(
        meeting_id=job.meeting_id,
        stage="audio_preprocess",
        status="running",
        params=params,
        params_hash=params_hash,
        code_version="v1",
        model_versions={},
        input_run_ids={},
        started_at=datetime.now(timezone.utc)
    )
    db.add(run)
    await db.flush()

    with tempfile.TemporaryDirectory() as temp_dir:
        video_path = os.path.join(temp_dir, "video.mp4")
        audio_path = os.path.join(temp_dir, "audio.wav")
        
        try:
            logger.info(f"[Audio Preprocess] Downloading video: {storage_key}")
            async with get_s3_client() as s3:
                await s3.download_file(settings.S3_BUCKET_NAME, storage_key, video_path)
            
            # Probe streams
            info = probe_streams(video_path)
            
            # Check if there's actually an audio stream
            has_audio = any(s.get('codec_type') == 'audio' for s in info.get('streams', []))
            if not has_audio:
                logger.warning(f"[Audio Preprocess] No audio stream in {storage_key}")
                run.status = "succeeded"
                run.finished_at = datetime.now(timezone.utc)
                run.error = "No audio stream found (has_audio=false)"
                await db.commit()
                return {"run_id": str(run.id), "status": "succeeded", "has_audio": False}

            offset_ms = compute_av_offset_ms(info)
            logger.info(f"[Audio Preprocess] Computed A/V offset: {offset_ms}ms")
            
            # Extract audio (synchronously but in thread pool)
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, extract_audio, video_path, audio_path, params["sample_rate"], params["mono"])
            
            # Upload extracted audio to MinIO
            audio_key = f"speech/orgs/{job.organization_id}/meetings/{job.meeting_id}/audio_16k.wav"
            async with get_s3_client() as s3:
                await s3.upload_file(
                    audio_path,
                    settings.S3_BUCKET_NAME,
                    audio_key,
                    ExtraArgs={"ContentType": "audio/wav"}
                )
            
            # Record offset on the raw video asset
            asset.av_offset_ms = offset_ms
            
            # Create MediaAsset for the audio
            audio_size = os.path.getsize(audio_path)
            audio_asset = MediaAsset(
                organization_id=job.organization_id,
                meeting_id=job.meeting_id,
                asset_type="audio",
                storage_bucket=settings.S3_BUCKET_NAME,
                storage_key=audio_key,
                storage_provider="s3",
                content_type="audio/wav",
                size_bytes=audio_size,
                upload_status="uploaded",
                uploaded_by_user_id=asset.uploaded_by_user_id
            )
            db.add(audio_asset)
            
            # Mark run as succeeded
            run.status = "succeeded"
            run.finished_at = datetime.now(timezone.utc)
            await db.commit()
            
            logger.info(f"[Audio Preprocess] Success. Extracted audio size: {audio_size} bytes")
            return {
                "run_id": str(run.id),
                "status": "succeeded",
                "offset_ms": offset_ms,
                "audio_asset_id": str(audio_asset.id),
                "has_audio": True
            }

        except Exception as e:
            logger.exception("[Audio Preprocess] Failed")
            run.status = "failed"
            run.finished_at = datetime.now(timezone.utc)
            run.error = str(e)
            await db.commit()
            raise
