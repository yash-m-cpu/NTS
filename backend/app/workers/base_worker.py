import logging
import traceback
from datetime import datetime
from uuid import UUID

from sqlalchemy import select

from app.core.db import async_session_maker
from app.models.jobs import ProcessingJob, ProcessingJobEvent
from app.workers.noop_worker import handle_noop
from app.workers.cv_extraction_worker import handle_cv_extraction
from app.workers.stt_worker import handle_stt_transcription
from app.workers.feature_fusion_worker import handle_feature_fusion
from app.workers.nts_scoring_worker import handle_nts_scoring
from app.workers.interaction_worker import handle_interaction_analysis
from app.workers.video_annotation_worker import handle_video_annotation
from app.workers.audio_preprocess_worker import handle_audio_preprocess
from app.workers.vad_worker import handle_vad
from app.workers.mouth_activity_worker import handle_mouth_activity
from app.workers.speaker_attribution_worker import handle_speaker_attribution
from app.workers.prosody_worker import handle_prosody_analysis
from app.workers.listener_analysis_worker import handle_listener_analysis

logger = logging.getLogger(__name__)

WORKER_HANDLERS = {
    "noop": handle_noop,
    "cv_extraction": handle_cv_extraction,
    "stt_transcription": handle_stt_transcription,
    "feature_fusion": handle_feature_fusion,
    "nts_scoring": handle_nts_scoring,
    "interaction_analysis": handle_interaction_analysis,
    "annotated_video_generation": handle_video_annotation,
    "audio_preprocess": handle_audio_preprocess,
    "vad": handle_vad,
    "mouth_activity": handle_mouth_activity,
    "speaker_attribution": handle_speaker_attribution,
    "prosody_analysis": handle_prosody_analysis,
    "listener_analysis": handle_listener_analysis,
}


async def _record_failure(job_uuid: UUID, error: BaseException) -> None:
    """Open a fresh session to record failure — needed because the main session may be rolled back.
    Catches ALL exceptions including asyncio.CancelledError and TimeoutError so the job
    status is ALWAYS written to the DB — never left as a zombie 'running' state.
    """
    tb = traceback.format_exc()
    logger.error("Job %s failed: %s\n%s", job_uuid, error, tb)
    try:
        async with async_session_maker() as db:
            job = await db.scalar(select(ProcessingJob).where(ProcessingJob.id == job_uuid))
            if not job:
                return
            if job.attempt_count >= job.max_attempts:
                job.status = "failed"
                job.finished_at = datetime.now()
                job.error_message = str(error)[:500]  # truncate so it fits in the column
                job.error_detail = {"traceback": tb[:5000]}
                event_type = "failed"
            else:
                job.status = "queued"  # will be retried by arq
                event_type = "retrying"

            event = ProcessingJobEvent(
                processing_job_id=job.id,
                event_type=event_type,
                payload={"error_message": str(error)[:500], "attempt": job.attempt_count},
            )
            db.add(event)
            await db.commit()
    except Exception as inner:
        # Last-resort log — don't let a DB error inside _record_failure swallow the original
        logger.critical("CRITICAL: Failed to record job failure for %s: %s", job_uuid, inner)


async def process_job(ctx, job_id: str, **kwargs):
    job_uuid = UUID(job_id)
    logger.info("Processing job %s", job_uuid)

    # --- Mark job as running ---
    async with async_session_maker() as db:
        job = await db.scalar(select(ProcessingJob).where(ProcessingJob.id == job_uuid))
        if not job:
            logger.warning("Job %s not found in DB, skipping.", job_uuid)
            return
        if job.status == "cancelled":
            logger.info("Job %s is cancelled, skipping.", job_uuid)
            return

        job.status = "running"
        job.started_at = datetime.now()
        job.attempt_count += 1

        event = ProcessingJobEvent(
            processing_job_id=job.id,
            event_type="started",
            payload={
                "job_type": job.job_type,
                "model_version_id": str(job.model_version_id) if job.model_version_id else None,
            },
        )
        db.add(event)
        await db.commit()

    # Keep a reference to job fields we need after the handler session closes
    job_type = job.job_type
    org_id = job.organization_id
    meeting_id = job.meeting_id
    media_asset_id = job.media_asset_id
    model_version_id = job.model_version_id

    # --- Run the handler in its OWN session ---
    handler = WORKER_HANDLERS.get(job_type, handle_noop)
    try:
        async with async_session_maker() as db:
            result = await handler(ctx, db, job_id, kwargs)

        # --- Mark succeeded in a fresh session ---
        async with async_session_maker() as db:
            job = await db.scalar(select(ProcessingJob).where(ProcessingJob.id == job_uuid))
            if job:
                job.status = "succeeded"
                job.finished_at = datetime.now()
                job.progress_pct = 100
                event = ProcessingJobEvent(
                    processing_job_id=job.id,
                    event_type="succeeded",
                    payload=result if isinstance(result, dict) else {},
                )
                db.add(event)

                # Orchestration: trigger next step in the pipeline cascade
                # NOTE: argument order must match enqueue_job(db, org_id, meeting_id, job_type, media_asset_id, model_version_id)
                from app.services.job_service import enqueue_job
                if job_type == "cv_extraction":
                    await enqueue_job(db, org_id, meeting_id, "audio_preprocess", media_asset_id, model_version_id)
                    # Chain annotated video generation if the user opted in
                    if kwargs.get("generate_annotated_video"):
                        await enqueue_job(db, org_id, meeting_id, "annotated_video_generation", media_asset_id, model_version_id)
                elif job_type == "audio_preprocess":
                    await enqueue_job(db, org_id, meeting_id, "vad", media_asset_id, model_version_id)
                elif job_type == "vad":
                    await enqueue_job(db, org_id, meeting_id, "stt_transcription", media_asset_id, model_version_id)
                elif job_type == "stt_transcription":
                    await enqueue_job(db, org_id, meeting_id, "mouth_activity", media_asset_id, model_version_id)
                elif job_type == "mouth_activity":
                    await enqueue_job(db, org_id, meeting_id, "speaker_attribution", media_asset_id, model_version_id)
                elif job_type == "speaker_attribution":
                    await enqueue_job(db, org_id, meeting_id, "prosody_analysis", media_asset_id, model_version_id)
                elif job_type == "prosody_analysis":
                    await enqueue_job(db, org_id, meeting_id, "listener_analysis", media_asset_id, model_version_id)
                elif job_type == "listener_analysis":
                    await enqueue_job(db, org_id, meeting_id, "feature_fusion", media_asset_id, model_version_id)
                elif job_type == "feature_fusion":
                    await enqueue_job(db, org_id, meeting_id, "nts_scoring", media_asset_id, model_version_id)
                    await enqueue_job(db, org_id, meeting_id, "interaction_analysis", media_asset_id, model_version_id)

                await db.commit()
                logger.info("Job %s (%s) succeeded: %s", job_uuid, job_type, result)

    except BaseException as e:
        # Catches TimeoutError, CancelledError, and all regular Exceptions
        await _record_failure(job_uuid, e)
        raise
