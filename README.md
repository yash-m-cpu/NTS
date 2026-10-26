# Non-Technical Skills (NTS) Meeting Intelligence & CCTV Workplace Productivity Platform

A unified, multi-modal artificial intelligence platform combining **Meeting Behavioral Intelligence (Non-Technical Skills Quantification)** with **CCTV Workplace Spatial & Workflow Analytics**.

---

## 🌟 Key Features

### 1. Multi-Modal Meeting Intelligence (NTS)
- **Computer Vision Perception:** Face detection, 468-point 3D facial landmark mesh, Perspective-n-Point (PnP) head pose estimation (yaw, pitch, roll), gaze tracking, and 7-class emotion classification using `@vladmandic/human` and TensorFlow.js.
- **Zero-Swap Spatial Anchor Tracking:** Seated multi-person spatial anchor algorithm that eliminates participant identity swapping during collaborative meetings.
- **Audio & Speech Recognition:** Accelerated transcription via Faster-Whisper (CTranslate2) with word-level timestamps.
- **Visual-Acoustic Diarization Fusion:** Novel Mouth Aperture Ratio (MAR) formulation to resolve overlapping speech and heated debates.
- **5-Dimensional NTS Scoring:** Quantifies Communication, Leadership, Engagement, Collaboration, and Confidence using trained Random Forest regressors.
- **Behavioral Archetypes:** Identifies participant archetypes (*Presenter*, *Facilitator*, *Collaborator*, *Observer*) and generates actionable feedback reports with downloadable PDFs.

### 2. CCTV Workplace Productivity & Spatial Analytics
- **Live Annotated Video Streaming:** Real-time MJPEG video pipeline featuring bounding boxes, spatial coordinates, and zone state overlays.
- **Multi-Person Tracking:** DeepSORT-based tracking with rotating HMAC salts for privacy-preserving telemetry.
- **Polygon Zone Geometry:** Interactive zone editor supporting workstation desks, meeting clusters, and transit corridors via Ray-Casting Point-in-Polygon (PIP) testing.
- **Workflow & Efficiency Scorecards:** Quantitative computation of Workstation Occupancy Rate (WOR), transit velocities, interruption frequencies, and corridor bottleneck detection.

### 3. Unified Frontend Experience
- Built with **React 18**, **TypeScript**, **Vite**, **Tailwind CSS**, and **Zustand**.
- Unified product-selection landing page at `/` allowing seamless navigation between CCTV Analytics and Skill Analysis modules.
- Dynamic data visualizations powered by **Recharts** (radar charts, participation timelines, turn-taking heatmaps, and metric scorecards).

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│             PRESENTATION LAYER (React 18 + TS)              │
│       Shared Theme │ Unified Landing │ Recharts UI          │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTPS / Reverse Proxy
┌──────────────────────────────▼──────────────────────────────┐
│                    API GATEWAY & ROUTING                    │
│   • Skill Analysis API (port 8000) - FastAPI + RLS          │
│   • CCTV Analytics API (port 8001) - FastAPI + Pipeline     │
└──────────────┬───────────────────────────────┬──────────────┘
               │                               │
        ┌──────▼──────┐                 ┌──────▼──────┐
        │ PostgreSQL  │                 │   SQLite    │
        │   15 + RLS  │                 │  Telemetry  │
        └──────┬──────┘                 └─────────────┘
               │
        ┌──────▼──────┐                 ┌─────────────┐
        │ Redis + ARQ │ ──────────────► │  MinIO S3   │
        │ Task Broker │                 │   Storage   │
        └──────┬──────┘                 └─────────────┘
               │
        ┌──────▼────────────────────────────────┐
        │       ASYNCHRONOUS ML WORKERS         │
        │  • CV Worker (Node.js + Human.js)     │
        │  • STT Worker (Faster-Whisper)        │
        │  • Fusion & NTS Scorer (Scikit-Learn) │
        └───────────────────────────────────────┘
```

---

## 🚀 Quick Start Guide

### Prerequisites
- [Docker](https://www.docker.com/) & Docker Compose
- [Python 3.12](https://www.python.org/)
- [Node.js 20+](https://nodejs.org/)

### 1. Clone the Repository
```bash
git clone https://github.com/yash-m-cpu/NTS.git
cd NTS
```

### 2. Start Core Infrastructure (Docker)
```bash
# Start PostgreSQL, Redis, MinIO, and the CV Worker
docker compose -f docker-compose.dev.yml up -d
```

### 3. Launch Skill Analysis Backend (Port 8000)
```bash
cd backend
cp .env.example .env   # configure environment variables if needed
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 4. Launch CCTV Analytics Backend (Port 8001)
```bash
cd Productivity-Analysis-main
python -m uvicorn src.backend.main:app --host 127.0.0.1 --port 8001 --reload
```

### 5. Launch Unified Frontend (Port 5173)
```bash
cd frontend
npm install
npm run dev
```

Visit **`http://localhost:5173`** in your browser.

---

## 📁 Repository Structure

```
.
├── backend/                    # FastAPI Skill Analysis backend & ORM models
│   ├── app/
│   │   ├── api/v1/             # REST API routers (auth, meetings, media, scores)
│   │   ├── models/             # SQLAlchemy relational database models
│   │   ├── services/           # Storage, STT, fusion, and scoring services
│   │   └── workers/            # ARQ background task workers
│   └── scripts/                # Database migration and worker entry points
├── frontend/                   # React 18 TypeScript SPA
│   ├── src/
│   │   ├── features/cctv/      # CCTV Analytics pages, views, and components
│   │   ├── routes/             # Landing page, Meeting analysis, and dashboards
│   │   └── services/           # Axios API clients for both backends
├── Productivity-Analysis-main/ # CCTV Workplace Intelligence engine & perception pipeline
│   └── src/
│       ├── analytics/          # Scorecard engines and bottleneck metrics
│       ├── backend/            # FastAPI CCTV server and MJPEG streaming
│       └── perception/         # YOLOv8 detection and DeepSORT tracking
├── external/                   # External computer vision models & dependencies
├── docs/                       # Architecture, PRD, and integration documentation
└── docker-compose.dev.yml      # Multi-container orchestration (PostgreSQL, Redis, MinIO)
```

---

## 🔒 Security & Privacy Covenants
- **Zero Biometric Persistence:** Raw facial geometry vectors and facial recognition embeddings are discarded after feature window aggregation.
- **Pseudonymization:** Real-time spatial tracking assigns anonymized IDs with rotating 24-hour HMAC salts.
- **Row-Level Security (RLS):** All meeting data and analytics are partitioned strictly by organization ID using PostgreSQL RLS policies.

---

## 👥 Authors & Academic Information

* **Institution:** Vellore Institute of Technology, Chennai
* **School:** School of Computer Science and Engineering (SCSE)
* **Program:** Bachelor of Technology in Computer Science and Engineering (CSE Core)
* **Team Members:**
  - **Yash Muthal** (23BCE5002)
  - **Mohd. Maaz Alam** (23BAI1426)
  - **Nikhil Kumar** (23BAI1264)
* **Project Guide:** Dr. Dhanush R, Assistant Professor, SCSE, VIT Chennai
* **Head of Department:** Dr. Prassanna J, Professor & HOD, SCSE, VIT Chennai
