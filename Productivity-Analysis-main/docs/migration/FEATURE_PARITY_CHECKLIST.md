# Feature Parity Checklist: Streamlit to React Migration
## Workplace Productivity & Workflow Intelligence System (WBPIS)

**Date:** October 18, 2026  
**Status Values:** `NOT_STARTED` | `IN_PROGRESS` | `IMPLEMENTED` | `TESTED` | `BLOCKED`

---

## 1. Application Shell & Global Controls

| Feature / Component | Existing Streamlit Location | React Implementation Location | Status | Verification Notes |
| :--- | :--- | :--- | :---: | :--- |
| Global Dark/High-Contrast Theme | `app.py`, inline styles | `frontend/src/index.css`, TailwindCSS | TESTED | Crisp typography, dark slate backgrounds (`#0f172a`, `#1e293b`) |
| Top Navigation Bar & Brand Header | `app.py` lines 152-155 | `frontend/src/components/layout/Header.tsx` | TESTED | System title, subtitle, health pill, camera & department selectors |
| Anti-Surveillance Covenant Badge | `app.py` line 86 | `frontend/src/components/common/CovenantBadge.tsx` | TESTED | "🛡️ Anti-Surveillance Covenant Active" |
| Backend Health Status Indicator | `app.py` lines 88-96 | `frontend/src/components/layout/Header.tsx` | TESTED | Polls `GET /health` with online/standby badge and refresh button |
| Active Camera Selector (`CAM-01`, `CAM-02`, `CAM-03`) | `app.py` line 99 | `frontend/src/context/AppContext.tsx` | TESTED | Global state synced across all views |
| Target Department Selector (`ENG`, `PRODUCT`, `OPERATIONS`, `SALES`) | `app.py` line 100 | `frontend/src/context/AppContext.tsx` | TESTED | Global state synced across all views |
| Global Custom Video Upload Modal/Drawer | `app.py` lines 102-127 | `frontend/src/components/video/VideoUploadModal.tsx` | TESTED | Uploads to `POST /api/v1/videos/upload` and triggers pipeline switch |
| Sidebar Navigation Menu (11 Operational Views) | `app.py` lines 129-148 | `frontend/src/components/layout/Sidebar.tsx` | TESTED | Client-side routing with React Router |

---

## 2. View 01: Live Annotated CCTV

| Feature / Component | Existing Location | React Component | Status | Verification Notes |
| :--- | :--- | :--- | :---: | :--- |
| Real-time MJPEG Video Stream Player | `view01_live_cctv.py` lines 106-124 | `frontend/src/pages/View01LiveCctv.tsx` | TESTED | Streaming from `/api/v1/stream/live/{camera_id}` |
| Video File Ingestion / Upload Dropzone | `view01_live_cctv.py` lines 19-53 | `frontend/src/pages/View01LiveCctv.tsx` | TESTED | Handles `.mp4`, `.avi`, `.mov` with upload progress |
| Pipeline Start Ingestion Button | `view01_live_cctv.py` lines 61-65 | `frontend/src/pages/View01LiveCctv.tsx` | TESTED | Calls `POST /api/v1/sessions/start` |
| Pipeline Stop Ingestion Button | `view01_live_cctv.py` lines 66-70 | `frontend/src/pages/View01LiveCctv.tsx` | TESTED | Calls `POST /api/v1/sessions/stop` |
| Connection Status Metric Card | `view01_live_cctv.py` lines 71-77 | `frontend/src/components/metrics/MetricCard.tsx` | TESTED | ONLINE / STOPPED with Streaming / Standby pill |
| Inference Rate (FPS) Metric Card | `view01_live_cctv.py` lines 78-80 | `frontend/src/components/metrics/MetricCard.tsx` | TESTED | FPS counter from `/api/v1/sessions/status/{camera_id}` |
| Active Tracks Count Metric Card | `view01_live_cctv.py` lines 81-84 | `frontend/src/components/metrics/MetricCard.tsx` | TESTED | Real-time person count |
| Level-of-Detail (LOD) Layer Toggles | `view01_live_cctv.py` lines 89-96 | `frontend/src/pages/View01LiveCctv.tsx` | TESTED | Checkboxes for polygons, boxes, footprints, badges, pills |
| Privacy Guard Info Card | `view01_live_cctv.py` lines 98-104 | `frontend/src/pages/View01LiveCctv.tsx` | TESTED | Facial recognition ban & ephemeral hash guarantees |
| Stream Health Metrics Footer (Camera, Ingested, Dropped, Coverage) | `view01_live_cctv.py` lines 125-139 | `frontend/src/pages/View01LiveCctv.tsx` | TESTED | Real-time diagnostics footer |

---

## 3. View 02: Ephemeral Track Details

