import logging
from uuid import UUID
from datetime import datetime, timezone
import hashlib
import json
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.jobs import ProcessingJob
from app.models.media import MediaAsset
from app.models.speech import PipelineRun, SpeechSegment, MouthActivity, AttributionEvidence
from app.services.speech.attribution import attribute_speakers

logger = logging.getLogger(__name__)

async def handle_speaker_attribution(ctx, db: AsyncSession, job_id: str, kwargs: dict):
    job = await db.scalar(select(ProcessingJob).where(ProcessingJob.id == UUID(job_id)))
    if not job:
        raise ValueError("Job not found")
        
    logger.info(f"[Attribution] Starting job {job_id} for meeting {job.meeting_id}")
    
    # Load MediaAsset to get av_offset_ms
    asset = await db.scalar(
        select(MediaAsset).where(MediaAsset.id == job.media_asset_id)
    )
    if not asset:
        raise ValueError("Media asset not found")
    
    av_offset_ms = asset.av_offset_ms or 0
        
    params = {"method": "mouth_activity_90p"}
    params_hash = hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest()
    
    run = PipelineRun(
        meeting_id=job.meeting_id,
        stage="speaker_attribution",
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
    
    try:
        # Load speech segments
        segments_q = await db.execute(
            select(SpeechSegment).where(SpeechSegment.meeting_id == job.meeting_id)
        )
        segments = segments_q.scalars().all()
        
        # Load mouth activities
        activities_q = await db.execute(
            select(MouthActivity).where(MouthActivity.meeting_id == job.meeting_id)
        )
        activities = activities_q.scalars().all()
        
        # Group mouth activities by track
        mouth_map = defaultdict(list)
        for act in activities:
            mouth_map[act.participant_track_id].append(act)
            
        # Run attribution
        attributions = attribute_speakers(segments, mouth_map, av_offset_ms)
        
        # Update segments and save evidence
        evidence_rows = []
        attributed_count = 0
        
        # We index segments for fast update
        seg_dict = {s.id: s for s in segments}
        
        for attr in attributions:
            seg = seg_dict[attr["segment_id"]]
            track_id = attr["participant_track_id"]
            
            if track_id:
                seg.participant_track_id = track_id
                attributed_count += 1
                
                evidence_rows.append(AttributionEvidence(
                    segment_id=seg.id,
                    participant_track_id=track_id,
                    details={"method": "mouth_activity_90p"},
                    score=1.0, rank=1
                ))
            
        from sqlalchemy import delete
        if seg_dict:
            await db.execute(delete(AttributionEvidence).where(AttributionEvidence.segment_id.in_(list(seg_dict.keys()))))
            await db.flush()

        if evidence_rows:
            db.add_all(evidence_rows)
            
        run.status = "succeeded"
        run.finished_at = datetime.now(timezone.utc)
        await db.commit()
        
        logger.info(f"[Attribution] Success. Attributed {attributed_count}/{len(segments)} segments.")
        return {
            "run_id": str(run.id),
            "status": "succeeded",
            "total_segments": len(segments),
            "attributed_segments": attributed_count
        }
        
    except Exception as e:
        logger.exception("[Attribution] Failed")
        run.status = "failed"
        run.finished_at = datetime.now(timezone.utc)
        run.error = str(e)
        await db.commit()
        raise
