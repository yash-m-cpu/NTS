# React API Contract & Specification
## CCTV Workplace Productivity & Workflow Intelligence System (WBPIS)

**Date:** October 18, 2026  
**Backend:** FastAPI (Python 3.11) on `http://127.0.0.1:8000`  
**Frontend Client:** React + TypeScript via Axios / Fetch  

---

## 1. System Health & Diagnostics

### `GET /health`
- **Method:** `GET`
- **Route:** `/health`
- **Description:** Returns the operational health status and configuration metadata of the backend server.
- **Request Parameters:** None
- **Response Schema:**
  ```json
  {
    "status": "HEALTHY",
    "timestamp": "2026-10-18T00:00:00.000000+00:00",
    "version": "1.0.0",
    "detector_initialized": true,
    "database_backend": "SQLite"
  }
  ```
- **Status Codes:** `200 OK`
- **Authentication:** None (Public health check)
- **Origin:** Existed previously.

---

### `GET /api/v1/system/audit-logs`
- **Method:** `GET`
- **Route:** `/api/v1/system/audit-logs`
- **Query Parameters:** `limit: int` (default: 50)
- **Description:** Fetches immutable STRIDE security and privacy audit log entries.
- **Response Schema:**
  ```json
  [
    {
      "log_id": "string",
      "timestamp": "ISO-8601 string",
      "user_id": "string",
      "user_role": "string",
      "action_type": "string",
      "resource_id": "string",
      "client_ip": "string",
      "status_code": 200,
      "details": {}
    }
  ]
  ```
- **Status Codes:** `200 OK`
- **Authentication:** Role-Based Access (DPO / Auditor / Admin)
- **Origin:** Existed previously.

---

## 2. Perception Pipeline & Live Streaming

### `POST /api/v1/sessions/start`
- **Method:** `POST`
- **Route:** `/api/v1/sessions/start?camera_id={camera_id}`
- **Query Parameters:** `camera_id: str` (default: "CAM-01")
- **Description:** Activates the video perception pipeline ingest worker and starts inference.
- **Response Schema:**
  ```json
  {
    "status": "STREAMING",
    "camera_id": "CAM-01",
    "started_at": "ISO-8601 string",
    "stream_url": "/api/v1/stream/live/CAM-01"
  }
  ```
- **Status Codes:** `200 OK`
- **Origin:** Existed previously.

---

### `POST /api/v1/sessions/stop`
- **Method:** `POST`
- **Route:** `/api/v1/sessions/stop?camera_id={camera_id}`
- **Query Parameters:** `camera_id: str` (default: "CAM-01")
- **Description:** Stops perception worker and releases hardware capture resources.
- **Response Schema:**
  ```json
  {
    "status": "STOPPED",
    "camera_id": "CAM-01",
    "stopped_at": "ISO-8601 string"
  }
  ```
- **Status Codes:** `200 OK`
- **Origin:** Existed previously.

---

### `GET /api/v1/sessions/status/{camera_id}`
- **Method:** `GET`
- **Route:** `/api/v1/sessions/status/{camera_id}`
- **Description:** Returns real-time ingestion health, inference FPS, dropped frame count, and track count.
- **Response Schema:**
  ```json
  {
    "camera_id": "CAM-01",
    "is_alive": true,
    "fps": 15.2,
    "active_tracks_count": 3,
    "total_frames_processed": 1420,
    "dropped_frames_count": 0,
    "observation_coverage_pct": 100.0
  }
  ```
- **Status Codes:** `200 OK`
- **Origin:** Existed previously.

---

### `GET /api/v1/stream/live/{camera_id}`
- **Method:** `GET`
- **Route:** `/api/v1/stream/live/{camera_id}`
- **Description:** Streams live multipart MJPEG frames (`multipart/x-mixed-replace; boundary=frame`) directly to the HTML5 video/image container.
- **Status Codes:** `200 OK`
- **Origin:** Existed previously.

---

