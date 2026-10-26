import logging
from typing import Dict, List, Any
from uuid import UUID

logger = logging.getLogger(__name__)

def attribute_speakers(
    speech_segments: List[Any], 
    mouth_activity: Dict[UUID, List[Any]], 
    av_offset_ms: int
) -> List[dict]:
    """
    Given a list of SpeechSegment rows and a dictionary of track_id -> [MouthActivity rows],
    determine which participant was speaking for each segment.
    
    Returns a list of dicts: {"segment_id": UUID, "participant_track_id": UUID, "evidence": dict}
    """
    attributions = []
    
    for seg in speech_segments:
        # Audio bounds (in audio clock)
        audio_start = seg.start_ms
        audio_end = seg.end_ms
        
        # Convert to video clock using offset
        # video_t = audio_t + av_offset
        vid_start = audio_start + av_offset_ms
        vid_end = audio_end + av_offset_ms
        
        # Calculate mouth activity metrics for each track during this segment
        track_scores = {}
        for track_id, activities in mouth_activity.items():
            # Filter activities within the segment's video time range
            segment_acts = [a for a in activities if vid_start <= a.t_ms <= vid_end]
            if segment_acts:
                # 90th percentile mouth open ratio
                ratios = sorted([a.mar for a in segment_acts])
                idx_90 = int(len(ratios) * 0.9)
                score = ratios[idx_90]
            else:
                score = 0.0
            
            track_scores[track_id] = score
            
        # Determine the winner
        winner_id = None
        evidence = {"method": "mouth_activity", "scores": {str(k): float(v) for k, v in track_scores.items()}}
        
        if track_scores:
            # Find track with highest score
            best_track, best_score = max(track_scores.items(), key=lambda x: x[1])
            # Threshold for deciding if someone is actually talking (e.g., 0.1 ratio)
            if best_score >= 0.05:
                winner_id = best_track
                
        # If no winner from mouth activity, fallback to cluster prior if available
        # (In a full implementation, you'd map the diar_cluster_id to the most common mouth winner overall)
        if not winner_id and seg.diar_cluster_id:
            evidence["method"] = "cluster_fallback"
            evidence["cluster_id"] = seg.diar_cluster_id
            # We don't have a direct map to participant_track_id yet without a full clustering pass,
            # so we leave participant_track_id as None and let the fallback note the cluster.
            
        attributions.append({
            "segment_id": seg.id,
            "participant_track_id": winner_id,
            "evidence": evidence
        })
        
    return attributions
