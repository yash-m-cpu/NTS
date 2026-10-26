# Implementation Execution Audit

**Document Path**: `docs/implementation/EXECUTION_AUDIT.md`  
**Date**: October 15, 2026  
**System**: CCTV Workplace Productivity and Workflow Intelligence System (WBPIS)  
**Execution Context**: Transition from Technical Specification to Implementation

---

## 1. Executive Summary

This audit evaluates the existing codebase assets in `audit_extracted/OpenCV-Based-Real-time-Employee-Tracking-System-main/` (Codebase A) and `C:\Users\DELL\Desktop\video/` (Codebase B) against the 19 implementation specifications in `docs/implementation/`.

It classifies every relevant component, establishes the primary application architecture, details dependency compatibility, and formulates the modular implementation blueprint.

---

## 2. Component Classification Matrix

Each component is classified into one of the five mandatory evaluation tiers:
1. **Reusable without changes**
2. **Reusable after modification**
3. **Replaceable**
4. **Unnecessary for the project**
5. **Missing and requiring implementation**

| Component / Artifact | Codebase Origin | Classification | Technical Rationale & Audit Findings |
| :--- | :--- | :--- | :--- |
| **Darknet YOLOv4-tiny Weights & Cfg** | Codebase A (`yolo_model/`) | **Reusable without changes** | The pre-trained weights (`yolov4-tiny.weights`, 24 MB) and config (`yolov4-tiny.cfg`) can be loaded directly via OpenCV DNN (`cv2.dnn.readNetFromDarknet`) for lightweight person detection without external model downloads. |
| **Sample Footage** | Codebase A (`uploads/`) | **Reusable without changes** | `1755331753_...mp4` (39 MB) provides an authentic workplace video file for offline testing, calibration, and regression validation. |
| **Apache ECharts Visualizations** | Codebase B (`video/horiz.py`, `choriwala_code.py`) | **Reusable after modification** | The ECharts JSON options for horizontal bar charts, radar charts, and gauges are directly adaptable into the Streamlit dashboard views. Must remove affective/emotion labels and replace with objective spatial metrics. |
| **Video Decoding & Frame Capture** | Codebase A (`employee_tracking_fixed.py`) | **Reusable after modification** | OpenCV `VideoCapture` loop is reusable once the live seek bug (`BUG-03`) is removed, `protocols=tcp` is enforced, and thread-safe mailbox buffering is integrated. |
| **Polygon / ROI Configuration** | Codebase A (`app.py`, `employee_tracking_fixed.py`) | **Replaceable** | Legacy system used hardcoded coordinate tuples and was broken by integer truncation (`BUG-02`). Replaced by a normalized GeoJSON polygon engine and interactive UI canvas. |
| **Flask Monolithic Web Server** | Codebase A (`app.py`) | **Replaceable** | Monolithic Flask application combines capture, inference, and HTTP polling into a single thread pool, causing browser freezes (`BUG-01`). Replaced by an asynchronous FastAPI backend service. |
| **Affective / Emotion ResNet Models** | Codebase B (`emo.py`, `ocean.py`, `choriwala_code.py`) | **Unnecessary for the project** | PyTorch-based facial emotion, gaze deception, and personality profiling are statistically unvalidated and violate the Anti-Surveillance Covenant (Phase 00 & 01). Excluded from the productivity pipeline. |
| **MediaPipe Single-Person FaceMesh** | Codebase B (`main.py`, `comp.py`) | **Unnecessary for the project** | Single-person FaceMesh snaps erratically when multiple employees appear in frame and provides no multi-person tracking handles. Excluded. |
| **Plaintext Credential Logger** | Codebase A (`app.py`) | **Unnecessary for the project** | `employee_log.txt` logged plaintext camera passwords (`SEC-01`). Permanently eliminated and replaced with sanitized structured logging. |
| **Multi-Person Object Tracking (MOT)** | Neither | **Missing & Requiring Implementation** | Neither codebase maintains identity continuity across frames. Requires implementing a robust Kalman filter associator (ByteTrack / Sort logic). |
| **Ray-Casting Point-in-Polygon Engine**| Neither | **Missing & Requiring Implementation** | Neither codebase tests ground-plane footprint contact points against arbitrary polygons. Requires implementing the ray-casting algorithm. |
| **Temporal Modal Activity Smoother** | Neither | **Missing & Requiring Implementation** | Neither codebase debounces posture predictions over time. Requires implementing the 75-frame rolling modal filter. |
| **Four Decoupled Scorecards Engine** | Neither | **Missing & Requiring Implementation** | Neither codebase computes Workflow Efficiency, Activity Share, Occupancy Variation, or Output Effectiveness. Requires implementing the formal metric catalog. |
| **Structured Relational Storage Tier**| Neither | **Missing & Requiring Implementation** | Neither codebase provides structured SQL persistence, time-series hypertables, or automated data retention. Requires implementing the database models. |
| **Asynchronous MP4 Video Exporter** | Neither | **Missing & Requiring Implementation** | Neither codebase supports rendering and exporting annotated MP4 clips with burned-in telemetry and audio stripping. Requires implementation. |

