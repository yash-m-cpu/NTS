from faster_whisper.vad import get_vad_model, get_speech_timestamps, VadOptions
import logging

logger = logging.getLogger(__name__)

class Interval:
    def __init__(self, start_ms: int, end_ms: int, mean_prob: float = 1.0):
        self.start_ms = start_ms
        self.end_ms = end_ms
        self.mean_prob = mean_prob

    def __repr__(self):
        return f"Interval({self.start_ms}ms - {self.end_ms}ms, prob={self.mean_prob:.2f})"

def detect_speech(wav_path: str, threshold: float = 0.5, min_speech_ms: int = 250, min_silence_ms: int = 300, pad_ms: int = 100) -> list[Interval]:
    """
    Detect speech using Silero VAD (bundled with faster_whisper).
    wav_path should be a 16kHz WAV file.
    Returns a list of speech intervals.
    """
    logger.info(f"[VAD] Initializing VAD model for {wav_path}")
    model = get_vad_model()
    options = VadOptions(
        threshold=threshold,
        min_speech_duration_ms=min_speech_ms,
        min_silence_duration_ms=min_silence_ms,
        speech_pad_ms=pad_ms,
    )
    
    # get_speech_timestamps returns a list of dicts with 'start' and 'end' as samples (usually 16k rate)
    from faster_whisper.audio import decode_audio
    audio = decode_audio(wav_path)
    timestamps = get_speech_timestamps(audio, vad_options=options)
    
    intervals = []
    # Convert samples to ms (assuming 16000 Hz)
    sample_rate = 16000
    for ts in timestamps:
        start_ms = int(ts['start'] / sample_rate * 1000)
        end_ms = int(ts['end'] / sample_rate * 1000)
        intervals.append(Interval(start_ms=start_ms, end_ms=end_ms))
        
    logger.info(f"[VAD] Detected {len(intervals)} speech segments.")
    return intervals

def merge_close_intervals(intervals: list[Interval], gap_ms: int = 200) -> list[Interval]:
    if not intervals:
        return []
        
    merged = []
    current = intervals[0]
    
    for next_inv in intervals[1:]:
        if next_inv.start_ms - current.end_ms <= gap_ms:
            current.end_ms = max(current.end_ms, next_inv.end_ms)
        else:
            merged.append(current)
            current = next_inv
            
    merged.append(current)
    return merged
