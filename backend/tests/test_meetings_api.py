from unittest.mock import AsyncMock, MagicMock
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
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock.execute.return_value = mock_result
    
    mock.scalar.return_value = 0 # for total
    
    return mock

def test_create_meeting(mock_db_session):
    app.dependency_overrides[get_db] = lambda: mock_db_session
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_current_org] = override_get_current_org
    
    with TestClient(app) as c:
        response = c.post(
            "/api/v1/meetings",
            json={"project_id": str(uuid4()), "title": "Test Meeting", "source_type": "upload"}
        )
        assert response.status_code == 201

def test_list_meetings(mock_db_session):
    app.dependency_overrides[get_db] = lambda: mock_db_session
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_current_org] = override_get_current_org
    
    with TestClient(app) as c:
        response = c.get("/api/v1/meetings")
        assert response.status_code == 200