---

## 3. Primary Application Architecture Selection

### Decision: Decoupled FastAPI Backend + Streamlit Analytics UI
- **Backend Service (`src/backend`)**: **FastAPI** running on Uvicorn. Serves high-throughput REST APIs, handles session state, provides WebSocket telemetry streaming at `/ws/live-telemetry`, and exposes operational webhook ingestion endpoints.
- **Frontend Portal (`src/frontend`)**: **Streamlit** powered by `streamlit-echarts`. Consumes FastAPI REST and WebSocket endpoints, providing all 10 mandatory operational views without thread blocking or unhandled client-side DOM exceptions.
- **Perception Pipeline (`src/perception`)**: Modular Python package utilizing OpenCV DNN for YOLO detection, ByteTrack for MOT, ray-casting for zone occupancy, and 2D biomechanical keypoint geometry for activity classification.
- **Storage Tier (`src/storage`)**: SQLAlchemy 2.0 ORM with SQLite (for standalone embedded edge deployment) and PostgreSQL / TimescaleDB compatibility (for enterprise cluster deployment).

### Why Flask Was Deprecated
The Flask prototype in `audit_extracted/.../app.py` suffered from severe architectural flaws:
1. Synchronous blocking video generator starved server worker threads under multiple client connections.
2. Client-side JavaScript polled `/status` every $500\text{ ms}$ (`BUG-01`), triggering race conditions and deadlocks.
3. Lack of modular separation between perception, business logic, and UI rendering.

---

## 4. Environment & Dependency Compatibility

The host environment runs **Python 3.11.9** with the following key verified packages:
- `fastapi 0.141.1` & `uvicorn 0.40.0`
- `pydantic 2.13.4`
- `streamlit 1.58.0` & `streamlit-echarts 0.7.0`
- `SQLAlchemy 2.0.52`
- `numpy 2.4.6`, `scipy 1.17.1`, `pandas 2.3.3`, `scikit-learn 1.9.0`
- `pytest 9.1.1`
- `opencv-python-headless 5.0.0.93` (Installed & verified)

All planned modules are $100\%$ compatible with this Python 3.11 environment.

---

## 5. Directory Structure & Execution Plan

```
src/
├── core/                  # Configuration, logging, secret masking (SEC-01)
├── perception/            # Ingestion, YOLOv4-tiny/YOLOv8 DNN, ByteTrack MOT, PIP geometry
├── analytics/             # Metric registry, Scorecards A-D, calibration, layout rules
├── storage/               # SQLAlchemy models, SQLite/TimescaleDB engine, event logging
├── backend/               # FastAPI application, routers, WebSockets, webhooks
├── frontend/              # Streamlit dashboard, 10 operational views, ECharts widgets
├── export/                # Video overlay renderer, MP4 exporter
tests/
├── unit/                  # Metric formulas, ray-casting PIP, coordinate normalization
├── integration/           # FastAPI endpoints, WebSocket telemetry, database persistence
└── regression/            # BUG-01, BUG-02, BUG-03, SEC-01, ANL-01 regression tests
```

---

## 6. Execution Progress Checklist

- [x] Phase 0: Audit & Execution Strategy (`EXECUTION_AUDIT.md`)
- [ ] Phase 1: Core Architecture, Config & Secret Sanitization
- [ ] Phase 2: Perception Engine (Detection, Multi-Person Tracking & Footprints)
- [ ] Phase 3: Spatial Zone Engine & Occupancy State Machine
- [ ] Phase 4: Activity Classification & Modal Filtering
- [ ] Phase 5: Workflow Bottleneck & Transit Churn Engine
- [ ] Phase 6: Scorecards A, B, C, D & Calibration Engine
- [ ] Phase 7: Storage Tier & FastAPI Backend Services
- [ ] Phase 8: Annotated Video Streaming & MP4 Export
- [ ] Phase 9: Unified Streamlit Analytics Dashboard (10 Views)
- [ ] Phase 10: Operational Outcome Integration
- [ ] Phase 11: End-to-End Testing, Regression Verification & Acceptance
