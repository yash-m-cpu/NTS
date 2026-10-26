from fastapi import Depends
from fastapi.testclient import TestClient

from app.core.rbac import require_role
from app.main import app


# Create a test route in the app just for testing rbac
@app.get("/api/v1/test-rbac-admin", dependencies=[Depends(require_role("ADMIN"))])
def dummy_admin_route():
    return {"status": "ok"}

@app.get("/api/v1/test-rbac-manager", dependencies=[Depends(require_role("MANAGER"))])
def dummy_manager_route():
    return {"status": "ok"}

client = TestClient(app)

def test_rbac_no_token():
    response = client.get("/api/v1/test-rbac-admin")
    assert response.status_code == 401
