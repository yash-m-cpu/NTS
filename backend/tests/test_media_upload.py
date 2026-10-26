from unittest.mock import AsyncMock, patch, MagicMock
import pytest
from fastapi.testclient import TestClient
from uuid import uuid4

from app.api.deps import get_db, get_current_user, get_current_org
from app.main import app

def override_get_current_user():
    class MockUser:
        id = uuid4()
    return MockUser()

def override_get_current_org():
    return str(uuid4())

@pytest.fixture
def mock_db_session():
    mock = AsyncMock()
    
    class MockMeeting:
        id = uuid4()
        
    class MockAsset:
        id = uuid4()
        storage_key = "test_key"
        content_type = "video/mp4"
        upload_status = "pending"
        meeting_id = uuid4()
        
    # We can just return MockMeeting on first call and MockAsset on others if needed, 
    # but the simplest is just testing the endpoint with patch
    return mock

@patch("app.api.v1.media.generate_presigned_upload_url", return_value=("http://presigned", "test_key"))
def test_initiate_upload(mock_presigned, mock_db_session):
    app.dependency_overrides[get_db] = lambda: mock_db_session
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_current_org] = override_get_current_org
    
    class MockMeeting:
        id = uuid4()
    mock_db_session.scalar.return_value = MockMeeting()
    
    with TestClient(app) as c:
        response = c.post(
            "/api/v1/media/uploads/initiate",
            json={
                "meeting_id": str(uuid4()),
                "asset_type": "video",
                "content_type": "video/mp4",
                "size_bytes": 1024
            }
        )
        assert response.status_code == 201
        data = response.json()["data"]
        assert "upload_url" in data
        assert data["upload_url"] == "http://presigned"

@patch("app.api.v1.media.verify_upload", return_value="verified")
def test_complete_upload(mock_verify, mock_db_session):
    app.dependency_overrides[get_db] = lambda: mock_db_session
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_current_org] = override_get_current_org
    
    class MockAsset:
        id = uuid4()
        storage_key = "test_key"
        content_type = "video/mp4"
        upload_status = "pending"
        meeting_id = uuid4()
    mock_db_session.scalar.return_value = MockAsset()
    
    with TestClient(app) as c:
        response = c.post(f"/api/v1/media/uploads/{uuid4()}/complete")
        assert response.status_code == 200
        assert response.json()["data"]["status"] == "verified"
