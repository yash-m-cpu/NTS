import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from datetime import datetime

from app.models.jobs import ProcessingJob
from app.models.participants import ParticipantTrack
from app.models.features import FeatureExtraction, FeatureWindow
from app.models.metrics import BehavioralMetric
from app.workers.feature_fusion_worker import handle_feature_fusion
from app.models.media import MediaAsset

@pytest.fixture
def mock_db_session():
    return AsyncMock()

@pytest.fixture
def anyio_backend():
    return "asyncio"

@pytest.mark.anyio
async def test_feature_fusion_worker(mock_db_session):
    org_id = uuid4()
    meeting_id = uuid4()
    job_id = uuid4()
    media_id = uuid4()
    track_id = uuid4()
    model_id = uuid4()

    job = ProcessingJob(
        id=job_id,
        organization_id=org_id,
        meeting_id=meeting_id,
        job_type="feature_fusion",
        status="running",
        model_version_id=model_id
    )
    
    media = MediaAsset(id=media_id, meeting_id=meeting_id, organization_id=org_id)
    
    track = ParticipantTrack(
        id=track_id, 
        organization_id=org_id, 
        media_asset_id=media_id, 
        processing_job_id=job_id,
        track_label="speaker1",
        first_seen_at_ms=1000,
        last_seen_at_ms=6000
    )

    ext1 = FeatureExtraction(
        organization_id=org_id, participant_track_id=track_id, media_asset_id=media_id, processing_job_id=job_id, model_version_id=model_id,
        extraction_pipeline_version="1", feature_type="gaze", timestamp_ms=1000, values={"yaw": 0.5, "pitch": 0.1}
    )
    ext2 = FeatureExtraction(
        organization_id=org_id, participant_track_id=track_id, media_asset_id=media_id, processing_job_id=job_id, model_version_id=model_id,
        extraction_pipeline_version="1", feature_type="gaze", timestamp_ms=6000, values={"yaw": 0.1, "pitch": 0.1}
    )
    ext3 = FeatureExtraction(
        organization_id=org_id, participant_track_id=track_id, media_asset_id=media_id, processing_job_id=job_id, model_version_id=model_id,
        extraction_pipeline_version="1", feature_type="speaker_turn", timestamp_ms=2000, values={"is_speaking": True}
    )
    
    # Mock db_session.scalar and db_session.scalars
    def mock_scalar(stmt):
        return job
        
    def mock_scalars(stmt):
        mock_result = MagicMock()
        # Very hacky way to figure out what is being queried
        stmt_str = str(stmt).lower()
        if "media_assets" in stmt_str:
            mock_result.all.return_value = [media]
        elif "feature_extractions" in stmt_str:
            mock_result.all.return_value = [ext1, ext2, ext3]
        return mock_result

    mock_db_session.scalar.side_effect = mock_scalar
    mock_db_session.scalars.side_effect = mock_scalars
    
    # Track additions
    added_objects = []
    mock_db_session.add = MagicMock(side_effect=lambda obj: added_objects.append(obj))
    
    await handle_feature_fusion(None, mock_db_session, str(job_id), {})
    
    # Check that windows and metrics were added
    windows = [obj for obj in added_objects if isinstance(obj, FeatureWindow)]
    metrics = [obj for obj in added_objects if isinstance(obj, BehavioralMetric)]
    
    assert len(windows) == 3
    # Windows:
    # 1. gaze, window 0
    # 2. gaze, window 1
    # 3. speaker_turn, window 0
    
    assert len(metrics) > 0
    metric_keys = {m.metric_key for m in metrics}
    assert "gaze_aversion_ratio" in metric_keys
    assert "speech_ratio" in metric_keys

    gaze_metric = next(m for m in metrics if m.metric_key == "gaze_aversion_ratio")
    assert gaze_metric.value == 0.5
