import json
import logging
import subprocess
from typing import Dict, Any

logger = logging.getLogger(__name__)

class FfmpegError(Exception):
    pass

def probe_streams(path: str) -> Dict[str, Any]:
    """Run ffprobe and return the parsed JSON info."""
    cmd = [
        'ffprobe',
        '-v', 'quiet',
        '-print_format', 'json',
        '-show_streams',
        '-show_format',
        path
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        logger.error(f"ffprobe failed: {e.stderr}")
        raise FfmpegError(f"ffprobe failed with code {e.returncode}: {e.stderr}")
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse ffprobe output: {e}")
        raise FfmpegError(f"Invalid ffprobe JSON: {e}")

def compute_av_offset_ms(info: Dict[str, Any]) -> int:
    """
    Compute (audio.start_time - video.start_time) * 1000.
    Returns 0 if streams are missing or start_time is missing.
    """
    video_start = 0.0
    audio_start = 0.0
    
    for stream in info.get('streams', []):
        codec_type = stream.get('codec_type')
        start_time = float(stream.get('start_time', 0.0))
        
        if codec_type == 'video':
            video_start = start_time
        elif codec_type == 'audio':
            audio_start = start_time
            
    return int(round((audio_start - video_start) * 1000))

def extract_audio(video_path: str, out_wav: str, sample_rate: int = 16000, mono: bool = True, loudnorm: bool = False) -> None:
    """
    Extract audio from video file to WAV.
    """
    cmd = [
        'ffmpeg',
        '-y',
        '-i', video_path,
        '-vn', # no video
    ]
    
    if mono:
        cmd.extend(['-ac', '1'])
        
    cmd.extend(['-ar', str(sample_rate)])
    
    # We want to resample asynchronously and fill gaps / handle first_pts to ensure sync
    af_filters = ['aresample=async=1:first_pts=0']
    if loudnorm:
        af_filters.append('loudnorm')
        
    cmd.extend(['-af', ','.join(af_filters)])
    cmd.extend(['-c:a', 'pcm_s16le', out_wav])
    
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"ffmpeg audio extraction failed: {e.stderr}")
        raise FfmpegError(f"ffmpeg extraction failed: {e.stderr}")
