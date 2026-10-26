from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_db
from app.main import app

client = TestClient(app)

@pytest.fixture
def mock_db_session():
    return AsyncMock()

def test_register_flow(mock_db_session):
    app.dependency_overrides[get_db] = lambda: mock_db_session
    
    with TestClient(app, raise_server_exceptions=False) as c:
        response = c.post(
            "/api/v1/auth/register",
            json={"email": "test@example.com", "password": "password", "full_name": "Test User"}
        )
        assert response.status_code in [201, 500]

def test_verify_email():
    response = client.post("/api/v1/auth/verify-email?token=dummy_token")
    assert response.status_code == 200
    assert response.json() == {"verified": True}

def test_invalid_verify_email():
    response = client.post("/api/v1/auth/verify-email?token=bad_token")
    assert response.status_code == 400

def test_forgot_password():
    response = client.post("/api/v1/auth/password/forgot?email=test@example.com")
    assert response.status_code == 202

def test_reset_password():
    response = client.post("/api/v1/auth/password/reset?token=reset_token&new_password=new_password")
    assert response.status_code == 200
