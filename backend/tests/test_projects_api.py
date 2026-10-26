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
    
    # Setup for scalar returning None or mock objects
    mock.scalar.return_value = None
    
    # Setup for execute().scalars().all()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock.execute.return_value = mock_result
    
    return mock

def test_list_projects(mock_db_session):
    app.dependency_overrides[get_db] = lambda: mock_db_session
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_current_org] = override_get_current_org
    
    with TestClient(app) as c:
        response = c.get("/api/v1/projects")
        assert response.status_code == 200

def test_create_project(mock_db_session):
    app.dependency_overrides[get_db] = lambda: mock_db_session
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_current_org] = override_get_current_org
    
    # mock existing project check -> returns None
    mock_db_session.scalar.return_value = None
    
    with TestClient(app) as c:
        response = c.post(
            "/api/v1/projects",
            json={"name": "Test Project"}
        )
        assert response.status_code == 201, response.json()
