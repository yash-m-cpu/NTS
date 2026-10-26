# Comprehensive Technical Audit: React Migration Strategy
## Workplace Productivity & Workflow Intelligence System (WBPIS)

**Date:** October 18, 2026  
**Author:** Senior React Architect & Lead Software Migration Specialist  
**Workspace:** `C:\Users\DELL\Desktop\cctv`  
**Target Frontend:** React 19 + TypeScript + Vite + TailwindCSS / Lucide + Apache ECharts  

---

## 1. Executive Summary & Purpose

This audit serves as the architectural blueprint for migrating the existing Streamlit dashboard interface of the **CCTV Workplace Productivity & Workflow Intelligence System (WBPIS)** into an enterprise-grade, high-performance **React + TypeScript SPA (Single Page Application)**.

### Core Objectives
1. **100% Feature Parity**: Every view, widget, card, chart, table, metric, filter, and action present in the current Streamlit app (`src/frontend/`) must be replicated in React.
2. **Zero CV Pipeline Disturbance**: The Python backend (`FastAPI`, `OpenCV`, `YOLOv4-tiny`/`YOLOv8n`, `SORT`/Euclidean tracking, spatial zone logic) remains the single source of truth and execution engine. No computer vision logic will be rewritten in JavaScript.
3. **Preservation of Anti-Surveillance Covenants**: Strictly uphold the cryptographic pseudonymization of employee tracks (`TRK-xxxx`), zero facial recognition, absence of punitive employee ranking, and $k$-anonymity ($k \ge 5$) constraints.
4. **Enhanced Streaming & UX**: Replace full-page Streamlit reloads and script executions with clean React state management, resilient MJPEG video streaming, auto-reconnecting telemetry, and client-side routing.

---

## 2. Inventory of Existing Codebases & Components

### 2.1 Workspace Structure Overview

```
C:\Users\DELL\Desktop\cctv
├── audit_extracted/                   # Legacy prototype archive (Flask + Darknet YOLOv4-tiny)
│   └── OpenCV-Based-Real-time-Employee-Tracking-System-main/
│       ├── app.py                     # Flask entry point (port 5000)
│       ├── employee_tracking_fixed.py # Binary ROI overlap presence detector
│       └── yolo_model/                # coco.names, yolov4-tiny.cfg, yolov4-tiny.weights
├── config/
│   └── zones.json                     # Persistent polygon spatial definitions
├── docs/
│   ├── implementation/                # 18 design and architecture specifications
│   └── migration/                     # Migration audit, parity checklist, API contract
├── exports/                           # Directory for rendered MP4 clips
├── logs/                              # Audit and pipeline execution logs
├── output_frames/                     # Transient debug frames
├── reports/                           # Technical audit reports
├── src/
│   ├── analytics/                     # Scorecard engines (A, B, C, D), recommendations
│   ├── backend/                       # FastAPI application (main.py) and pipeline manager (pipeline.py)
│   ├── core/                          # Config, logging, Pydantic schemas, security
│   ├── export/                        # Video exporter (MP4 rendering with privacy overlays)
│   ├── frontend/                      # Existing Streamlit application (to be replaced)
│   │   ├── app.py                     # Streamlit main entry point (sidebar, routing)
│   │   ├── components/                # api_client.py, echarts_charts.py
│   │   └── views/                     # 11 operational views (view01 through view10 + zone_editor)
│   ├── perception/                    # Ingest, YOLO detector, tracker, spatial logic, activity
│   └── storage/                       # SQLite/SQLAlchemy database, models, repository
├── tests/                             # 36 unit, integration, and regression tests
└── uploads/                           # Ingested CCTV MP4 video files
```

---

## 3. Detailed Audit of the 11 Operational Frontend Views

