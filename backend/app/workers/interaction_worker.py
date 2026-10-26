from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.jobs import ProcessingJob
from app.models.features import FeatureExtraction
from app.models.participants import ParticipantTrack
from app.models.media import MediaAsset
from app.models.speech import SpeechSegment
from app.models.interactions import InteractionGraph
import logging
logger = logging.getLogger(__name__)

async def handle_interaction_analysis(ctx, db: AsyncSession, job_id: str, kwargs: dict):
    job = await db.scalar(select(ProcessingJob).where(ProcessingJob.id == UUID(job_id)))
    if not job or not job.meeting_id:
        raise ValueError("Job not found")
    
    meeting_id = job.meeting_id
    
    # Load all attributed speech segments for the meeting, ordered by start time
    result = await db.execute(
        select(SpeechSegment, ParticipantTrack)
        .join(ParticipantTrack, ParticipantTrack.id == SpeechSegment.participant_track_id)
        .where(
            SpeechSegment.meeting_id == meeting_id,
            SpeechSegment.participant_track_id.isnot(None)
        )
        .order_by(SpeechSegment.start_ms)
    )
    rows = result.all()
    
    if not rows:
        logger.info("No attributed speech segments found for meeting %s, skipping interaction analysis", meeting_id)
        return {"edges": 0, "nodes": 0}
    
    # Build a list of turns with track info, sorted by start time
    turns = []
    for seg, track in rows:
        turns.append({
            'track_id': str(track.id),
            'track_label': track.track_label,
            'start': (seg.start_ms / 1000.0) if seg.start_ms is not None else 0.0,
            'end': (seg.end_ms / 1000.0) if seg.end_ms is not None else 0.0,
            'text': seg.text or ''
        })
    
    turns.sort(key=lambda x: x['start'])
    
    # Get all unique tracks
    tracks_map = {}
    for t in turns:
        if t['track_id'] not in tracks_map:
            tracks_map[t['track_id']] = {
                'id': t['track_label'],
                'track_id': t['track_id'],
                'speaking_time': 0.0
            }
        tracks_map[t['track_id']]['speaking_time'] += max(0, t['end'] - t['start'])
    
    # Compute pairwise interactions from consecutive turn changes
    from collections import defaultdict
    pair_exchanges = defaultdict(int)
    pair_quick_responses = defaultdict(int)
    
    for i in range(1, len(turns)):
        prev = turns[i - 1]
        curr = turns[i]
        if prev['track_id'] != curr['track_id']:
            key = (prev['track_label'], curr['track_label'])
            pair_exchanges[key] += 1
            gap = curr['start'] - prev['end']
            if gap <= 1.0:  # quick response if gap < 1 second
                pair_quick_responses[key] += 1
    
    edges = []
    for (from_label, to_label), count in pair_exchanges.items():
        edges.append({
            'from': from_label,
            'to': to_label,
            'exchanges': count,
            'quick_responses': pair_quick_responses.get((from_label, to_label), 0)
        })
    
    graph_data = {
        'nodes': list(tracks_map.values()),
        'edges': edges
    }
    
    # Upsert the graph
    existing = await db.scalar(
        select(InteractionGraph).where(InteractionGraph.meeting_id == meeting_id)
    )
    if existing:
        existing.graph_data = graph_data
        existing.computed_at = datetime.now(timezone.utc)
        existing.processing_job_id = job.id
    else:
        db.add(InteractionGraph(
            organization_id=job.organization_id,
            meeting_id=meeting_id,
            processing_job_id=job.id,
            graph_data=graph_data,
            computed_at=datetime.now(timezone.utc)
        ))
    
    await db.commit()
    return {'nodes': len(tracks_map), 'edges': len(edges)}
