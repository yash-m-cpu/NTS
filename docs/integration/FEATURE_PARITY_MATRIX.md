# Feature Parity & Integration Matrix

**Platform:** Unified Workplace & Skill Intelligence Platform  
**Date:** October 20, 2026  

---

## 1. Complete Feature Parity Matrix

| Feature ID | Category | Product Module | Feature Description | Implementation Status | Shared Component / Asset | Backend Dependency | Migration Status |
|---|---|---|---|---|---|---|---|
| **SA-01** | Navigation | Skill Analysis | User Login & Registration | Implemented | `ProtectedLayout`, `authStore` | FastAPI Auth (`/api/v1/auth`) | Preserved in Unified App |
| **SA-02** | Dashboard | Skill Analysis | Project Portfolio & Meeting List | Implemented | `Dashboard.tsx`, `ProjectDetail.tsx` | FastAPI Meetings (`/api/v1/meetings`) | Preserved in Unified App |
| **SA-03** | Ingestion | Skill Analysis | Video Upload with Presigned S3 PUT | Implemented | `VideoUploader.tsx` | FastAPI Media (`/api/v1/media`) | Preserved in Unified App |
| **SA-04** | Orchestration | Skill Analysis | Asynchronous Job Status Polling | Implemented | `JobStatusBadge.tsx`, `useJobPolling.ts` | Redis + ARQ + `/api/v1/jobs` | Preserved in Unified App |
| **SA-05** | Analytics | Skill Analysis | Visual Features (Head Pose, Gaze, Emotion) | Implemented | `FeatureChart.tsx` | `@vladmandic/human` + `/features` | Preserved in Unified App |
| **SA-06** | Analytics | Skill Analysis | Speech & Turn-Taking Dynamics | Implemented | `MeetingAnalysis.tsx` (Tab 2) | Faster-Whisper + Diarization | Preserved in Unified App |
| **SA-07** | Analytics | Skill Analysis | Voice Prosody ($F_0$, RMS Energy) | Implemented | `ProsodyChart.tsx` | Praat / Parselmouth + `/prosody` | Preserved in Unified App |
| **SA-08** | Analytics | Skill Analysis | Conversational Interaction Graph | Implemented | `MeetingAnalysis.tsx` (Tab 3) | `InteractionGraph` + `/interaction-graph` | Preserved in Unified App |
| **SA-09** | Analytics | Skill Analysis | Multimodal Participation Radar | Implemented | `ParticipationRadar.tsx` | Feature Fusion + BehavioralMetrics | Preserved in Unified App |
| **SA-10** | Video | Skill Analysis | Synchronized Annotated Video Playback | Implemented | `MeetingAnalysis.tsx` (Tab 5) | OpenCV + FFmpeg + MinIO S3 | Preserved in Unified App |
| **SA-11** | Reporting | Skill Analysis | LLM Assessment & PDF Export | Implemented | `MeetingAnalysis.tsx` (Tab 4) | LLM Service + Weasyprint | Preserved in Unified App |
| **CC-01** | Landing | Unified Platform | Product Selection Landing Page | **NEW (To Build)** | `LandingPage.tsx` | Health Checks (`/health`, SA health) | Target Step |
| **CC-02** | Video | CCTV Analytics | Live Stream Monitoring & Telemetry | Implemented | `LiveVideoPlayer.tsx` | CCTV FastAPI (`/api/v1/stream`) | Migrate into Unified App |
| **CC-03** | Perception | CCTV Analytics | Multi-Person Tracking & Dwell Times | Implemented | `View02TrackDetails.tsx` | YOLOv4 + Centroid Tracker | Migrate into Unified App |
| **CC-04** | Analytics | CCTV Analytics | Scorecard A: Workflow Bottlenecks | Implemented | `View03WorkflowEfficiency.tsx` | ScorecardEngine (Corridors/Queues) | Migrate into Unified App |
| **CC-05** | Analytics | CCTV Analytics | Scorecard B: Ergonomic Activity Split | Implemented | `View04ActivityDistribution.tsx` | Activity Classifier (Seated/Mobile) | Migrate into Unified App |
| **CC-06** | Analytics | CCTV Analytics | Scorecard C: Workstation Occupancy | Implemented | `View05OccupancyPresence.tsx` | Spatial Engine + Debounce Grace | Migrate into Unified App |
| **CC-07** | Analytics | CCTV Analytics | Scorecard D: Output Effectiveness & SLA | Implemented | `View06OutputEffectiveness.tsx` | Throughput & Quality Calculator | Migrate into Unified App |
| **CC-08** | Analytics | CCTV Analytics | Team Workspace Interaction Clusters | Implemented | `View07TeamWorkspace.tsx` | Spatial Proximity Analyzer | Migrate into Unified App |
| **CC-09** | Analytics | CCTV Analytics | Historical Longitudinal Trends | Implemented | `View08HistoricalComparison.tsx` | TelemetryRepository History | Migrate into Unified App |
| **CC-10** | Export | CCTV Analytics | Annotated CCTV Video MP4 Export | Implemented | `View09VideoExport.tsx` | `VideoExportJob` + Static `/exports` | Migrate into Unified App |
| **CC-11** | Diagnostics | CCTV Analytics | Data Quality & Model Diagnostics | Implemented | `View10DataQuality.tsx` | Ingestion & Pipeline Health | Migrate into Unified App |
| **CC-12** | Configuration | CCTV Analytics | Interactive Polygon Zone Editor | Implemented | `ZoneEditor.tsx` | `/api/v1/zones` CRUD | Migrate into Unified App |

---

## 2. Shared Component & Design System Alignment

| Component | Skill Analysis Reference | CCTV Original | Unified Design Action |
|---|---|---|---|
| **App Shell** | `ProtectedLayout` (White header, light gray body) | `Layout` (Slate 950 dark) | Unify with Skill Analysis light layout |
| **Navigation** | Top header + Breadcrumbs | Dark Sidebar (11 views) | Skill Analysis header + Clean light sidebar for CCTV |
| **Cards** | `bg-white border border-gray-200 rounded-lg p-6 shadow-sm` | `bg-slate-900/80 border-slate-800` | Standardize to white card style |
| **Buttons** | `bg-blue-600 hover:bg-blue-700 text-white rounded font-medium` | `bg-sky-600 rounded-lg` | Standardize to Skill Analysis primary blue |
| **Badges** | Tailwind pills (`bg-blue-50 text-blue-700 border-blue-200`) | Dark pills (`bg-rose-500/20 text-rose-400`) | Standardize to soft light badges |
| **Charts** | Recharts (ResponsiveContainer, clean tooltips) | ECharts (`echarts-for-react`) | Keep ECharts for CCTV, re-theme to light palette |
| **API Client** | Custom fetch wrapper with refresh loop (`apiClient.ts`) | Axios instance (`api.ts`) | Keep separate API clients: `cctvApi.ts` & `skillAnalysisApi.ts` |
