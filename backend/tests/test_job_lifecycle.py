from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_current_org, get_current_user, get_db
from app.models.jobs import ProcessingJob, ProcessingJobEvent


def override_get_current_user():
    class MockUser:
        id = uuid4()
    return MockUser()

def override_get_current_org():
    return str(uuid4())

@pytest.fixture
def mock_db_session():
    mock = AsyncMock()
    return mock

def test_job_lifecycle(mock_db_session, monkeypatch):
    import app.main
    app.main.app.dependency_overrides[get_db] = lambda: mock_db_session
    app.main.app.dependency_overrides[get_current_user] = override_get_current_user
    app.main.app.dependency_overrides[get_current_org] = override_get_current_org
    
    from datetime import datetime
    mock_job = ProcessingJob(
        id=uuid4(),
        organization_id=uuid4(),
        meeting_id=uuid4(),
        job_type="analysis",
        status="queued",
        priority=0,
        queue_name="default",
        attempt_count=0,
        max_attempts=3,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )    
    async def mock_enqueue_job(*args, **kwargs):
        return mock_job
        
    import app.services.job_service
    monkeypatch.setattr(app.services.job_service, "enqueue_job", mock_enqueue_job)
    
    with TestClient(app.main.app) as c:
        # 1. Mock creating a meeting
        c.post(
            "/api/v1/meetings",
            json={"project_id": str(uuid4()), "title": "Test", "source_type": "upload"}
        )
        
        # We need mock_db_session to return a meeting object when get_meeting checks if it exists
        mock_db_session.scalar.return_value = MagicMock(id=uuid4())
        
        # 2. Request analysis
        response = c.post(
            f"/api/v1/meetings/{uuid4()}/analysis",
            json={"pipeline": "full"}
        )
        assert response.status_code == 202
        assert response.json()["data"]["job_id"] == str(mock_job.id)
        
        # 3. Check job status
        # Update mock_db_session scalar to return mock_job for job
        mock_db_session.scalar.return_value = mock_job
        
        response = c.get(
            f"/api/v1/jobs/{mock_job.id}"
        )
        assert response.status_code == 200
        assert response.json()["data"]["status"] == "queued"
        
        # 4. Check events
        mock_event = ProcessingJobEvent(
            id=uuid4(),
            event_type="job.queued",
            processing_job_id=mock_job.id,
            payload={},
            occurred_at=datetime.now()
        )
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_event]
        mock_db_session.execute.return_value = mock_result
        
        response = c.get(
            f"/api/v1/jobs/{mock_job.id}/events"
        )
        assert response.status_code == 200
        assert response.json()["data"][0]["event_type"] == "job.queued"