### `POST /api/v1/videos/upload`
- **Method:** `POST`
- **Route:** `/api/v1/videos/upload?camera_id={camera_id}`
- **Content-Type:** `multipart/form-data`
- **Request Body:** Form-data with file under key `"file"`
- **Response Schema:**
  ```json
  {
    "status": "UPLOADED",
    "filename": "office.mp4",
    "saved_path": "C:\\path\\to\\uploads\\...",
    "camera_id": "CAM-01",
    "is_streaming": true,
    "size_bytes": 10485760
  }
  ```
- **Status Codes:** `201 Created`
- **Origin:** Existed previously.

---

### `GET /api/v1/telemetry/live/{camera_id}`
- **Method:** `GET`
- **Route:** `/api/v1/telemetry/live/{camera_id}`
- **Description:** Returns the latest telemetry snapshot of active tracks, bounding boxes, dwell durations, activity classifications, and zone occupancies.
- **Response Schema:**
  ```json
  {
    "timestamp": "ISO-8601 string",
    "camera_id": "CAM-01",
    "fps": 15.0,
    "active_tracks": [
      {
        "track_id": "TRK-0101",
        "zone_id": "ZONE-DESK-01",
        "activity": "ACT-01: Seated at Workstation",
        "confidence": 0.92,
        "velocity": 0.005,
        "dwell_duration_seconds": 320.0,
        "transitions_count": 2,
        "interruption_events": 1,
        "waiting_seconds": 15.0,
        "activity_breakdown": {
          "ACT-01": 70.0,
          "ACT-02": 15.0,
          "ACT-03": 10.0,
          "ACT-05": 3.0,
          "ACT-07": 2.0
        }
      }
    ],
    "zones_occupancy": {
      "ZONE-DESK-01": "OCCUPIED",
      "ZONE-DESK-02": "VACANT"
    },
    "observation_coverage_pct": 100.0
  }
  ```
- **Status Codes:** `200 OK`
- **Origin:** Existed previously.

---

## 3. Spatial Zone Management

### `GET /api/v1/zones`
- **Method:** `GET`
- **Route:** `/api/v1/zones`
- **Query Parameters:** `camera_id: Optional[str]`
- **Response Schema:**
  ```json
  [
    {
      "zone_id": "ZONE-DESK-01",
      "camera_id": "CAM-01",
      "name": "Desk Pod 1",
      "zone_type": "WORKSTATION",
      "capacity": 2,
      "polygon_coords": [[0.1, 0.2], [0.4, 0.2], [0.4, 0.6], [0.1, 0.6]],
      "created_at": "ISO-8601 string"
    }
  ]
  ```
- **Status Codes:** `200 OK`
- **Origin:** Existed previously.

---

### `POST /api/v1/zones`
- **Method:** `POST`
- **Route:** `/api/v1/zones`
- **Request Schema:**
  ```json
  {
    "zone_id": "ZONE-DESK-03",
    "camera_id": "CAM-01",
    "name": "Desk Pod 3",
    "zone_type": "WORKSTATION",
    "capacity": 2,
    "polygon_coords": [[0.1, 0.2], [0.4, 0.2], [0.4, 0.6], [0.1, 0.6]]
  }
  ```
- **Status Codes:** `201 Created`, `422 Unprocessable Entity`
- **Origin:** Existed previously.

---

### `DELETE /api/v1/zones/{zone_id}`
- **Method:** `DELETE`
- **Route:** `/api/v1/zones/{zone_id}?camera_id={camera_id}`
- **Status Codes:** `200 OK`, `404 Not Found`
- **Origin:** Existed previously.

---

## 4. Scorecards & Recommendations

