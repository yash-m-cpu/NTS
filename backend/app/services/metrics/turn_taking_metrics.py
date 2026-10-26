from .registry import registry

@registry.register("speech_ratio")
def compute_speech_ratio(windows):
    # This is rough because we only see speech windows, not total meeting duration.
    # But let's assume total meeting duration can be derived from the max window_end_ms of all features.
    if not windows: return None
    speech_windows = [w for w in windows if w.feature_type == "speaker_turn"]
    total_meeting_ms = max((w.window_end_ms for w in windows), default=0)
    
    if total_meeting_ms == 0: return None
    
    speaking_ms = sum(w.window_end_ms - w.window_start_ms for w in speech_windows)
    
    return {
        "value": speaking_ms / total_meeting_ms,
        "category": "temporal",
        "unit": "ratio"
    }

@registry.register("speaking_time_seconds")
def compute_speaking_time(windows):
    speech_windows = [w for w in windows if w.feature_type == "speaker_turn"]
    if not speech_windows: return None
    
    speaking_ms = sum(w.window_end_ms - w.window_start_ms for w in speech_windows)
    return {
        "value": speaking_ms / 1000.0,
        "category": "temporal",
        "unit": "seconds"
    }

@registry.register("turn_count")
def compute_turn_count(windows):
    speech_windows = [w for w in windows if w.feature_type == "speaker_turn"]
    if not speech_windows: return None
    
    # We can approximate turns by looking at disjoint windows.
    # Since windows are 5s, contiguous windows might be 1 turn.
    turns = 0
    sorted_ws = sorted(speech_windows, key=lambda w: w.window_start_ms)
    
    last_end = -10000
    for w in sorted_ws:
        if w.window_start_ms > last_end + 5000: # gap of more than window size
            turns += 1
        last_end = w.window_end_ms
        
    return {
        "value": turns,
        "category": "temporal",
        "unit": "count"
    }

@registry.register("avg_turn_duration_seconds")
def compute_avg_turn_duration(windows):
    tc = compute_turn_count(windows)
    st = compute_speaking_time(windows)
    if not tc or not st or tc["value"] == 0:
        return None
    return {
        "value": st["value"] / tc["value"],
        "category": "temporal",
        "unit": "seconds"
    }
