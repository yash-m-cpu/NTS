import pytest
from unittest.mock import patch, MagicMock
import json
import subprocess
from app.services.audio.ffmpeg_utils import probe_streams, compute_av_offset_ms, extract_audio, FfmpegError

@pytest.fixture
def mock_ffprobe_output():
    return {
        "streams": [
            {
                "codec_type": "video",
                "start_time": "0.000000"
            },
            {
                "codec_type": "audio",
                "start_time": "0.042000"
            }
        ],
        "format": {
            "duration": "100.0"
        }
    }

def test_probe_streams(mock_ffprobe_output):
    with patch('subprocess.run') as mock_run:
        mock_result = MagicMock()
        mock_result.stdout = json.dumps(mock_ffprobe_output)
        mock_run.return_value = mock_result
        
        info = probe_streams('dummy.mp4')
        assert 'streams' in info
        assert len(info['streams']) == 2

def test_compute_av_offset_ms(mock_ffprobe_output):
    offset = compute_av_offset_ms(mock_ffprobe_output)
    # audio 0.042 - video 0.0 = 0.042s -> 42ms
    assert offset == 42

def test_compute_av_offset_ms_negative():
    info = {
        "streams": [
            {"codec_type": "video", "start_time": "0.100000"},
            {"codec_type": "audio", "start_time": "0.050000"}
        ]
    }
    offset = compute_av_offset_ms(info)
    assert offset == -50

def test_extract_audio_success():
    with patch('subprocess.run') as mock_run:
        extract_audio('in.mp4', 'out.wav')
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert 'ffmpeg' in args
        assert '-vn' in args
        assert '-ac' in args
        assert '1' in args

def test_extract_audio_failure():
    with patch('subprocess.run') as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(1, 'ffmpeg', stderr='error')
        with pytest.raises(FfmpegError):
            extract_audio('in.mp4', 'out.wav')