| Feature / Component | Existing Location | React Component | Status | Verification Notes |
| :--- | :--- | :--- | :---: | :--- |
| Ephemeral Track Selector (`TRK-xxxx`) | `view02_track_details.py` lines 111-114 | `frontend/src/pages/View02TrackDetails.tsx` | TESTED | Dynamic dropdown populated from live active tracks |
| Track Identity Card & Activity State Pill | `view02_track_details.py` lines 120-131 | `frontend/src/pages/View02TrackDetails.tsx` | TESTED | Track ID, Assigned Zone, Activity badge |
| Personal Interruptions Metric Card | `view02_track_details.py` lines 132-140 | `frontend/src/components/metrics/MetricCard.tsx` | TESTED | Event count and frequency (/hr) |
| Service Waiting Time Metric Card | `view02_track_details.py` lines 141-149 | `frontend/src/components/metrics/MetricCard.tsx` | TESTED | Duration (sec) and % of session time |
| Zone Transit Churn Metric Card | `view02_track_details.py` lines 150-158 | `frontend/src/components/metrics/MetricCard.tsx` | TESTED | Move count and velocity (moves/hr) |
| Workstation Presence Ratio Radial Gauge | `view02_track_details.py` lines 170-184 | `frontend/src/components/charts/RadialGaugeChart.tsx` | TESTED | 0-100% presence ratio (`ACT-01`+`ACT-02`+`ACT-04`) |
| Continuous Dwell Duration Caption | `view02_track_details.py` line 185 | `frontend/src/pages/View02TrackDetails.tsx` | TESTED | "Active desk presence: X% \| Continuous focus dwell: Y min (Zs)" |
| Individual Ergonomic Posture 100% Bar | `view02_track_details.py` lines 188-190 | `frontend/src/components/charts/StackedBarChart.tsx` | TESTED | 7 activity classes for the selected track |
| Individual Posture State Data Table | `view02_track_details.py` lines 200-210 | `frontend/src/components/common/DataTable.tsx` | TESTED | Code, State, Individual Share %, Status |
| Anti-Surveillance & Privacy Guarantees | `view02_track_details.py` lines 212-224 | `frontend/src/pages/View02TrackDetails.tsx` | TESTED | Zero facial recognition, 24h salt rotation, no ranking |

---

## 4. View 03: Workflow Efficiency (Scorecard A)

| Feature / Component | Existing Location | React Component | Status | Verification Notes |
| :--- | :--- | :--- | :---: | :--- |
| Primary Scorecard A Radial Gauge | `view03_workflow_efficiency.py` lines 32-36 | `frontend/src/components/charts/RadialGaugeChart.tsx` | TESTED | Composite Score /100 with confidence level & department |
| Interruption Frequency Metric Card | `view03_workflow_efficiency.py` lines 41-48 | `frontend/src/components/metrics/MetricCard.tsx` | TESTED | Focus interruptions / hr |
| Corridor Congestion Ratio Metric Card | `view03_workflow_efficiency.py` lines 49-56 | `frontend/src/components/metrics/MetricCard.tsx` | TESTED | Congested time percentage (< 5%) |
| Service Waiting Ratio Metric Card | `view03_workflow_efficiency.py` lines 58-65 | `frontend/src/components/metrics/MetricCard.tsx` | TESTED | Waiting time at shared resources |
| Zone Transit Churn Metric Card | `view03_workflow_efficiency.py` lines 66-73 | `frontend/src/components/metrics/MetricCard.tsx` | TESTED | Inter-zone transit moves / hr |
| Person-Wise Spatial Friction Table | `view03_workflow_efficiency.py` lines 79-170 | `frontend/src/components/common/DataTable.tsx` | TESTED | Track ID, Zone, Interruption Freq, Waiting %, Transit Churn, Corridor %, Friction Level, Driver |
| Circulation Flows Sankey Diagram | `view03_workflow_efficiency.py` lines 172-176 | `frontend/src/components/charts/SankeyChart.tsx` | TESTED | Inter-zone transition flow volumes |
| Layout Optimization Insights Cards | `view03_workflow_efficiency.py` lines 178-190 | `frontend/src/pages/View03WorkflowEfficiency.tsx` | TESTED | Deterministic recommendation cards (Rule REC-01 to REC-04) |

---

## 5. View 04: Activity Distribution (Scorecard B)