### `GET /api/v1/analytics/scorecards`
- **Method:** `GET`
- **Route:** `/api/v1/analytics/scorecards?camera_id={camera_id}&department={department}`
- **Response Schema:**
  ```json
  {
    "scorecard_a": {
      "scorecard_name": "Scorecard A: Workflow Efficiency",
      "composite_score": 76.5,
      "confidence": "HIGH",
      "metrics": {
        "focus_interruption_freq": 1.0,
        "congestion_ratio_pct": 0.8,
        "waiting_ratio_pct": 1.7,
        "zone_transition_frequency": 4.0
      }
    },
    "scorecard_b": {
      "scorecard_name": "Scorecard B: Activity Distribution",
      "composite_score": 72.4,
      "confidence": "HIGH",
      "metrics": {
        "activity_shares": {
          "ACT-01": 58.0,
          "ACT-02": 16.0,
          "ACT-03": 12.0,
          "ACT-04": 7.0,
          "ACT-05": 4.0,
          "ACT-06": 1.5,
          "ACT-07": 1.5
        }
      }
    },
    "scorecard_c": {
      "scorecard_name": "Scorecard C: Occupancy & Presence",
      "composite_score": 78.2,
      "confidence": "HIGH",
      "metrics": {
        "workstation_occupancy_rate_pct": 75.0,
        "away_time_ratio_pct": 25.0
      }
    },
    "scorecard_d": {
      "scorecard_name": "Scorecard D: Output Effectiveness",
      "composite_score": 88.5,
      "status": "AVAILABLE",
      "source_system": "JIRA_SPRINT_WEBHOOK",
      "metrics": {
        "throughput_rate_pct": 105.0,
        "quality_rate_pct": 97.1,
        "timeliness_rate_pct": 93.3,
        "rework_rate_pct": 2.9
      }
    }
  }
  ```
- **Status Codes:** `200 OK`
- **Origin:** Existed previously.

---

### `GET /api/v1/analytics/recommendations`
- **Method:** `GET`
- **Route:** `/api/v1/analytics/recommendations?camera_id={camera_id}`
- **Response Schema:**
  ```json
  [
    {
      "recommendation_id": "REC-01",
      "rule_code": "REC-01",
      "hypothesis": "string",
      "observed_metric_evidence": "string",
      "recommended_action": "string",
      "target_metric": "string",
      "expected_impact_pct": 15.0,
      "mitigation_notes": "string"
    }
  ]
  ```
- **Status Codes:** `200 OK`
- **Origin:** Existed previously.

---

### `POST /api/v1/ingest/operational-outcomes`
- **Method:** `POST`
- **Route:** `/api/v1/ingest/operational-outcomes`
- **Request Schema:**
  ```json
  {
    "report_date": "2026-10-18",
    "department_code": "ENG",
    "actual_completed_units": 105,
    "target_planned_units": 100,
    "quality_accepted_units": 102,
    "quality_assessed_units": 105,
    "on_time_units": 98,
    "total_deadline_units": 105,
    "rework_units": 3,
    "source_system": "JIRA_SPRINT_WEBHOOK"
  }
  ```
- **Status Codes:** `202 Accepted`
- **Origin:** Existed previously.

---

## 5. Video Export & Redaction

### `POST /api/v1/export/video`
- **Method:** `POST`
- **Route:** `/api/v1/export/video?camera_id={camera_id}&max_frames={max_frames}`
- **Response Schema:**
  ```json
  {
    "job_id": "EXP-1792056000",
    "status": "QUEUED",
    "output_filename": "EXP-1792056000_CAM-01.mp4"
  }
  ```
- **Status Codes:** `202 Accepted`
- **Origin:** Existed previously.

---

### `GET /api/v1/export/status/{job_id}`
- **Method:** `GET`
- **Route:** `/api/v1/export/status/{job_id}`
- **Response Schema:**
  ```json
  {
    "job_id": "EXP-1792056000",
    "status": "READY",
    "progress_pct": 100.0,
    "frames_rendered": 150,
    "total_frames": 150,
    "error_message": null,
    "download_url": "/exports/EXP-1792056000_CAM-01.mp4"
  }
  ```
- **Status Codes:** `200 OK`, `404 Not Found`
- **Origin:** Existed previously.
