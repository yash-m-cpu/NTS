# Comprehensive Project Audit: Skill Analysis vs. CCTV Workplace Intelligence

**Audit Date:** October 20, 2026  
**Auditor:** Full-Stack & Systems Integration Architecture  
**Target Environment:** `c:\PJT`  

---

## 1. Executive Summary

This audit assesses the state of two independent intelligent video analytics platforms located within the workspace:
1. **Skill Analysis / NTS Platform:** An enterprise multimodal meeting analysis engine combining computer vision, voice prosody, whisper speech-to-text, speaker attribution, listener analysis, behavioral skill scoring, and dynamic annotated video rendering.
2. **CCTV Workplace Productivity & Workflow Intelligence System (`Productivity-Analysis-main`):** An operational computer vision and spatial intelligence platform combining person detection, multi-person tracking, spatial zone analytics, 4-tier operational scorecards (A: Workflow Efficiency, B: Activity Distribution, C: Occupancy & Space Planning, D: Output Effectiveness), and interactive zone editing.

Both projects possess robust architectures but were built with different visual styling and backend contracts. This document establishes the factual foundation for unifying them into a single, cohesive web platform.

---

## 2. Skill Analysis (NTS) Platform Audit

### 2.1 Technical Stack
- **Frontend:** React 19, TypeScript 6, Vite 8, Tailwind CSS 4, Zustand (in-memory JWT security), TanStack React Query, Recharts.
- **Backend API:** FastAPI (Python 3.12), Pydantic v2, SQLAlchemy 2.0 (Asyncpg/Psycopg), Argon2 password hashing, PyJWT.
- **Asynchronous Processing:** Redis 7 + ARQ task queue with automated 12-stage cascade.
- **Computer Vision:** Node.js 20 child process running `@vladmandic/human` with TensorFlow.js (478-point face mesh, iris gaze, head pose, MoveNet body skeleton, emotion detection) and spatial X-anchor tracking.
- **Acoustic & Speech:** Praat/Parselmouth (pitch $F_0$, RMS energy), Faster-Whisper, Silero VAD, MediaPipe Face Mesh (lip MAR speaker attribution).
- **Database & Storage:** PostgreSQL 15 (relational entities, RLS multi-tenancy) + MinIO (S3-compatible object storage).

### 2.2 Frontend Route Inventory
- `/login` & `/register`: In-memory JWT authentication.
- `/dashboard`: Project portfolio listing.
- `/projects/:projectId`: Project details with meeting upload widget and job status pills.
- `/projects/:projectId/meetings/new`: Meeting initialization.
- `/meetings/:meetingId/analysis`: Flagship dashboard featuring:
  - Participant sidebar with quick report generation.
  - Visual Features tab (yaw, pitch, roll, gaze bearing, body keypoints, emotion distribution).
  - Speech & Language tab (speaking time, speech ratio %, turns, avg turn duration, transcript, Praat voice dynamics).
  - Interactions tab (participation comparison, pairwise exchange matrix, behavioral radar).
  - Annotated Video tab (H.264 video with skeleton & emotion overlays).
  - Report tab (LLM assessment with PDF export).

### 2.3 Operational Status
- **Backend & Worker:** Fully operational inside Docker containers (`pjt-postgres-1`, `pjt-redis-1`, `pjt-minio-1`, `pjt-worker-1`) and host Uvicorn (`127.0.0.1:8000`).
- **Data Integrity:** Active participant tracks (`person_0`, `person_1`) with verified speech turns, prosody contours, and interaction graph edges.

---

## 3. CCTV Workplace Intelligence Platform Audit

### 3.1 Technical Stack
- **Frontend:** React 19, TypeScript 6, Vite 8, Tailwind CSS 4, Lucide React, Axios, ECharts (`echarts-for-react`).
- **Backend API:** FastAPI (Python 3.12), Pydantic schemas, SQLAlchemy (SQLite / PostgreSQL), OpenCV DNN / YOLOv4-tiny.
- **Perception Pipeline:**
  - `src/perception/detector.py`: YOLOv4-tiny person detection.
  - `src/perception/tracker.py`: Centroid and Kalman-based trajectory tracking.
  - `src/perception/spatial.py`: Polygon zone point-in-polygon tests (desks, corridors, service queues).
  - `src/perception/activity.py`: Posture and velocity-based activity classification.
- **Analytics & Scorecards:**
  - `Scorecard A`: Workflow Efficiency (focus interruption frequency, corridor congestion ratio, service waiting ratio, zone transition rate).
  - `Scorecard B`: Activity & Ergonomic Time Distribution (active, seated, mobile, collaborative).
  - `Scorecard C`: Workstation Occupancy & Space Planning (occupancy rate, transitory absence grace debounce, rightsizing potential).
  - `Scorecard D`: Output Effectiveness (throughput attainment, first-pass quality rate, SLA adherence).
- **Export & Storage:** OpenCV video annotator (`src/export/overlay.py`, `video_exporter.py`), SQLite telemetry repository (`wbpis_telemetry.db`).

### 3.2 Frontend Route & View Inventory
- `View01LiveCctv`: Live CCTV stream monitoring with live telemetry metrics and active track overlays.
- `View02TrackDetails`: Individual track breakdown with dwell times and movement trajectories.
- `View03WorkflowEfficiency`: Scorecard A KPI cards, bottleneck radar, and congestion graphs.
- `View04ActivityDistribution`: Scorecard B stacked activity bars, posture metrics, and ergonomic distributions.
- `View05OccupancyPresence`: Scorecard C workstation utilization gauge, occupancy timeline, and desk vacancy tables.
- `View06OutputEffectiveness`: Scorecard D SLA attainment, quality yield, and throughput tracking.
- `View07TeamWorkspace`: Cross-departmental team workspace density and interaction clusters.
- `View08HistoricalComparison`: Trend analysis comparing daily/weekly operational performance.
- `View09VideoExport`: MP4 export job manager with custom overlay toggles.
- `View10DataQuality`: Camera FPS, detector latency, dropped frame rate, and sensor health diagnostics.
- `ZoneEditor`: Interactive canvas for defining and editing workstation and corridor polygon zones.

### 3.3 Visual Identity Discrepancy
- The existing CCTV frontend used a dark theme (`bg-slate-950 text-slate-100`) with dark blue accents, whereas Skill Analysis uses a clean, modern enterprise light theme (`bg-gray-50`, `bg-white`, `text-gray-900`, `text-blue-600` accents).
- In accordance with the Master Prompt, the Skill Analysis theme is the visual reference and design authority for the unified platform.

---

## 4. Integration Boundaries & Shared Surface

| Dimension | Skill Analysis | CCTV Workplace Intelligence | Unified Architecture |
|---|---|---|---|
| **Primary Domain** | Meeting behavioral analysis | Workplace spatial & operational analytics | Dual-branch enterprise suite |
| **Video Focus** | Faces, head pose, gaze, speech turns | Multi-person spatial movement, zones, occupancy | Maintained separately |
| **Backend Ports** | `8000` (FastAPI) | `8001` (FastAPI) | Dedicated ports with Vite proxy routing |
| **Data Persistence** | PostgreSQL + MinIO S3 | SQLite / Telemetry Repository | Separate datastores preserved |
| **Design System** | Clean light mode (Tailwind 4, Blue/Gray) | Dark mode (Slate 950) | Unified under Skill Analysis design system |
| **Frontend App** | React 19 + TypeScript + Vite | React 19 + TypeScript + Vite | Consolidated into single frontend (`frontend/src`) |