| Feature / Component | Existing Location | React Component | Status | Verification Notes |
| :--- | :--- | :--- | :---: | :--- |
| Anti-Conflation Mandate Banner | `view04_activity_distribution.py` lines 21-25 | `frontend/src/pages/View04ActivityDistribution.tsx` | TESTED | Physical posture != cognitive productivity mandate |
| Primary Scorecard B Radial Gauge | `view04_activity_distribution.py` lines 44-48 | `frontend/src/components/charts/RadialGaugeChart.tsx` | TESTED | Composite Score /100 |
| Pod Aggregate Posture 100% Stacked Bar | `view04_activity_distribution.py` lines 49-53 | `frontend/src/components/charts/StackedBarChart.tsx` | TESTED | `ACT-01` to `ACT-07` breakdown across all occupants |
| Ergonomic Dynamics Sub-Metric Cards (4x) | `view04_activity_distribution.py` lines 56-95 | `frontend/src/components/metrics/MetricCard.tsx` | TESTED | Seated Share, Collab Share, Active Mobility, Unobserved Ratio |
| Person-Wise Ergonomic Posture Table | `view04_activity_distribution.py` lines 98-207 | `frontend/src/components/common/DataTable.tsx` | TESTED | Track ID, State, Seated %, Standing %, Walking %, Interaction %, Collab %, Away/Unknown %, Assessment |
| Shift Chronological Timeline Table | `view04_activity_distribution.py` lines 209-222 | `frontend/src/components/common/DataTable.tsx` | TESTED | Hour-by-hour posture shares across operational shift |

---

## 6. View 05: Occupancy & Presence (Scorecard C)

| Feature / Component | Existing Location | React Component | Status | Verification Notes |
| :--- | :--- | :--- | :---: | :--- |
| Primary Scorecard C Radial Gauge | `view05_occupancy_presence.py` lines 33-37 | `frontend/src/components/charts/RadialGaugeChart.tsx` | TESTED | Composite Score /100 |
| Spatial Presence Metric Cards (4x) | `view05_occupancy_presence.py` lines 39-56 | `frontend/src/components/metrics/MetricCard.tsx` | TESTED | Workstation Occupancy Rate, Space Rightsizing Potential, Away-Time Ratio, Debounce Duration |
| Person-Wise Workstation Presence Table | `view05_occupancy_presence.py` lines 59-172 | `frontend/src/components/common/DataTable.tsx` | TESTED | Track ID, Primary Zone, Presence %, Continuous Dwell, Transitory Departures, Prolonged Departures, State, Planning Affordance |
| Workstation Zone Utilization Matrix Bar | `view05_occupancy_presence.py` lines 177-190 | `frontend/src/components/charts/BarChart.tsx` | TESTED | Utilization percentage across registered zones |
| Hourly Occupancy Trend & $\pm 1\sigma$ Variance | `view05_occupancy_presence.py` lines 191-196 | `frontend/src/components/charts/TrendVarianceChart.tsx` | TESTED | Mean occupancy line with upper/lower confidence bands |
| Space Planning Guidance (Rule REC-01) Card | `view05_occupancy_presence.py` lines 198-210 | `frontend/src/pages/View05OccupancyPresence.tsx` | TESTED | Automated capacity guidance based on rolling WOR |

---

## 7. View 06: Output Effectiveness (Scorecard D)

| Feature / Component | Existing Location | React Component | Status | Verification Notes |
| :--- | :--- | :--- | :---: | :--- |
| External Deliverable Covenant Disclosure | `view06_output_effectiveness.py` lines 16-21 | `frontend/src/pages/View06OutputEffectiveness.tsx` | TESTED | Strict covenant: CCTV never substituted for work output |
| Conditional Render: Scorecard D Unavailable | `view06_output_effectiveness.py` lines 27-34 | `frontend/src/pages/View06OutputEffectiveness.tsx` | TESTED | Explicit N/A notification when no external webhook received |
| External Ingestion Simulator / Form | `view06_output_effectiveness.py` lines 36-71 | `frontend/src/pages/View06OutputEffectiveness.tsx` | TESTED | Posts test payload to `POST /api/v1/ingest/operational-outcomes` |
| Primary Scorecard D Radial Gauge | `view06_output_effectiveness.py` lines 79-83 | `frontend/src/components/charts/RadialGaugeChart.tsx` | TESTED | Output Effectiveness score /100 |
| Deliverable Performance Metric Cards (4x) | `view06_output_effectiveness.py` lines 84-104 | `frontend/src/components/metrics/MetricCard.tsx` | TESTED | Throughput Attainment, First-Pass Quality, On-Time SLA, Rework Rate |
| Cryptographic Data Provenance Notice | `view06_output_effectiveness.py` line 106 | `frontend/src/pages/View06OutputEffectiveness.tsx` | TESTED | Immutable enterprise audit confirmation |

---

## 8. View 07: Team & Workspace Overview

