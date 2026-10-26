# Phase 15: Testing and Validation Specification

## 1. Document Overview

### 1.1 Purpose
This document specifies the comprehensive quality assurance, automated test pyramid, regression test suites, and empirical ground-truth benchmarking protocols for the CCTV Workplace Productivity and Workflow Intelligence System (WBPIS). It establishes measurable acceptance criteria and verification procedures, ensuring that no metric or model is labeled as "validated" without verifiable ground-truth evidence.

### 1.2 Scope
- **Testing Pyramid**: Unit tests, integration tests, performance/stress tests, and perception accuracy benchmarks.
- **Regression Test Suites**: Formal remediation verification for legacy audit bugs (`BUG-01` to `BUG-03`, `SEC-01`, `ANL-01`).
- **Benchmark Specification**: The **WBPIS-BENCH-V1** standardized ground-truth evaluation dataset and testing protocol.

---

## 2. Existing Implementation Findings

Grounding assessment based on [`reports/CCTV_PRODUCTIVITY_CODEBASE_AUDIT.md`](file:///C:/Users/DELL/Desktop/cctv/reports/CCTV_PRODUCTIVITY_CODEBASE_AUDIT.md):

| Test Area | Codebase Location | Audit Status | Audit Assessment & Deficiencies |
| :--- | :--- | :--- | :--- |
| **Automated Unit Tests** | Neither codebase | `UNAVAILABLE` | Zero unit test files (`test_*.py`) exist in either legacy codebase; changes were tested via ad-hoc manual execution. |
| **Ground-Truth Benchmarks** | Neither codebase | `UNAVAILABLE` | Neither system possessed hand-annotated video clips to measure detection mAP, tracking MOTA, or posture F1 scores. |
| **Stress & Endurance Testing**| Neither codebase | `UNAVAILABLE` | Long-running endurance tests were never performed; memory leaks in OpenCV and Python garbage collection led to system crashes after 6–8 hours. |
| **Audit Bug Regressions** | `audit_extracted/.../` | `EXISTING_VERIFIED` | Multiple severe bugs (`BUG-01` to `BUG-03`, `SEC-01`) identified in audit report remained unpatched in source files. |

---

## 3. Four-Tier Testing Pyramid Architecture

```mermaid
flowchart TD
    subgraph Tier 4: Benchmark & Perception Validation
        BENCH["WBPIS-BENCH-V1 Ground Truth<br>(mAP@50, MOTA, IDF1, HOTA, Posture F1)"]
    end

    subgraph Tier 3: Performance & Endurance Testing
        STRESS["Multi-Stream Stress & Endurance<br>(15 FPS sustained, 48h Memory Leak Audit, Concurrency)"]
    end

    subgraph Tier 2: Integration & Contract Testing
        INTEG["Pipeline Dataflow & API Contracts<br>(RTSP -> TimescaleDB, WebSockets, RFC 7807)"]
    end

    subgraph Tier 1: Unit & Mathematical Testing
        UNIT["Unit & Mathematical Verification<br>(Ray-Casting PIP, Metric Formulas, Decoupled State Machines)"]
    end

    UNIT --> INTEG --> STRESS --> BENCH
```

---

## 4. Tier 1: Unit & Mathematical Verification

Unit tests validate core mathematical algorithms in total isolation from network cameras or databases:
- **Framework**: `pytest`, `pytest-cov`, `hypothesis` (property-based testing).
- **Execution Target**: Runs on every Git commit via pre-commit hooks and GitHub Actions ($< 30\text{ seconds}$ execution time).
- **Coverage Target**: $\ge 90\%$ line and branch coverage across all modules in `src/perception/math/` and `src/analytics/metrics/`.

### 4.1 Key Unit Test Suites
1. `test_ray_casting_pip.py`: Validates point-in-polygon containment for complex, concave, and degenerate polygons against Shapely reference implementations.
2. `test_metric_formulas.py`: Verifies mathematical correctness of all 26 metrics across Groups A through E, testing boundary conditions ($x=0$, $x=\infty$, division by zero).
3. `test_temporal_modal_filter.py`: Verifies that single-frame prediction noise is eliminated by the 75-frame rolling majority voting filter.
4. `test_clock_synchronization.py`: Tests monotonic drift compensation algorithms under simulated synthetic clock skews.

---

## 5. Tier 2: Integration & API Contract Testing

Integration tests verify dataflow across service boundaries using Docker Compose test harnesses:
- **Framework**: `pytest-asyncio`, `httpx`, `testcontainers-python`.
- **Database Test Isolation**: Executes against a dedicated ephemeral TimescaleDB container initialized with Alembic migrations.

### 5.1 Key Integration Test Suites
1. `test_api_contracts.py`: Validates all REST endpoints against OpenAPI 3.1 schemas, verifying RFC 7807 problem detail error structures.
2. `test_websocket_telemetry.py`: Connects asynchronous WebSocket clients to `/ws/live-telemetry/{camera_id}`, asserting message schema compliance and streaming frequency.
3. `test_dual_control_export.py`: Tests the video export approval workflow, verifying that requests without valid DPO cryptographic tokens are rejected with HTTP 403.
4. `test_data_retention_shredding.py`: Fast-forwards mock database timestamps to verify that TimescaleDB automated retention policies drop chunks older than 14 days.

---

## 6. Tier 3: Performance & Endurance Testing

Performance tests stress the system under maximum operational load to prevent real-world production crashes:
- **Framework**: Locust (API load testing), Python multi-stream RTSP synthetic simulator, `memory_profiler`.

| Test Scenario | Test Duration | Workload Profile | Acceptance Threshold |
| :--- | :--- | :--- | :--- |
| **Sustained Stream Throughput** | 12 Hours | 4 Concurrent 1080p RTSP streams @ 15 FPS | $\ge 14.8\text{ FPS sustained per stream}$ |
| **Memory Leak Endurance** | 48 Hours | Continuous ingestion + YOLOv8 + ByteTrack | Process RAM growth $\le 50\text{ MB}$ over 48 hours |
| **WebSocket Client Saturation** | 1 Hour | 25 Concurrent dashboard viewer WebSocket connections | Broadcast latency $\le 250\text{ ms}$; zero socket drops |
| **High Density Track Load** | 2 Hours | Synthetic video feed with 30 concurrent people | Inference latency $\le 45\text{ ms}$; zero thread lock |

---

## 7. Tier 4: Perception Accuracy & Benchmark Specification (WBPIS-BENCH-V1)

To eliminate unverified claims of computer vision accuracy, WBPIS establishes the **WBPIS-BENCH-V1** benchmark dataset:

```
┌────────────────────────────────────────────────────────────────────────┐
│                   WBPIS-BENCH-V1 BENCHMARK DATASET                     │
├────────────────────────────────────────────────────────────────────────┤
│ Total Video Duration:   40 Hours across 8 Multi-Camera Office Views    │
│ Lighting Conditions:    Morning Glare, Fluorescent, Evening Low-Light │
│ Density Profiles:       Sparse (1-3), Moderate (4-8), Congested (12+)  │
│ Annotations:            250,000 Hand-Labeled Ground-Truth Bounding    │
│                         Boxes, 2D Skeletons, and Activity States       │
│ Splits:                 Train (60%), Validation (20%), Test (20%)     │
└────────────────────────────────────────────────────────────────────────┘
```

### 7.1 Perception Acceptance Thresholds

| Perception Task | Evaluation Metric | Mathematical Definition | Minimum Acceptance Target |
| :--- | :--- | :--- | :--- |
| **Person Detection** | $\text{mAP@50}$ | Mean Average Precision at $\text{IoU} \ge 0.50$ | $\ge 0.88$ |
| **Multi-Object Tracking** | $\text{MOTA}$ | Multiple Object Tracking Accuracy | $\ge 0.75$ |
| **Tracking Continuity** | $\text{IDF1}$ | ID F1 Score (ratio of correctly identified detections) | $\ge 0.78$ |
| **Tracking Association** | $\text{HOTA}$ | Higher Order Tracking Accuracy | $\ge 0.65$ |
| **Posture Classification** | Macro $\text{F1}$ | Harmonic mean of precision and recall across 7 states | $\ge 0.85$ |
| **Workstation Occupancy**| Error Rate | $|\text{Observed Duration} - \text{True Duration}| / \text{True}$ | $\le 4.0\%$ |

---

## 8. Legacy Bug Regression Test Suites

WBPIS incorporates automated regression tests targeting every critical vulnerability uncovered in the codebase audit:

```python
# tests/regression/test_legacy_audit_regressions.py

def test_regression_bug_01_polling_eliminated():
    """Verify HTTP /status rapid polling is superseded by WebSockets."""
    from src.backend.main import app
    client_routes = [route.path for route in app.routes]
    assert "/status" not in client_routes, "Legacy polling route /status must not exist."

def test_regression_bug_02_coordinate_float_truncation():
    """Verify normalized float coordinates are not truncated by int()."""
    from src.perception.spatial import parse_normalized_coordinates
    raw_coords = [[0.345, 0.420], [0.510, 0.680]]
    parsed = parse_normalized_coordinates(raw_coords)
    assert parsed[0][0] == 0.345, "Float coordinate truncated to integer!"

def test_regression_bug_03_video_rewind_on_rtsp():
    """Verify cap.set(CAP_PROP_POS_FRAMES) is never called on live streams."""
    from src.perception.ingest import VideoIngestWorker
    import inspect
    source = inspect.getsource(VideoIngestWorker.calibrate_frames)
    assert "CAP_PROP_POS_FRAMES" not in source, "Dangerous seek called on live RTSP!"

def test_regression_sec_01_credential_leak_in_logs(caplog):
    """Verify camera passwords are sanitized from log outputs."""
    from src.perception.ingest import sanitize_rtsp_url
    url = "rtsp://admin:SecretPass123@192.168.1.50:554/live"
    sanitized = sanitize_rtsp_url(url)
    assert "SecretPass123" not in sanitized
    assert sanitized == "rtsp://admin:*****@192.168.1.50:554/live"
```

---

## 9. Verification and Acceptance Criteria

| ID | Test / Acceptance Criterion | Verification Method | Pass Threshold |
| :--- | :--- | :--- | :--- |
| **AC-TEST-01** | Full unit test suite passes with zero errors on CI/CD runner. | Automated `pytest` execution. | $100\%$ tests passing; coverage $\ge 90\%$ |
| **AC-TEST-02** | WBPIS-BENCH-V1 evaluation suite passes all minimum accuracy gates. | Benchmark evaluation runner script. | Detection $\text{mAP} \ge 0.88$; $\text{MOTA} \ge 0.75$ |
| **AC-TEST-03** | 48-Hour endurance test completes with zero memory crashes or restarts. | Long-running Linux server stress test. | Zero OOM kills; zero unhandled exceptions |
| **AC-TEST-04** | Regression suite passes for all 5 audit bugs (`BUG-01` to `BUG-03`, `SEC-01`, `ANL-01`). | Automated `pytest tests/regression/`. | $100\%$ regression tests passing |

---

## 10. Open Questions & Assumptions

> [!NOTE]
> ### 1. Ground-Truth Data Collection Protocol
> *Assumption*: Facility volunteers will provide explicit written consent to participate in the 40-hour WBPIS-BENCH-V1 benchmarking recording sessions.
> *Open Question*: Should faces in the benchmark dataset be pre-blurred prior to manual bounding box annotation, or blurred post-annotation to ensure facial landmark accuracy is not affected?

---

## 11. Related Documentation Links

- **System Architecture**: Pipeline tested in [`02_SYSTEM_ARCHITECTURE.md`](file:///C:/Users/DELL/Desktop/cctv/docs/implementation/02_SYSTEM_ARCHITECTURE.md).
- **Perception Pipelines**: YOLOv8 + ByteTrack in [`04_PERSON_DETECTION_TRACKING_AND_IDS.md`](file:///C:/Users/DELL/Desktop/cctv/docs/implementation/04_PERSON_DETECTION_TRACKING_AND_IDS.md).
- **Security Testing**: STRIDE penetration tests in [`16_SECURITY_PRIVACY_AND_ACCESS_CONTROL.md`](file:///C:/Users/DELL/Desktop/cctv/docs/implementation/16_SECURITY_PRIVACY_AND_ACCESS_CONTROL.md).
- **Roadmap Milestones**: Testing phases in [`18_IMPLEMENTATION_ROADMAP.md`](file:///C:/Users/DELL/Desktop/cctv/docs/implementation/18_IMPLEMENTATION_ROADMAP.md).
