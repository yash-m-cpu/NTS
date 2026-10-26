import logging
import os
import tempfile
from uuid import UUID
from datetime import datetime, timezone
import hashlib
import json
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.jobs import ProcessingJob
from app.models.media import MediaAsset
from app.models.speech import PipelineRun, SpeechSegment, SpeechWord, ProsodyWindow, SpeechMetric
from app.services.storage_service import get_s3_client
from app.core.config import settings
from app.services.speech.prosody import extract_f0, pitch_distribution, speaking_rate

logger = logging.getLogger(__name__)

async def handle_prosody_analysis(ctx, db: AsyncSession, job_id: str, kwargs: dict):
    job = await db.scalar(select(ProcessingJob).where(ProcessingJob.id == UUID(job_id)))
    if not job:
        raise ValueError("Job not found")
        
    logger.info(f"[Prosody] Starting job {job_id} for meeting {job.meeting_id}")
    
    asset = await db.scalar(
        select(MediaAsset)
        .where(MediaAsset.meeting_id == job.meeting_id)
        .where(MediaAsset.asset_type == 'audio')
        .order_by(MediaAsset.created_at.desc())
    )
    if not asset:
        asset = await db.scalar(select(MediaAsset).where(MediaAsset.id == job.media_asset_id))
    if not asset:
        raise ValueError("Media asset not found")
        
    params = {"method": "praat_parselmouth"}
    params_hash = hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest()
    
    from sqlalchemy import delete
    await db.execute(delete(ProsodyWindow).where(ProsodyWindow.meeting_id == job.meeting_id))
    await db.execute(delete(SpeechMetric).where(
        SpeechMetric.meeting_id == job.meeting_id,
        SpeechMetric.metric_key.in_(["pitch_p10_hz", "pitch_p50_hz", "pitch_p90_hz", "pitch_range_semitones", "overall_wpm", "articulation_wpm"])
    ))
    await db.flush()

    run = PipelineRun(
        meeting_id=job.meeting_id,
        stage="prosody_analysis",
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
        # Load speech segments and words
        segments_q = await db.execute(
            select(SpeechSegment)
            .where(SpeechSegment.meeting_id == job.meeting_id)
            .where(SpeechSegment.participant_track_id.is_not(None))
        )
        segments = segments_q.scalars().all()
        
        seg_ids = [s.id for s in segments]
        
        words = []
        if seg_ids:
            words_q = await db.execute(
                select(SpeechWord).where(SpeechWord.segment_id.in_(seg_ids)).order_by(SpeechWord.start_ms)
            )
            words = words_q.scalars().all()
            
        with tempfile.TemporaryDirectory() as temp_dir:
            audio_path = os.path.join(temp_dir, "audio.wav")
            async with get_s3_client() as s3:
                await s3.download_file(asset.storage_bucket, asset.storage_key, audio_path)
                
            # Extract full audio pitch & RMS
            times, f0, voiced, rms = extract_f0(audio_path, hop_ms=10)
            
            # Map times into milliseconds
            times_ms = (times * 1000).astype(int)
            
            # 1. Bucket prosody by attributed segment track
            prosody_windows = []
            metrics = []
            
            track_f0s = defaultdict(list)
            track_words = defaultdict(list)
            
            # Map words to tracks
            seg_to_track = {s.id: s.participant_track_id for s in segments}
            for w in words:
                tid = seg_to_track.get(w.segment_id)
                if tid:
                    track_words[tid].append({"start_ms": w.start_ms, "end_ms": w.end_ms, "word": w.word})
            
            # Extract prosody windows that fall inside attributed segments
            # To optimize, we can iterate over segments and slice the numpy arrays
            for seg in segments:
                start_ms = seg.start_ms
                end_ms = seg.end_ms
                tid = seg.participant_track_id
                
                # Slicing the numpy arrays
                mask = (times_ms >= start_ms) & (times_ms <= end_ms)
                
                seg_times = times_ms[mask]
                seg_f0 = f0[mask]
                seg_voiced = voiced[mask]
                seg_rms = rms[mask]
                
                # Add to track F0 for distribution
                track_f0s[tid].extend(seg_f0[seg_voiced])
                
                # We can downsample for storage if needed (e.g. 100ms instead of 10ms)
                # Let's just save one window every 100ms
                for i in range(0, len(seg_times), 10):
                    prosody_windows.append(ProsodyWindow(
                        meeting_id=job.meeting_id,
                        run_id=run.id,
                        participant_track_id=tid,
                        t_ms=int(seg_times[i]),
                        f0_hz=float(seg_f0[i]) if seg_voiced[i] else None,
                        voiced=bool(seg_voiced[i]),
                        rms_db=float(seg_rms[i])
                    ))
                    
            # 2. Calculate track metrics
            for tid, valid_f0 in track_f0s.items():
                p_dist = pitch_distribution(valid_f0)
                if p_dist:
                    for k, v in p_dist.items():
                        metrics.append(SpeechMetric(
                            meeting_id=job.meeting_id,
                            run_id=run.id,
                            participant_track_id=tid,
                            metric_key=f"pitch_{k}",
                            value=v,
                            unit="Hz" if "hz" in k else "semitones",
                            derivation="praat_parselmouth"
                        ))
                        
            for tid, w_list in track_words.items():
                w_rate = speaking_rate(w_list, [])
                if w_rate:
                    for k, v in w_rate.items():
                        metrics.append(SpeechMetric(
                            meeting_id=job.meeting_id,
                            run_id=run.id,
                            participant_track_id=tid,
                            metric_key=k,
                            value=v,
                            unit="wpm" if "wpm" in k else "ratio",
                            derivation="praat_parselmouth"
                        ))
                        
            if prosody_windows:
                db.add_all(prosody_windows)
            if metrics:
                db.add_all(metrics)
                
            run.status = "succeeded"
            run.finished_at = datetime.now(timezone.utc)
            await db.commit()
            
            logger.info(f"[Prosody] Success. Saved {len(prosody_windows)} windows and {len(metrics)} metrics.")
            return {
                "run_id": str(run.id),
                "status": "succeeded"
            }
            
    except Exception as e:
        logger.exception("[Prosody] Failed")
        run.status = "failed"
        run.finished_at = datetime.now(timezone.utc)
        run.error = str(e)
        await db.commit()
        raise
