from uuid import UUID
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.media import MediaAsset
from app.models.metrics import BehavioralMetric
from app.models.speech import SpeechMetric
from app.services.feature_windowing import bucket_features_for_media_assets
from app.services.metrics import registry
import numpy as np

async def handle_feature_fusion(ctx, db: AsyncSession, job_id: str, kwargs: dict):
    # From kwargs or job, we need to know the meeting_id or media_asset_id
    from app.models.jobs import ProcessingJob
    job = await db.scalar(select(ProcessingJob).where(ProcessingJob.id == UUID(job_id)))
    if not job:
        raise Exception(f"Job {job_id} not found")
        
    meeting_id = job.meeting_id
    if not meeting_id:
        raise Exception("feature_fusion job requires a meeting_id")
        
    result = await db.scalars(select(MediaAsset).where(MediaAsset.meeting_id == meeting_id))
    media_assets = result.all()
    media_asset_ids = [ma.id for ma in media_assets]
    
    org_id = job.organization_id
    
    # 1. Bucket extractions into windows
    windows = await bucket_features_for_media_assets(db, media_asset_ids, org_id)
    
    # 2. Compute metrics
    # Group windows by track_id
    from collections import defaultdict
    track_windows = defaultdict(list)
    for w in windows:
        track_windows[w.participant_track_id].append(w)
        
    # Delete existing metrics for these tracks to be idempotent
    track_ids = list(track_windows.keys())
    if track_ids:
        await db.execute(delete(BehavioralMetric).where(BehavioralMetric.participant_track_id.in_(track_ids)))
        
    pipeline_version = registry.version
    
    for track_id, track_ws in track_windows.items():
        for metric_key, compute_func in registry.get_metrics().items():
            metric_result = compute_func(track_ws)
            if metric_result:
                bm = BehavioralMetric(
                    organization_id=org_id,
                    participant_track_id=track_id,
                    metric_key=metric_key,
                    metric_category=metric_result.get("category", "uncategorized"),
                    value=metric_result["value"],
                    unit=metric_result.get("unit"),
                    computed_by_pipeline_version=pipeline_version
                )
                db.add(bm)
                
    # --- PHASE 11: Multimodal fusion (interaction metrics and participation) ---
    # Fetch SpeechMetrics generated in Phases 9 and 10
    speech_metrics_q = await db.execute(
        select(SpeechMetric).where(SpeechMetric.meeting_id == meeting_id)
    )
    speech_metrics = speech_metrics_q.scalars().all()
    
    metrics_by_track = defaultdict(dict)
    for sm in speech_metrics:
        metrics_by_track[sm.participant_track_id][sm.metric_key] = sm.value
        
    # Gather global distribution arrays
    all_speaking_rates = []
    all_f0_ranges = []
    all_speaking_times = []
    all_listener_pcts = []
    
    for tid, m_dict in metrics_by_track.items():
        if "articulation_wpm" in m_dict: all_speaking_rates.append(m_dict["articulation_wpm"])
        if "pitch_range_semitones" in m_dict: all_f0_ranges.append(m_dict["pitch_range_semitones"])
        # Wait, speaking time was computed by turn_taking_metrics in BehavioralMetric!
        
    # Also fetch the newly generated BehavioralMetrics for speaking time
    bm_q = await db.execute(select(BehavioralMetric).where(BehavioralMetric.participant_track_id.in_(track_ids)))
    existing_bms = bm_q.scalars().all()
    
    for bm in existing_bms:
        if bm.metric_key == "speaking_time_seconds":
            all_speaking_times.append(bm.value)
            metrics_by_track[bm.participant_track_id]["speaking_time_seconds"] = bm.value
            
        # from listener metric
    for tid, m_dict in metrics_by_track.items():
        if "avg_listener_gaze_on_speaker_pct" in m_dict:
            all_listener_pcts.append(m_dict["avg_listener_gaze_on_speaker_pct"])
            
    def z_score(val, arr):
        if not arr or len(arr) < 2: return 0.0
        arr_np = np.array(arr)
        std = np.std(arr_np)
        if std == 0: return 0.0
        return float((val - np.mean(arr_np)) / std)
        
    for track_id, m_dict in metrics_by_track.items():
        # Calculate dominance
        # Weighted z-score: 0.6 * wpm + 0.4 * f0_range
        wpm_z = z_score(m_dict.get("articulation_wpm", 0), all_speaking_rates)
        f0_z = z_score(m_dict.get("pitch_range_semitones", 0), all_f0_ranges)
        dominance = (0.6 * wpm_z) + (0.4 * f0_z)
        
        db.add(BehavioralMetric(
            organization_id=org_id,
            participant_track_id=track_id,
            metric_key="multimodal_dominance",
            metric_category="temporal",
            value=dominance,
            unit="z-score",
            computed_by_pipeline_version=pipeline_version
        ))
        
        # Calculate participation
        # 0.7 * speaking_time_z + 0.3 * listener_gaze_z
        st_z = z_score(m_dict.get("speaking_time_seconds", 0), all_speaking_times)
        list_z = z_score(m_dict.get("avg_listener_gaze_on_speaker_pct", 0), all_listener_pcts)
        participation = (0.7 * st_z) + (0.3 * list_z)
        
        db.add(BehavioralMetric(
            organization_id=org_id,
            participant_track_id=track_id,
            metric_key="multimodal_participation",
            metric_category="temporal",
            value=participation,
            unit="z-score",
            computed_by_pipeline_version=pipeline_version
        ))
                
    await db.commit()
    
    return {"message": "Feature fusion completed successfully"}