| View Name | Entry File | Core Functionality & Visible Controls | Backend & Data Dependencies |
| :--- | :--- | :--- | :--- |
| **01. Live Annotated CCTV** | `view01_live_cctv.py` | • Real-time MJPEG video player<br>• Video file uploader (.mp4, .avi, .mov)<br>• Pipeline Start/Stop buttons<br>• Metric cards: Connection Status, Inference Rate (FPS), Active Tracks<br>• Overlay LOD checkboxes: Workstation Polygons, Bounding Boxes, Footprints, Track Badges, Activity State Pills<br>• Privacy Guard info card<br>• Stream Health Metrics Footer (Camera Target, Frames Ingested, Dropped Frames, Coverage %) | `GET /api/v1/stream/live/{camera_id}`<br>`GET /api/v1/sessions/status/{camera_id}`<br>`POST /api/v1/sessions/start`<br>`POST /api/v1/sessions/stop`<br>`POST /api/v1/videos/upload` |
| **02. Ephemeral Track Details** | `view02_track_details.py` | • Ephemeral Track selector (`TRK-xxxx`)<br>• Identity Card: Track ID, Assigned Zone, Activity state pill<br>• Metric cards: Personal Interruptions, Service Waiting Time, Zone Transit Churn<br>• Radial Gauge: Workstation Presence Ratio (%)<br>• Stacked 100% Bar: Track Ergonomic Posture Breakdown (`ACT-01` to `ACT-07`)<br>• Table: Posture states, shares %, ergonomic status<br>• Anti-Surveillance guarantees | `GET /api/v1/telemetry/live/{camera_id}`<br>(Active tracks, dwell durations, activity breakdown) |
| **03. Workflow Efficiency (Scorecard A)** | `view03_workflow_efficiency.py` | • Radial Gauge: Scorecard A Workflow Efficiency (/100)<br>• Metric cards: Focus Interruption Frequency, Corridor Congestion Ratio, Service Waiting Ratio, Zone Transit Churn<br>• **Person-Wise Spatial Friction & Bottleneck Table**: Track ID, Zone, Interruptions, Waiting %, Transit Churn, Corridor Exposure %, Friction Risk Level, Primary Driver<br>• Circulation Flow Sankey diagram<br>• Layout Optimization Insights cards | `GET /api/v1/analytics/scorecards`<br>`GET /api/v1/telemetry/live/{camera_id}`<br>`GET /api/v1/analytics/recommendations` |
| **04. Activity Distribution (Scorecard B)** | `view04_activity_distribution.py` | • Anti-Conflation Mandate banner<br>• Radial Gauge: Scorecard B Activity Distribution (/100)<br>• 100% Stacked Bar: Pod Aggregate Ergonomic Time Shares (`ACT-01` to `ACT-07`)<br>• Sub-metric cards: Seated Workstation Share, Collaboration Share, Active Mobility Share, Unobserved Ratio<br>• **Person-Wise Ergonomic Posture Breakdown Table**: Track ID, Current State, Seated %, Standing %, Walking %, Interaction %, Collab %, Away/Unknown %, Ergonomic Assessment<br>• Shift Chronological Timeline Table | `GET /api/v1/analytics/scorecards`<br>`GET /api/v1/telemetry/live/{camera_id}` |
| **05. Occupancy & Presence (Scorecard C)** | `view05_occupancy_presence.py` | • Radial Gauge: Scorecard C Occupancy & Utilization (/100)<br>• Metric cards: Workstation Occupancy Rate (WOR), Space Rightsizing Potential, Away-Time Ratio, Transitory Debounce Duration<br>• **Person-Wise Workstation Presence & Dwell Times Table**: Track ID, Zone, Desk Presence Ratio %, Continuous Dwell, Transitory Departures, Prolonged Departures, Current State, Space Planning Affordance<br>• Workstation Zone Utilization Matrix bar chart<br>• Hourly Occupancy Trend & Confidence Variance chart ($\pm 1\sigma$ band)<br>• Space Planning Guidance (Rule REC-01) card | `GET /api/v1/analytics/scorecards`<br>`GET /api/v1/telemetry/live/{camera_id}`<br>`GET /api/v1/zones`<br>`GET /api/v1/analytics/recommendations` |
| **06. Output Effectiveness (Scorecard D)** | `view06_output_effectiveness.py` | • Anti-Conflation Mandate & External Data Notice<br>• Conditional Render: When external data unconfigured, renders explicit N/A notice + External Data Ingestion Simulator / Webhook Tester form<br>• When data ingested: Radial Gauge Output Effectiveness (/100), Throughput Attainment, First-Pass Quality Rate, On-Time SLA Adherence, Rework Rate<br>• Data provenance disclosure | `GET /api/v1/analytics/scorecards`<br>`POST /api/v1/ingest/operational-outcomes` |
| **07. Team & Workspace Overview** | `view07_team_workspace.py` | • Strict $k$-Anonymity ($k \ge 5$) & Anti-Ranking Callout<br>• Metric cards: Monitored Team Size, Pod Collaboration Index, Meeting Room Pressure, Focus Work Protection<br>• Interactive Floor Plan & Pod Utilization Grid cards (occupancy %, active badges, type colors)<br>• Collaboration & Huddle Activity insights card | `GET /api/v1/zones`<br>`GET /api/v1/analytics/scorecards` |
| **08. Historical Trend Comparison** | `view08_historical_comparison.py` | • Baseline Window (Period A) and Experimental Window (Period B) selectors<br>• Comparative Metric Delta Table: Metric Name, Period A, Period B, Absolute Delta, Relative Change, p-Value, Statistical Significance<br>• Statistically Verified Success summary callout | Historical analytics / A/B comparison calculations |
| **09. Video Export Controls** | `view09_video_export.py` | • Export Request Specification Form: Source Camera, Duration slider (30-300 frames), DPO Authorization Token (password field), Automated Privacy Masking checkbox, Mandatory Business Justification text area, Submit button<br>• Active Export Queue & Download Registry: Job ID, Status badge, Progress %, Frame count, Download Redacted MP4 button, Refresh status<br>• Privacy & Compliance Assurances | `POST /api/v1/export/video`<br>`GET /api/v1/export/status/{job_id}`<br>`GET /exports/{filename}` |
| **10. Data Quality & Model Health** | `view10_data_quality.py` | • Ingestion & Pipeline Performance Table: Camera, State, Inference Rate, Frames Ingested, Dropped Frames, Dropped Ratio, Observation Coverage, Health Rating<br>• Perception Stability Metrics: Tracking Continuity, Centroid Ground Error, Modal Smoothing Window, Observation Coverage Threshold<br>• Population Stability Index (PSI) drift monitoring radial gauge<br>• STRIDE Security & Privacy Audit Trail Table | `GET /api/v1/sessions/status/{camera_id}`<br>`GET /api/v1/system/audit-logs` |
| **11. Interactive Zone Editor** | `zone_editor.py` | • Currently Configured Spatial Zones Table: Zone ID, Name, Type, Capacity, Target Camera, Vertices Count, Sample Coordinates<br>• Tab 1 (Add/Update Zone): Zone ID, Display Name, Zone Type, Capacity, Camera ID, JSON Polygon Coordinates editor with float $[0.0, 1.0]$ validation, Save button<br>• Tab 2 (Delete Zone): Zone selector, Delete button | `GET /api/v1/zones`<br>`POST /api/v1/zones`<br>`DELETE /api/v1/zones/{zone_id}` |

