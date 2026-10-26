import pytest
from uuid import uuid4
import asyncio
from unittest.mock import AsyncMock

from app.models.jobs import ProcessingJob
from app.models.media import MediaAsset
from app.workers.stt_worker import handle_stt_transcription
from app.models.participants import ParticipantTrack
from app.models.features import FeatureExtraction

class MockWord:
    def __init__(self, word, start, end, probability):
        self.word = word
        self.start = start
        self.end = end
        self.probability = probability

class MockSegment:
    def __init__(self, start, end, text, words):
        self.start = start
        self.end = end
        self.text = text
        self.words = words
        self.avg_logprob = -0.1
        self.no_speech_prob = 0.05
        self.tokens = []

@pytest.fixture
def mock_s3_client(monkeypatch):
    class MockS3Client:
        async def download_file(self, bucket, key, path):
            with open(path, "w") as f:
                f.write("mock audio data")
            return
            
        async def __aenter__(self):
            return self
            
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass
            
    def mock_get_s3_client():
        return MockS3Client()
        
    monkeypatch.setattr("app.workers.stt_worker.get_s3_client", mock_get_s3_client)

@pytest.fixture
def mock_stt_service(monkeypatch):
    class MockSTTService:
        async def transcribe(self, audio_path):
            return [
                MockSegment(
                    start=0.0,
                    end=1.0,
                    text="hello world",
                    words=[
                        MockWord("hello", 0.0, 0.5, 0.9),
                        MockWord("world", 0.5, 1.0, 0.9)
                    ]
                )
            ]
            
    monkeypatch.setattr("app.workers.stt_worker.stt_service", MockSTTService())

@pytest.mark.asyncio
async def test_stt_worker(mock_s3_client, mock_stt_service):
    org_id = uuid4()
    asset_id = uuid4()
    job_id = uuid4()
    
    mock_db = AsyncMock()
    
    mock_job = ProcessingJob(
        id=job_id,
        organization_id=org_id,
        media_asset_id=asset_id,
        job_type="stt_transcription",
        status="pending"
    )
    
    mock_asset = MediaAsset(
        id=asset_id,
        organization_id=org_id,
        storage_bucket="test-bucket",
        storage_key="test/test.mp4"
    )
    
    async def scalar_side_effect(stmt, *args, **kwargs):
        s = str(stmt).lower()
        if 'processingjob' in s or 'processing_jobs' in s:
            return mock_job
        if 'mediaasset' in s or 'media_assets' in s:
            return mock_asset
        return None
        
    mock_db.scalar.side_effect = scalar_side_effect
    
    from unittest.mock import MagicMock
    mock_execute_result = MagicMock()
    mock_execute_result.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_execute_result
    
    result = await handle_stt_transcription({}, mock_db, str(job_id), {})
    
    assert result["speech_segments"] == 1
    assert result["speech_words"] == 2
    assert result["legacy_turns_extracted"] == 1
    
    # Verify add_all was called
    assert mock_db.add_all.called
