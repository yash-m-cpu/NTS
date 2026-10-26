import re

with open('c:/PJT/backend/app/api/v1/meetings.py', 'r', encoding='utf-8') as f:
    c = f.read()

t = """@router.get("/{id}/speaking-summary", response_model=dict)
async def get_speaking_summary(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_id: str = Depends(get_current_org)
):
    from app.models.participants import ParticipantTrack
    from app.models.media import MediaAsset
    from app.models.metrics import BehavioralMetric
    from app.models.features import FeatureExtraction
    
    # Get all tracks for this meeting
    tracks_result = await db.execute(
        select(ParticipantTrack)
        .join(MediaAsset, MediaAsset.id == ParticipantTrack.media_asset_id)
        .where(MediaAsset.meeting_id == id)
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
        metric_dict = {m.metric_key: m.value for m in metrics}
        
        # Get turns
        features_result = await db.execute(
            select(FeatureExtraction)
            .where(
                FeatureExtraction.participant_track_id == track.id,
                FeatureExtraction.feature_type == 'speaker_turn'
            )
            .order_by(FeatureExtraction.timestamp_ms)
        )
        features = features_result.scalars().all()
        
        turns = []
        for f in features:
            val = f.values or {}
            turns.append({
                "start": val.get("start", f.timestamp_ms / 1000.0),
                "end": val.get("end", f.timestamp_ms / 1000.0 + 5),
                "text": val.get("text", "")
            })"""

r = """@router.get("/{id}/speaking-summary", response_model=dict)
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
    
    # Get all tracks for this meeting
    tracks_result = await db.execute(
        select(ParticipantTrack)
        .join(MediaAsset, MediaAsset.id == ParticipantTrack.media_asset_id)
        .where(MediaAsset.meeting_id == id)
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
        metric_dict = {m.metric_key: m.value for m in metrics}
        
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
        for f in features:
            turns.append({
                "start": (f.start_ms / 1000.0) if f.start_ms is not None else 0.0,
                "end": (f.end_ms / 1000.0) if f.end_ms is not None else 0.0,
                "text": f.text or ""
            })"""

if t in c:
    with open('c:/PJT/backend/app/api/v1/meetings.py', 'w', encoding='utf-8') as f:
        f.write(c.replace(t, r))
    print('done')
else:
    print('not found')