---

## 4. Chart Migration Strategy (ECharts in React)

The Streamlit dashboard uses `streamlit-echarts` for 5 distinct visualization types in `src/frontend/components/echarts_charts.py`. All of these will be cleanly migrated using `echarts-for-react` (backed by the canonical `echarts` npm library):

1. **`render_radial_gauge`**:
   - Speedometer-style circular radial gauge with gradient color stops (Red `#f56c6c`, Amber `#e6a23c`, Green `#67c23a`).
   - Crisp high-contrast dark theme fonts (`#f8fafc` detail, `#e2e8f0` title, `#cbd5e1` labels).
   - Electric blue pointer needle (`#3b82f6`).
   - Supports custom units (`%`, `/100`, `min`).
2. **`render_activity_stacked_bar`**:
   - 100% horizontal stacked bar for the 7 standardized activity classes (`ACT-01` through `ACT-07`).
   - Exact hex palette: `#2b82c9`, `#2ecc71`, `#f39c12`, `#9b59b6`, `#1abc9c`, `#e74c3c`, `#95a5a6`.
3. **`render_sankey_flow`**:
   - Sankey flow diagram representing zone-to-zone circulation volumes (Desk Pod A/B, Meeting Room 1, Collaboration Bar, Corridor Spine, Kitchen).
4. **`render_occupancy_matrix`**:
   - Category bar chart displaying utilization percentages across registered spatial zones.
5. **`render_trend_with_variance`**:
   - Time-series line chart with dual-stacked confidence bands displaying Mean Occupancy $\pm 1\sigma$ variance over shift hours.
6. **`render_psi_drift_gauge`**:
   - Specialized Population Stability Index gauge ($0.00$ to $0.35$ range) with stability thresholds ($< 0.10$ stable, $0.10 - 0.25$ moderate drift, $> 0.25$ significant drift).

---

## 5. Architectural Invariants & Non-Negotiables

1. **CCTV Feed Display**: Uses standard `<img src="/api/v1/stream/live/CAM-01" />` pattern with automatic error handling, placeholder states, and stream controls.
2. **API Communication**: Unified Axios / Fetch client with baseURL `/api/v1`, request/response interceptors, robust timeout and offline handling.
3. **Telemetry Polling / Refresh**: Active views poll live telemetry at 2 Hz or 1 Hz (or WebSocket where appropriate) without blocking UI interactivity.
4. **Production Build & Serving**: The Vite app builds into `frontend/dist/`. The FastAPI backend will be configured to optionally serve static assets from `frontend/dist/` in production mode while proxying API routes seamlessly.