| Feature / Component | Existing Location | React Component | Status | Verification Notes |
| :--- | :--- | :--- | :---: | :--- |
| Strict $k$-Anonymity & Anti-Ranking Callout | `view07_team_workspace.py` lines 15-24 | `frontend/src/pages/View07TeamWorkspace.tsx` | TESTED | $k \ge 5$ compliance banner |
| Macro Team KPI Cards (4x) | `view07_team_workspace.py` lines 27-36 | `frontend/src/components/metrics/MetricCard.tsx` | TESTED | Team Size, Collab Index, Meeting Pressure, Focus Protection |
| Interactive Floor Plan Pod Cards Grid | `view07_team_workspace.py` lines 38-66 | `frontend/src/pages/View07TeamWorkspace.tsx` | TESTED | Card per zone with type badge, utilization %, active status |
| Collaboration & Huddle Activity Insights | `view07_team_workspace.py` lines 68-73 | `frontend/src/pages/View07TeamWorkspace.tsx` | TESTED | Huddle dynamics summary |

---

## 9. View 08: Historical Trend Comparison (A/B Testing)

| Feature / Component | Existing Location | React Component | Status | Verification Notes |
| :--- | :--- | :--- | :---: | :--- |
| Baseline & Experimental Window Selectors | `view08_historical_comparison.py` lines 21-35 | `frontend/src/pages/View08HistoricalComparison.tsx` | TESTED | Selectors for Period A and Period B |
| Comparative Metric Delta Table | `view08_historical_comparison.py` lines 38-90 | `frontend/src/components/common/DataTable.tsx` | TESTED | Metric Name, Period A, Period B, Delta, Relative %, p-Value, Significance |
| Statistically Verified Success Summary | `view08_historical_comparison.py` lines 92-100 | `frontend/src/pages/View08HistoricalComparison.tsx` | TESTED | Statistical verification callout |

---

## 10. View 09: Video Export Controls

| Feature / Component | Existing Location | React Component | Status | Verification Notes |
| :--- | :--- | :--- | :---: | :--- |
| Export Request Specification Form | `view09_video_export.py` lines 21-52 | `frontend/src/pages/View09VideoExport.tsx` | TESTED | Camera, duration slider (30-300 frames), DPO token, justification, submit button |
| Active Export Queue & Progress Monitor | `view09_video_export.py` lines 54-85 | `frontend/src/pages/View09VideoExport.tsx` | TESTED | Polls `GET /api/v1/export/status/{job_id}` |
| Download Redacted MP4 Link / Button | `view09_video_export.py` lines 76-80 | `frontend/src/pages/View09VideoExport.tsx` | TESTED | Direct download link to `/exports/{filename}` |
| Privacy & Compliance Assurance Cards | `view09_video_export.py` lines 86-95 | `frontend/src/pages/View09VideoExport.tsx` | TESTED | Edge video shredding, audit logging, expiring storage |

---

## 11. View 10: Data Quality & Model Health

| Feature / Component | Existing Location | React Component | Status | Verification Notes |
| :--- | :--- | :--- | :---: | :--- |
| Ingestion & Pipeline Performance Table | `view10_data_quality.py` lines 22-45 | `frontend/src/components/common/DataTable.tsx` | TESTED | Stream, State, FPS, Frames, Dropped Frames, Drop Ratio, Coverage %, Health Rating |
| Perception Reliability Metrics Cards | `view10_data_quality.py` lines 51-66 | `frontend/src/components/metrics/MetricCard.tsx` | TESTED | Tracking Continuity, Centroid Error, Modal Smoothing Window, Coverage Gate |
| Population Stability Index (PSI) Gauge | `view10_data_quality.py` lines 67-70 | `frontend/src/components/charts/PsiGaugeChart.tsx` | TESTED | Specialized 0.00-0.35 drift gauge |
| STRIDE Security Audit Log Table | `view10_data_quality.py` lines 72-82 | `frontend/src/components/common/DataTable.tsx` | TESTED | Immutable audit table populated from `GET /api/v1/system/audit-logs` |

---

## 12. Interactive Spatial Zone Editor

| Feature / Component | Existing Location | React Component | Status | Verification Notes |
| :--- | :--- | :--- | :---: | :--- |
| Currently Configured Zones Table | `zone_editor.py` lines 21-44 | `frontend/src/components/common/DataTable.tsx` | TESTED | Zone ID, Name, Type, Capacity, Camera, Vertices Count, Coordinates |
| Add / Update Zone Form & Validator | `zone_editor.py` lines 49-105 | `frontend/src/pages/ZoneEditor.tsx` | TESTED | Form fields with JSON coordinate validation ($[0.0, 1.0]$ bounds) |
| Delete Zone Selector & Action | `zone_editor.py` lines 106-120 | `frontend/src/pages/ZoneEditor.tsx` | TESTED | Deletion with confirmation |
