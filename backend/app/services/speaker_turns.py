from typing import List, Any, Dict
from app.schemas.transcripts import SpeakerTurn, Word

def align_stt_with_diarization(segments: List[Any], diarization: List[Dict]) -> List[SpeakerTurn]:
    """
    Aligns whisper segments with diarization segments to produce SpeakerTurns.
    """
    turns = []
    
    for seg in segments:
        words = []
        if seg.words:
            for w in seg.words:
                words.append(Word(
                    word=w.word,
                    start=w.start,
                    end=w.end,
                    probability=w.probability
                ))
                
        # Find the dominant speaker for this segment based on overlap
        # O(N*M) but N and M are small per meeting
        best_speaker = "speaker_0"
        max_overlap = 0.0
        
        for d in diarization:
            overlap_start = max(seg.start, d["start"])
            overlap_end = min(seg.end, d["end"])
            overlap = max(0, overlap_end - overlap_start)
            if overlap > max_overlap:
                max_overlap = overlap
                best_speaker = d["speaker"]
                
        turn = SpeakerTurn(
            speaker=best_speaker,
            start=seg.start,
            end=seg.end,
            text=seg.text.strip(),
            words=words
        )
        turns.append(turn)
        
    return turns

def group_segments_into_turns(segments: List[Any]) -> List[SpeakerTurn]:
    # Legacy wrapper if diarization isn't available
    return align_stt_with_diarization(segments, [{"start": 0.0, "end": 99999.0, "speaker": "speaker_0"}])
