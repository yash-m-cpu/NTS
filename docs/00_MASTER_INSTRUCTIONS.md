# 00 — Master Instructions (Project Constitution)

> **Status:** Binding. All future implementation work — code, documentation, data pipelines, model training, infrastructure — must comply with this document.
> Any deviation must be explicitly documented (what changed, why, and where) in `docs/decisions/`.

---

## 1. Project Name

**Video Motion Analysis for Non-Technical Skills (NTS) Reports**

## 2. Project Purpose

Build an AI-driven system that analyzes meeting video and audio to extract observable behavioral features and generate reproducible Non-Technical Skills (NTS) reports.

The system supports three ingestion modes (mode 3 is future work):

1. **Uploaded video/audio files** — MP4, AVI, and common browser-supported formats.
2. **Live camera / microphone input** — webcam, browser camera, live audio, with future support for real-time meeting platforms.
3. **Real-time meeting integrations (future)** — Zoom, Microsoft Teams, using architecture/patterns adapted from [`realtime-meeting-intelligence`](https://github.com/Umer-2612/realtime-meeting-intelligence).

## 3. Vision Computer-Vision Base

Use [`vladmandic/human`](https://github.com/vladmandic/human) as a **pretrained CV feature-extraction layer**, never as the final NTS prediction model.

Relevant Human capabilities:

- body pose
- face detection
- face landmarks
- iris analysis
- gaze-related information
- emotion prediction
- hand tracking
- gesture recognition
- head/face rotation
- body segmentation (where useful)

**The final NTS scoring models must be developed by this project.** Human never outputs an NTS score, a leadership score, or any behavioral judgment — it outputs raw geometric/probabilistic signals only.

## 4. Core Pipeline

```
INPUT
  ↓
INGESTION
  ↓
VIDEO/AUDIO PROCESSING
  ↓
COMPUTER VISION FEATURE EXTRACTION
  ↓
AUDIO/SPEECH FEATURE EXTRACTION
  ↓
TEMPORAL FEATURE AGGREGATION
  ↓
MULTIMODAL FEATURE FUSION
  ↓
NTS SCORING
  ↓
BEHAVIORAL ARCHETYPING
  ↓
NARRATIVE GENERATION
  ↓
DASHBOARD / REPORT
```

## 5. Prohibited Claims

The system must **never** assert unsupported causal or evaluative claims, including but not limited to:

- a smile automatically means leadership
- looking at the camera automatically means confidence
- speaking more automatically means leadership
- a specific gesture automatically means influence

Features are **observable behavioral signals only**. NTS scores are **model outputs** and must always be clearly and visibly distinguished from raw observations, both in the data model and in every user-facing surface (dashboard, report, export, API response).

## 6. Target NTS Dimensions

The current project targets:

1. Leadership
2. Communication
3. Teamwork
4. Influence
5. Engagement / Resilience

**Dimensions must be configurable.** The source presentation deck contains multiple candidate dimension sets. No business logic may be hard-coded around one fixed dimension list — dimensions, their definitions, their input feature sets, and their scoring weights must be defined in configuration/data, not in code.

## 7. Modeling Principle — The Four Layers

Every implementation must keep these four layers distinct in the data model, the code, the API contracts, and the UI:

| Layer | Definition | Example |
|---|---|---|
| **Observed Features** | Raw signals produced directly by CV/audio models, timestamped, per-frame or per-segment | gaze direction, body pose, facial expression probabilities, speaking duration |
| **Derived Behavioral Metrics** | Deterministic aggregations/transformations of observed features over a time window | speaking-time ratio, turn frequency, gaze stability, movement variability |
| **NTS Scores** | Outputs of a trained/calibrated scoring model, with confidence and provenance | leadership = 78, communication = 72 |
| **LLM-Generated Narrative** | Natural-language text generated strictly from the structured outputs above | "Participant demonstrated relatively high participation..." |

**The narrative must never invent measurements that do not exist.** The narrative-generation layer receives only structured JSON (features, metrics, scores, confidence) — never raw video/audio — and is prompt-constrained to describe only what is present in that structured input.

## 8. Datasets

| Dataset | Role |
|---|---|
| **AMI Meeting Corpus** | Primary — meeting-level multimodal analysis |
| **MPIIGroupInteraction** | Secondary — behavior-related feature learning/validation |
| **ELEA** | Secondary — used where leadership/emergent-leadership supervision is available |
| **NoXi** | Secondary — interaction, gesture, engagement, conversational behavior |
| **First Impressions V2** | Auxiliary — not the main meeting dataset |

## 9. Reference Repositories

| Repository | Role |
|---|---|
| [`vladmandic/human`](https://github.com/vladmandic/human) | CV feature-extraction base |
| [`Umer-2612/realtime-meeting-intelligence`](https://github.com/Umer-2612/realtime-meeting-intelligence) | Architecture/pattern reference for future Zoom/Teams bot integration |

**Do not blindly merge either repository into this project.** Reuse concepts and components where appropriate; do not vendor them wholesale or assume their exact tech stack (e.g. the reference meeting-bot repo is a Windows/.NET + C++ + Python polyglot monorepo — this project's own meeting-bot layer, when built, may adopt the same *pattern* of bot-captures-media → stream-processor without adopting the same languages).

## 10. Architectural Principles

1. Modular architecture.
2. Python backend for orchestration, ML, and data processing.
3. JavaScript/TypeScript frontend for live video and browser camera handling.
4. Human may run in the frontend/browser when that is more efficient for real-time inference.
5. Backend handles heavy/offline analysis.
6. Use asynchronous job processing for long videos.
7. Never block HTTP requests while processing an hour-long video.
8. Store extracted features, not raw video, by default.
9. Privacy-first architecture.
10. Raw video retention must be configurable.
11. Every ML result must have provenance.
12. Every feature must have timestamps.
13. Every participant must have a stable internal anonymous ID.
14. Do not store unnecessary biometric identity information.
15. Never implement face recognition for identifying employees unless explicitly required.
16. Separate ingestion, feature extraction, scoring, and reporting.
17. All services must be independently testable.

## 11. Required Input Modes

**A. File Mode** — user uploads video, optional audio, optional transcript.
**B. Live Mode** — user provides browser camera and microphone.
**C. Meeting Mode (future)** — Zoom, Teams.

The system must use a **common internal event/stream representation** so downstream analysis never needs to know where the media originated.

## 12. Expected Output (per analyzed meeting)

- meeting metadata
- participants
- processing status
- extracted features
- aggregate behavioral metrics
- NTS scores
- confidence/quality indicators
- behavioral archetype
- narrative report
- visualizations

## 13. Expected Visualizations

- NTS radar chart
- participant comparison
- speaking-time distribution
- speaking-turn timeline
- gaze/attention timeline
- engagement timeline
- movement/activity timeline
- team interaction graph
- behavioral archetype quadrant
- meeting timeline

## 14. Quality Requirements

Typed APIs, structured logging, error handling, retries, idempotent jobs, validation, unit tests, integration tests, clear configuration, environment variables, Docker support, reproducible local setup.

## 15. Explicit Non-Goals / Prohibitions

Do **not**:

- create fake ML accuracy numbers
- invent labels
- pretend Human predicts leadership
- hard-code dataset-specific assumptions into generic services
- couple frontend directly to the database
- expose secrets to the frontend
- process long videos synchronously through API requests
- store raw video indefinitely
- use LLM output as ground truth
- use personality/behavior inference beyond what the available labels support

## 16. Feature Implementation Checklist

Before implementing any feature, determine:

1. Which layer owns it?
2. What input does it consume?
3. What output does it produce?
4. How is it persisted?
5. How is it tested?
6. How is it observed/debugged?

## 17. Required Reading Order

Before writing code, read, in order:

1. PRD — `docs/01_PRD.md`
2. Architecture — `docs/02_ARCHITECTURE.md`
3. Database Schema
4. API/Auth
5. Implementation Plan
6. Dataset/Features
7. File Structure

**Never violate these documents without explicitly documenting the reason.**
