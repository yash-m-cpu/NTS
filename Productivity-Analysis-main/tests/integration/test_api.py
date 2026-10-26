"""Integration tests for FastAPI REST API endpoints."""

from fastapi.testclient import TestClient
import pytest
from src.backend.main import app

client = TestClient(app)


def test_health_check_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "HEALTHY"
    assert "version" in data
    assert "database_backend" in data


def test_session_status_endpoint():
    response = client.get("/api/v1/sessions/status/CAM-01")
    assert response.status_code == 200
    data = response.json()
    assert data["camera_id"] == "CAM-01"
    assert "fps" in data
    assert "active_tracks_count" in data
    assert "observation_coverage_pct" in data


def test_live_telemetry_endpoint():
    response = client.get("/api/v1/telemetry/live/CAM-01")
    assert response.status_code == 200
    data = response.json()
    assert data["camera_id"] == "CAM-01"
    assert "active_tracks" in data
    assert "zones_occupancy" in data
    assert isinstance(data["active_tracks"], list)


def test_zone_crud_lifecycle():
    # 1. Create zone
    zone_payload = {
        "zone_id": "TEST-ZONE-99",
        "camera_id": "CAM-01",
        "name": "Integration Test Pod",
        "zone_type": "WORKSTATION",
        "capacity": 2,
        "polygon_normalized": [
            [0.10, 0.10],
            [0.35, 0.10],
            [0.35, 0.40],
            [0.10, 0.40]
        ]
    }
    create_resp = client.post("/api/v1/zones", json=zone_payload)
    assert create_resp.status_code == 201
    created_data = create_resp.json()
    assert created_data["zone_id"] == "TEST-ZONE-99"

    # 2. List zones and verify presence
    list_resp = client.get("/api/v1/zones?camera_id=CAM-01")
    assert list_resp.status_code == 200
    zones = list_resp.json()
    assert any(z["zone_id"] == "TEST-ZONE-99" for z in zones)

    # 3. Delete zone
    del_resp = client.delete("/api/v1/zones/TEST-ZONE-99?camera_id=CAM-01")
    assert del_resp.status_code == 200
    assert del_resp.json()["status"] == "DELETED"

    # 4. Verify 404 on deleting non-existent zone
    del_again = client.delete("/api/v1/zones/TEST-ZONE-99?camera_id=CAM-01")
    assert del_again.status_code == 404


def test_scorecards_endpoint():
    response = client.get("/api/v1/analytics/scorecards?camera_id=CAM-01&department=ENG")
    assert response.status_code == 200
    data = response.json()
    assert "scorecard_a" in data
    assert "scorecard_b" in data
    assert "scorecard_c" in data
    assert "scorecard_d" in data
    assert data["scorecard_a"]["scorecard_name"] == "Workflow Efficiency"
    assert "workflow_efficiency_score" in data["scorecard_a"]


def test_recommendations_endpoint():
    response = client.get("/api/v1/analytics/recommendations?camera_id=CAM-01")
    assert response.status_code == 200
    recs = response.json()
    assert isinstance(recs, list)
    if len(recs) > 0:
        assert "hypothesis" in recs[0]
        assert "recommended_experiment" in recs[0]


def test_operational_outcomes_ingestion_webhook():
    outcome_payload = {
        "report_date": "2026-10-15",
        "department_code": "QA-TEST",
        "actual_completed_units": 50,
        "target_planned_units": 50,
        "quality_accepted_units": 48,
        "quality_assessed_units": 50,
        "on_time_units": 49,
        "total_deadline_units": 50,
        "rework_units": 2,
        "source_system": "TEST_CLIENT_SUITE"
    }
    response = client.post("/api/v1/ingest/operational-outcomes", json=outcome_payload)
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "ACCEPTED"
    assert data["department_code"] == "QA-TEST"
    assert data["output_effectiveness_score"] > 90.0


def test_audit_logs_endpoint():
    response = client.get("/api/v1/system/audit-logs?limit=10")
    assert response.status_code == 200
    logs = response.json()
    assert isinstance(logs, list)
    assert len(logs) > 0
    assert "action_type" in logs[0]


def test_video_upload_endpoint():
    dummy_video_bytes = b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00isommp42"
    files = {"file": ("integration_test_clip.mp4", dummy_video_bytes, "video/mp4")}
    response = client.post("/api/v1/videos/upload?camera_id=CAM-01", files=files)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "UPLOADED"
    assert data["filename"] == "integration_test_clip.mp4"
    assert data["camera_id"] == "CAM-01"

