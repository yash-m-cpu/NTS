import logging
import math
import numpy as np
import parselmouth
from parselmouth.praat import call

logger = logging.getLogger(__name__)

def extract_f0(wav_path: str, hop_ms: int = 10) -> tuple:
    """
    Extracts pitch (F0) and intensity (RMS energy) from a wav file using Praat.
    Returns (times, f0, voiced, rms).
    """
    sound = parselmouth.Sound(wav_path)
    
    # Calculate Pitch
    # Time step is hop_ms / 1000
    time_step = hop_ms / 1000.0
    pitch = sound.to_pitch(time_step=time_step, pitch_floor=75, pitch_ceiling=600)
    
    # Calculate Intensity
    intensity = sound.to_intensity(minimum_pitch=75, time_step=time_step)
    
    pitch_values = pitch.selected_array['frequency']
    times = pitch.xs()
    
    # Intensity might have slightly different timing, interpolate to pitch times
    int_times = intensity.xs()
    int_values = intensity.values[0, :]
    
    # Interpolate intensity values to match pitch timestamps
    interp_intensity = np.interp(times, int_times, int_values)
    
    # Voiced is where frequency > 0
    voiced = pitch_values > 0
    f0 = np.where(voiced, pitch_values, 0.0)
    rms = interp_intensity
    
    return times, f0, voiced, rms

def pitch_distribution(f0_track: list) -> dict:
    """
    Calculate p10, p50, p90, and semitone range.
    f0_track should be a list of non-zero F0 values in Hz.
    """
    if not f0_track:
        return {}
        
    p10 = np.percentile(f0_track, 10)
    p50 = np.percentile(f0_track, 50)
    p90 = np.percentile(f0_track, 90)
    
    # Semitone range relative to median
    if p50 > 0 and p10 > 0 and p90 > 0:
        # 12 * log2(f1 / f2)
        st_range = 12.0 * math.log2(p90 / p10)
    else:
        st_range = 0.0
        
    return {
        "p10_hz": p10,
        "p50_hz": p50,
        "p90_hz": p90,
        "range_semitones": st_range
    }

def speaking_rate(words: list, vad_segments: list) -> dict:
    """
    Calculate words per minute (articulation and overall) and pause ratio.
    words: list of dicts {"start_ms": int, "end_ms": int}
    vad_segments: list of dicts {"start_ms": int, "end_ms": int}
    """
    if not words:
        return {}
        
    total_words = len(words)
    first_word_ms = words[0]["start_ms"]
    last_word_ms = words[-1]["end_ms"]
    
    overall_duration_min = (last_word_ms - first_word_ms) / 60000.0
    if overall_duration_min <= 0:
        return {}
        
    overall_wpm = total_words / overall_duration_min
    
    # Articulation WPM excludes pauses > 250ms
    # Sum up durations between words that are <= 250ms gap
    articulation_ms = 0
    pause_ms = 0
    
    for i in range(len(words) - 1):
        w1 = words[i]
        w2 = words[i+1]
        word_dur = max(0, w1["end_ms"] - w1["start_ms"])
        gap = max(0, w2["start_ms"] - w1["end_ms"])
        
        articulation_ms += word_dur
        if gap > 250:
            pause_ms += gap
        else:
            articulation_ms += gap
            
    # Add last word
    articulation_ms += max(0, words[-1]["end_ms"] - words[-1]["start_ms"])
    
    articulation_min = articulation_ms / 60000.0
    articulation_wpm = total_words / articulation_min if articulation_min > 0 else overall_wpm
    
    total_time_ms = articulation_ms + pause_ms
    pause_ratio = pause_ms / total_time_ms if total_time_ms > 0 else 0.0
    
    return {
        "overall_wpm": overall_wpm,
        "articulation_wpm": articulation_wpm,
        "pause_ratio": pause_ratio
    }
