from typing import List, Dict, Any
from uuid import UUID
from collections import defaultdict
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.features import FeatureExtraction, FeatureWindow
from app.models.speech import SpeechSegment
from app.models.participants import ParticipantTrack

WINDOW_SIZE_MS = 5000

async def bucket_features_for_media_assets(db: AsyncSession, media_asset_ids: List[UUID], org_id: UUID) -> List[FeatureWindow]:
    if not media_asset_ids:
        return []
        
    result = await db.scalars(
        select(FeatureExtraction)
        .where(FeatureExtraction.media_asset_id.in_(media_asset_ids))
        .order_by(FeatureExtraction.timestamp_ms)
    )
    extractions = result.all()
    
    # Clean up existing windows for these media assets tracks
    # We find all tracks involved
    track_ids = {ext.participant_track_id for ext in extractions}
    if track_ids:
        await db.execute(delete(FeatureWindow).where(FeatureWindow.participant_track_id.in_(list(track_ids))))
    
    # Group by track_id and feature_type
    # windows[track_id][feature_type][window_idx] = List[FeatureExtraction]
    windows_map = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    
    for ext in extractions:
        window_idx = ext.timestamp_ms // WINDOW_SIZE_MS
        windows_map[ext.participant_track_id][ext.feature_type][window_idx].append(ext)
        
    new_windows = []
    # Create windows
    for track_id, f_type_map in windows_map.items():
        for f_type, window_map in f_type_map.items():
            for w_idx, exts in window_map.items():
                start_ms = w_idx * WINDOW_SIZE_MS
                end_ms = start_ms + WINDOW_SIZE_MS
                
                agg = {}
                keys = exts[0].values.keys()
                for k in keys:
                    valid_vals = [e.values[k] for e in exts if k in e.values and isinstance(e.values[k], (int, float))]
                    if valid_vals:
                        agg[k] = sum(valid_vals) / len(valid_vals)
                    else:
                        agg[k] = exts[-1].values.get(k)
                        
                window = FeatureWindow(
                    organization_id=org_id,
                    participant_track_id=track_id,
                    feature_type=f_type,
                    window_start_ms=start_ms,
                    window_end_ms=end_ms,
                    aggregation=agg,
                    source_extraction_count=len(exts)
                )
                db.add(window)
                new_windows.append(window)
                
    # Phase 9: Process SpeechSegments (if available) and map them into speaker_turn windows
    meeting_ids = set()
    for ext in extractions:
        meeting_ids.add(ext.media_asset_id) # well, wait, media_asset_id is not meeting_id
    
    # Let's get meeting_ids from media_assets
    if media_asset_ids:
        from app.models.media import MediaAsset
        assets = await db.scalars(select(MediaAsset).where(MediaAsset.id.in_(media_asset_ids)))
        meeting_ids = {a.meeting_id for a in assets.all()}
        
        segments = await db.scalars(
            select(SpeechSegment)
            .where(SpeechSegment.meeting_id.in_(meeting_ids))
            .where(SpeechSegment.participant_track_id.is_not(None))
        )
        
        for seg in segments.all():
            w_start = seg.start_ms // WINDOW_SIZE_MS
            w_end = seg.end_ms // WINDOW_SIZE_MS
            
            for w_idx in range(w_start, w_end + 1):
                start_ms = w_idx * WINDOW_SIZE_MS
                end_ms = start_ms + WINDOW_SIZE_MS
                
                # Check if we already created a legacy speaker_turn window for this track and window
                exists = False
                for w in new_windows:
                    if w.participant_track_id == seg.participant_track_id and w.feature_type == "speaker_turn" and w.window_start_ms == start_ms:
                        exists = True
                        break
                        
                if not exists:
                    window = FeatureWindow(
                        organization_id=org_id,
                        participant_track_id=seg.participant_track_id,
                        feature_type="speaker_turn",
                        window_start_ms=start_ms,
                        window_end_ms=end_ms,
                        aggregation={"text": seg.text},
                        source_extraction_count=1
                    )
                    db.add(window)
                    new_windows.append(window)

    await db.flush()
    return new_windows
