from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=False)

@app.get("/test-error")
def error_route():
    raise Exception("This is a test exception")

def test_unhandled_exception_format():
    response = client.get("/test-error")
    assert response.status_code == 500
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "INTERNAL_ERROR"
    # Ensure no traceback is leaked
    assert "This is a test exception" not in response.text
