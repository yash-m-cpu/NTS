# WBPIS Technical Documentation Suite & Master Architecture Index

Welcome to the central technical documentation repository for the **CCTV Workplace Productivity & Workflow Intelligence System (WBPIS)**.

This index maps the complete architectural specifications, mathematical formulations, ethical privacy protocols, migration audit trails, and engineering blueprints that govern the platform.

---

## 🗂️ Documentation Suite Structure

```
c:\Users\DELL\Desktop\cctv\docs\
├── assets/                     # Visual assets, system screenshots, diagrams
├── implementation/             # 19 canonical engineering & algorithmic specifications (00 to 18)
├── migration/                  # React frontend migration audits, checklists, and API contracts
└── README.md                   # Central documentation navigation portal (this document)
```

---

## 📐 1. Implementation Specifications (`docs/implementation/`)

The implementation specification suite provides the complete architectural and mathematical specifications for the WBPIS perception, scoring, and telemetry engines:

| Document ID | Title & Scope | Primary Architectural Domain | Status |
| :---: | :--- | :--- | :---: |
| [**00**](file:///c:/Users/DELL/Desktop/cctv/docs/implementation/00_PROJECT_VISION_AND_SCOPE.md) | **Project Vision & Strategic Charter** | 4 Core Objectives, anti-surveillance covenant, failure modes | `FOUNDATIONAL` |
| [**01**](file:///c:/Users/DELL/Desktop/cctv/docs/implementation/01_REQUIREMENTS_AND_ETHICS.md) | **Requirements, Ethics & Compliance** | GDPR (Arts. 5, 6, 9, 35) & CCPA alignment, STRIDE threat model | `MANDATORY` |
| [**02**](file:///c:/Users/DELL/Desktop/cctv/docs/implementation/02_SYSTEM_ARCHITECTURE.md) | **System Architecture & Concurrency** | Multiprocessing concurrency, C4 container model, mailbox queues | `ARCHITECTURE` |
| [**03**](file:///c:/Users/DELL/Desktop/cctv/docs/implementation/03_VIDEO_INGESTION_AND_PREPROCESSING.md) | **Video Ingestion & Stream Decoding** | RTSP over TCP, GStreamer/NVDEC hardware decoding, mailbox buffers | `PERCEPTION` |
| [**04**](file:///c:/Users/DELL/Desktop/cctv/docs/implementation/04_PERSON_DETECTION_TRACKING_AND_IDS.md) | **Detection, Multi-Object Tracking & IDs** | YOLOv8/YOLOv4-tiny, ByteTrack, ground footprints, ephemeral rotating IDs | `PERCEPTION` |
| [**05**](file:///c:/Users/DELL/Desktop/cctv/docs/implementation/05_WORKSTATION_ZONES_AND_OCCUPANCY.md) | **Workstation Zones & Occupancy Engine** | Normalized polygon geometry, ray-casting point-in-polygon, 5-min debounce | `SPATIAL` |
| [**06**](file:///c:/Users/DELL/Desktop/cctv/docs/implementation/06_ACTIVITY_CLASSIFICATION_AND_TIME_DISTRIBUTION.md) | **Activity Classification & Posture Dynamics** | 7 observable postures (`ACT-01` to `ACT-07`), 75-frame modal filter | `BEHAVIORAL` |
| [**07**](file:///c:/Users/DELL/Desktop/cctv/docs/implementation/07_WORKFLOW_BOTTLENECK_METRICS.md) | **Workflow Bottleneck & Spatial Friction** | Interruption frequency, queue dwell times, transit churn, corridor exposure | `ANALYTICS` |
| [**08**](file:///c:/Users/DELL/Desktop/cctv/docs/implementation/08_PRODUCTIVITY_METRICS_AND_SCORING.md) | **Productivity Metrics & Scorecard Synthesis** | Decoupled scorecards (A, B, C, D), external deliverable webhooks | `SCORING` |
| [**09**](file:///c:/Users/DELL/Desktop/cctv/docs/implementation/09_SCORE_CALIBRATION_AND_CONFIDENCE.md) | **Score Calibration, Normalization & PSI** | P5/P95 percentile normalization, Population Stability Index (PSI) drift | `MATHEMATICS` |
| [**10**](file:///c:/Users/DELL/Desktop/cctv/docs/implementation/10_ANNOTATED_VIDEO_AND_EXPORT.md) | **Video Overlays & Privacy-Redacted Export** | Level-of-Detail (LOD) overlays, DPO token authorization, MP4 export | `EXPORT` |
| [**11**](file:///c:/Users/DELL/Desktop/cctv/docs/implementation/11_DATABASE_AND_DATA_RETENTION.md) | **Database Hypertables & Retention Rules** | SQLite 3 & TimescaleDB DDL, 72-hour video shredding, audit logging | `PERSISTENCE` |
| [**12**](file:///c:/Users/DELL/Desktop/cctv/docs/implementation/12_BACKEND_APIS_AND_INTEGRATION.md) | **Backend REST APIs & Live WebSockets** | OpenAPI/FastAPI contracts, live telemetry streams, RFC 7807 error formats | `API` |
| [**13**](file:///c:/Users/DELL/Desktop/cctv/docs/implementation/13_FRONTEND_DASHBOARD_AND_VISUALIZATIONS.md) | **Frontend Dashboard & Visual Architecture** | 11 operational views, ECharts gauges/Sankey, $k \ge 5$ anti-ranking policy | `FRONTEND` |
| [**14**](file:///c:/Users/DELL/Desktop/cctv/docs/implementation/14_REPORTS_AND_WORKPLACE_RECOMMENDATIONS.md) | **Workplace Layout Recommendations** | Deterministic rules REC-01 to REC-04, mandatory 7-point hypothesis schema | `DECISION` |
| [**15**](file:///c:/Users/DELL/Desktop/cctv/docs/implementation/15_TESTING_AND_VALIDATION.md) | **Testing Pyramid & Benchmark Framework** | 4-tier testing pyramid, legacy bug regressions (`BUG-01` to `BUG-03`, `SEC-01`) | `QUALITY` |
| [**16**](file:///c:/Users/DELL/Desktop/cctv/docs/implementation/16_SECURITY_PRIVACY_AND_ACCESS_CONTROL.md) | **Security, Privacy & RBAC Access Matrix** | 4-role RBAC matrix, credential isolation, immutable audit logs | `SECURITY` |
| [**17**](file:///c:/Users/DELL/Desktop/cctv/docs/implementation/17_DEPLOYMENT_AND_PERFORMANCE_OPTIMIZATION.md) | **Deployment, Docker & Hardware Acceleration** | Docker Compose stack, INT8 quantization, NVMe storage budgets | `DEVOPS` |
| [**18**](file:///c:/Users/DELL/Desktop/cctv/docs/implementation/18_IMPLEMENTATION_ROADMAP.md) | **Implementation Roadmap & Milestones** | 12 dependency-aware implementation phases, sprint estimates | `ROADMAP` |
| [**AUDIT**](file:///c:/Users/DELL/Desktop/cctv/docs/implementation/EXECUTION_AUDIT.md) | **Execution Audit & Pre-Migration Assessment** | Comprehensive codebase verification of historical prototypes | `HISTORICAL` |

---

## ⚛️ 2. Frontend Migration to React (`docs/migration/`)

These documents detail the transition from the legacy Streamlit prototype to the modern React 19 + TypeScript SPA:

1. [**`REACT_MIGRATION_AUDIT.md`**](file:///c:/Users/DELL/Desktop/cctv/docs/migration/REACT_MIGRATION_AUDIT.md):
   - Architectural strategy, component hierarchy, and design system decisions.
   - Preserves all computer-vision logic in Python while moving the user interface to React.
2. [**`FEATURE_PARITY_CHECKLIST.md`**](file:///c:/Users/DELL/Desktop/cctv/docs/migration/FEATURE_PARITY_CHECKLIST.md):
   - Comprehensive matrix tracking every UI control, chart, table, metric, and form across all 11 operational views.
   - **Verification Result**: 100% of features verified with status `TESTED`.
3. [**`REACT_API_CONTRACT.md`**](file:///c:/Users/DELL/Desktop/cctv/docs/migration/REACT_API_CONTRACT.md):
   - Strict RESTful and WebSocket contract defining request/response structures between the FastAPI backend and the React frontend.
4. [**`README_DOCUMENTATION_AUDIT.md`**](file:///c:/Users/DELL/Desktop/cctv/docs/migration/README_DOCUMENTATION_AUDIT.md):
   - Independent verification audit evaluating every claim made in `README.md` against the working codebase.

---

## 🖼️ 3. Visual Assets Directory (`docs/assets/`)

The [`docs/assets/`](file:///c:/Users/DELL/Desktop/cctv/docs/assets/) directory contains visual documentation assets:

- `system_hero_banner.png`: Primary system architecture overview banner.
- `view02_dial_gauge.png`: Workstation presence radial dial gauge.
- `view02_track_details_resolved.png`: Ephemeral track inspector with personal posture breakdown.
- `view03_workflow_efficiency.png`: Scorecard A dashboard with Person-Wise Spatial Friction Table and Sankey circulation.
- `view04_activity_distribution.png`: Scorecard B dashboard with Anti-Conflation Banner and 100% stacked posture shares.
- `view05_occupancy_table.png`: Scorecard C dashboard with continuous focus dwell times and debounced occupancy matrix.

---

## 🔍 Recommended Reading Paths

### For Facility Managers & Ergonomists
1. [Project Vision & Core Objectives](file:///c:/Users/DELL/Desktop/cctv/docs/implementation/00_PROJECT_VISION_AND_SCOPE.md)
2. [Occupancy & Debounce Modeling](file:///c:/Users/DELL/Desktop/cctv/docs/implementation/05_WORKSTATION_ZONES_AND_OCCUPANCY.md)
3. [Layout Recommendations Engine](file:///c:/Users/DELL/Desktop/cctv/docs/implementation/14_REPORTS_AND_WORKPLACE_RECOMMENDATIONS.md)

### For Data Protection Officers (DPO) & Compliance Auditors
1. [Requirements, Ethics & Legal Alignment](file:///c:/Users/DELL/Desktop/cctv/docs/implementation/01_REQUIREMENTS_AND_ETHICS.md)
2. [Data Retention & 72h Shredding Protocols](file:///c:/Users/DELL/Desktop/cctv/docs/implementation/11_DATABASE_AND_DATA_RETENTION.md)
3. [RBAC Matrix & Video Redaction Policies](file:///c:/Users/DELL/Desktop/cctv/docs/implementation/16_SECURITY_PRIVACY_AND_ACCESS_CONTROL.md)

### For Software & Computer Vision Engineers
1. [System Architecture & Concurrency Model](file:///c:/Users/DELL/Desktop/cctv/docs/implementation/02_SYSTEM_ARCHITECTURE.md)
2. [Perception, Tracking & Ephemeral IDs](file:///c:/Users/DELL/Desktop/cctv/docs/implementation/04_PERSON_DETECTION_TRACKING_AND_IDS.md)
3. [Backend API Contracts & WebSockets](file:///c:/Users/DELL/Desktop/cctv/docs/implementation/12_BACKEND_APIS_AND_INTEGRATION.md)
4. [React Frontend Parity Checklist](file:///c:/Users/DELL/Desktop/cctv/docs/migration/FEATURE_PARITY_CHECKLIST.md)
