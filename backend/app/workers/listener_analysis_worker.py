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
from app.models.speech import PipelineRun, SpeechSegment, ListenerState, SpeechMetric
from app.models.features import FeatureExtraction
from app.models.participants import ParticipantTrack
from app.services.speech.listener import target_direction, orientation_score, gaze_on_target_pct

logger = logging.getLogger(__name__)

async def handle_listener_analysis(ctx, db: AsyncSession, job_id: str, kwargs: dict):
    job = await db.scalar(select(ProcessingJob).where(ProcessingJob.id == UUID(job_id)))
    if not job:
        raise ValueError("Job not found")
        
    logger.info(f"[Listener] Starting job {job_id} for meeting {job.meeting_id}")
    
    asset = await db.scalar(
        select(MediaAsset)
        .where(MediaAsset.meeting_id == job.meeting_id)
        .where(MediaAsset.asset_type == 'video')
        .order_by(MediaAsset.created_at.desc())
    )
    if not asset:
        asset = await db.scalar(select(MediaAsset).where(MediaAsset.id == job.media_asset_id))
    
    params = {"method": "2d_gaze_heuristic"}
    params_hash = hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest()
    
    from sqlalchemy import delete
    await db.execute(delete(ListenerState).where(ListenerState.meeting_id == job.meeting_id))
    await db.execute(delete(SpeechMetric).where(
        SpeechMetric.meeting_id == job.meeting_id,
        SpeechMetric.metric_key == "avg_listener_gaze_on_speaker_pct"
    ))
    await db.flush()

    run = PipelineRun(
        meeting_id=job.meeting_id,
        stage="listener_analysis",
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
        # Load speech segments (who is talking when)
        segments_q = await db.execute(
            select(SpeechSegment)
            .where(SpeechSegment.meeting_id == job.meeting_id)
            .where(SpeechSegment.participant_track_id.is_not(None))
        )
        segments = segments_q.scalars().all()
        
        # Load tracks
        tracks_q = await db.execute(
            select(ParticipantTrack).where(ParticipantTrack.media_asset_id == asset.id)
        )
        track_ids = [t.id for t in tracks_q.scalars().all()]
        
        # Load visual features (bounding boxes, gaze, head pose)
        features_q = await db.execute(
            select(FeatureExtraction)
            .where(FeatureExtraction.participant_track_id.in_(track_ids))
            .where(FeatureExtraction.feature_type == 'face_pose')
            .order_by(FeatureExtraction.timestamp_ms)
        )
        features = features_q.scalars().all()
        
        # Group features by timestamp
        frames_by_ts = defaultdict(dict) # ts_ms -> track_id -> feat
        for feat in features:
            if feat.timestamp_ms is not None:
                frames_by_ts[feat.timestamp_ms][feat.participant_track_id] = feat
                
        # To calculate listener metrics, we look at each speech segment.
        # For each segment, the attributed track is the SPEAKER.
        # All other tracks are LISTENERS.
        
        listener_states = []
        metrics_by_listener = defaultdict(list)
        
        for seg in segments:
            speaker_id = seg.participant_track_id
            start_ms = seg.start_ms
            end_ms = seg.end_ms
            
            # Find frames in this time range
            # Note: A/V offset applies! Speech segment times are AUDIO.
            # Visual features are VIDEO.
            vid_start = start_ms + (asset.av_offset_ms or 0)
            vid_end = end_ms + (asset.av_offset_ms or 0)
            
            segment_frames = {ts: feats for ts, feats in frames_by_ts.items() if vid_start <= ts <= vid_end}
            
            for listener_id in track_ids:
                if listener_id == speaker_id:
                    continue
                    
                listener_frames_data = []
                
                for ts, feats in segment_frames.items():
                    if speaker_id in feats and listener_id in feats:
                        s_feat = feats[speaker_id]
                        l_feat = feats[listener_id]
                        
                        s_box = s_feat.values.get("box")
                        l_box = l_feat.values.get("box")
                        
                        bearing = target_direction(l_box, s_box)
                        
                        listener_frames_data.append({
                            "gaze": l_feat.values.get("gaze"),
                            "rotation": l_feat.values.get("rotation"),
                            "target_bearing": bearing
                        })
                
                if listener_frames_data:
                    # Calculate pct
                    pct = gaze_on_target_pct(listener_frames_data)
                    if pct is not None:
                        metrics_by_listener[listener_id].append(pct)
                        
                        listener_states.append(ListenerState(
                            meeting_id=job.meeting_id,
                            run_id=run.id,
                            participant_track_id=listener_id,
                            target_track_id=speaker_id,
                            state="listening",
                            derivation="heuristic",
                            start_ms=start_ms, # Save in audio time for consistency with segment
                            end_ms=end_ms,
                            gaze_on_target_pct=pct
                        ))
                        
        if listener_states:
            db.add_all(listener_states)
            
        # Aggregate metrics per track
        metrics = []
        for tid, pcts in metrics_by_listener.items():
            if pcts:
                avg_pct = sum(pcts) / len(pcts)
                metrics.append(SpeechMetric(
                    meeting_id=job.meeting_id,
                    run_id=run.id,
                    participant_track_id=tid,
                    metric_key="avg_listener_gaze_on_speaker_pct",
                    value=avg_pct,
                    unit="ratio",
                    derivation="2d_gaze_heuristic"
                ))
                
        if metrics:
            db.add_all(metrics)
            
        run.status = "succeeded"
        run.finished_at = datetime.now(timezone.utc)
        await db.commit()
        
        logger.info(f"[Listener] Success. Saved {len(listener_states)} states and {len(metrics)} metrics.")
        return {
            "run_id": str(run.id),
            "status": "succeeded"
        }
        
    except Exception as e:
        logger.exception("[Listener] Failed")
        run.status = "failed"
        run.finished_at = datetime.now(timezone.utc)
        run.error = str(e)
        await db.commit()
        raise
