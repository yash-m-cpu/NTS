# 01 — Product Requirements Document (PRD)

**Project:** Video Motion Analysis for Non-Technical Skills (NTS) Reports
**Status:** Draft v1.0 — governed by `00_MASTER_INSTRUCTIONS.md`
**Objective:** Build an AI-driven system that analyzes meeting video/audio and produces reproducible behavioral and Non-Technical Skills reports.

---

## 1. Executive Summary

Organizations increasingly recognize that "non-technical skills" — leadership, communication, teamwork, influence, and engagement/resilience — are as important to team and business outcomes as technical competence. Today these skills are almost always assessed through subjective, infrequent, and inconsistent means: manager impressions, 360 surveys, or ad-hoc feedback.

This project builds a system that observes recorded or live meeting video and audio, extracts objective, timestamped behavioral signals using computer-vision and speech-processing models, aggregates those signals into interpretable metrics, and applies purpose-built, dataset-trained scoring models to produce **NTS scores** — always alongside the observed evidence that supports them, and always accompanied by confidence indicators.

The system is explicitly **not** a personality-inference or lie-detection tool, and it does not claim that any single visual or audio cue "means" a particular trait. It is a decision-support tool: it surfaces consistent, reproducible, evidence-linked behavioral observations so that human reviewers (HR, managers, researchers) can make better-informed, less biased judgments — never a replacement for human judgment.

The system reuses [`vladmandic/human`](https://github.com/vladmandic/human) as a pretrained computer-vision feature extractor (pose, face, gaze, emotion, hands, gestures) and takes architectural inspiration from [`Umer-2612/realtime-meeting-intelligence`](https://github.com/Umer-2612/realtime-meeting-intelligence) for the future live meeting-bot ingestion pattern (bot joins call → captures raw media → streams to a Python analytics backend). Neither repository is merged wholesale; both are used as references, and all NTS scoring logic is built and owned by this project.

---

## 2. Problem Statement

### 2.1 Subjective employee reviews
Behavioral competencies are typically rated once or twice a year by a manager who saw a small, non-random sample of the employee's behavior (a handful of meetings, under observation bias). Ratings vary by manager, by mood, by recency, and by the rater's own communication style preferences.

### 2.2 Lack of consistent behavioral measurement
There is no standard instrument that measures the same behavioral construct (e.g., "turn-taking balance," "engagement") the same way, on the same scale, across every meeting and every employee. Without a consistent measurement, comparisons over time or across teams are unreliable.

### 2.3 Limitations of manager-only observation
A manager cannot attend to every non-verbal and paraverbal cue simultaneously in a live meeting (who spoke, for how long, who was interrupted, who looked engaged, whose posture changed). Manager attention itself is a scarce, biased resource, and managers may unconsciously favor employees who are more similar to themselves.

### 2.4 Need for objective behavioral signals
An objective, always-on, or consistently-sampled measurement layer — one that records *what was observed* (gaze direction, speaking time, pose, prosody) separately from *what it means* — gives organizations a way to triangulate manager judgment with reproducible evidence, surface blind spots, and track change over time.

### 2.5 Risks of overclaiming behavioral inference
This same capability is dangerous if misused. Computer vision and speech models can produce statistically confident-looking outputs that are **not** valid measures of internal states like confidence, honesty, or leadership potential. Overclaiming (e.g., "this person smiled 40% of the time therefore they are a strong leader") is:

- **scientifically unsupported** — the underlying academic literature on facial-expression-to-trait inference is contested and culture-dependent;
- **ethically and legally risky** — using unvalidated behavioral inference in employment decisions can be discriminatory and, in some jurisdictions, is regulated or prohibited (e.g., restrictions on automated video-based hiring assessments and biometric inference);
- **damaging to trust** — employees who learn that a black-box model scored their "leadership" from webcam footage will reasonably distrust the system.

The product design directly addresses this risk by (a) always separating observation from inference, (b) always attaching confidence and provenance to every derived score, (c) requiring human review before any score is used in a formal evaluation process, and (d) refusing to support use cases such as covert surveillance, emotion-based hiring screens, or identity-based biometric profiling.

---

## 3. Product Vision

The product provides an end-to-end pipeline:

- **Video/audio ingestion** — uploaded files or live camera/microphone, normalized into a common internal stream representation.
- **CV feature extraction** — pose, face, gaze, emotion, hands, gestures via the Human library.
- **Speech/interaction analysis** — transcription, diarization, speaking turns, latency, interruptions.
- **Multimodal feature fusion** — a single per-participant, per-time-window feature representation combining video and audio signals.
- **NTS scoring** — calibrated, explainable scores per configurable dimension.
- **Behavioral archetypes** — cluster-based behavioral "profiles" derived from the same feature space, not from the NTS scores themselves.
- **Automated narrative reports** — LLM-generated summaries constrained to the structured outputs.
- **Interactive dashboard** — timelines, comparisons, radar charts, and exportable reports.

The long-term vision extends ingestion to live Zoom/Teams meetings via a meeting-bot architecture, without changing anything downstream of ingestion.

---

## 4. Target Users

| User | Type | Description |
|---|---|---|
| **HR / People Managers** | Production | Review individual and team NTS reports as one input into development conversations and talent programs. |
| **Team Leads** | Production | Review their own team's meeting dynamics and participation balance to improve facilitation. |
| **Project Managers** | Production | Monitor team engagement/collaboration trends across a program of recurring meetings. |
| **Administrators** | Production | Manage users, org configuration, dimension definitions, retention policy, and access control. |
| **Researchers** | Research | Interrogate raw features, model internals, dataset performance, and validation metrics; not typically consumers of a single employee's report. |
| **Developers / Data Scientists** | Research | Build, retrain, and evaluate CV/audio/fusion/scoring models; work with the dataset layer directly. |

**Production vs. research distinction:** Production users interact only with **aggregated, reviewed, access-controlled outputs** (reports, dashboards) and never see raw video/audio identifiers beyond what governance policy allows. Research users interact with **de-identified or consented raw features and model artifacts** in a separate research workspace, governed by a distinct data-access policy, and never with an individual's live production report unless that individual has separately consented to research use.

---

## 5. User Stories

### 5.1 File Analysis

- As an HR manager, I want to **upload a recorded meeting video** so that the system can analyze it without me needing any special equipment.
- As an HR manager, I want to **monitor processing status** (queued/running/completed/failed) so I know when a report will be ready.
- As an HR manager, I want to **view the generated NTS report** for a meeting so I can review team members' behavioral summaries.
- As a team lead, I want to **inspect the meeting timeline** (speaking turns, gaze, engagement) so I can see exactly when and why a metric changed.
- As a team lead, I want to **inspect a specific participant's extracted features** so I can understand what evidence underlies their metrics, not just the final number.

### 5.2 Live Analysis

- As a team lead, I want to **enable my camera and microphone** before a live session so the system can begin capturing behavioral signals.
- As a team lead, I want to **start a live analysis session** so that features are extracted in near-real-time during the meeting.
- As a participant, I want to **see live behavioral indicators** (e.g., my own speaking-time share) so I can self-adjust during the meeting, without seeing a live "score" framed as a judgment.
- As a team lead, I want to **stop a live session** cleanly so partial data is preserved and no orphaned resources remain.
- As a team lead, I want the system to **generate a final report** automatically once a live session ends, using the same pipeline as file-based analysis.

### 5.3 Management

- As an HR manager, I want to **compare participants** within the same meeting on the same NTS dimensions so I can see relative patterns, with the same caveats and confidence intervals shown for each.
- As a team lead, I want to **inspect team dynamics** (interaction graph, turn balance) to identify who dominates or is excluded from discussion.
- As an HR manager, I want to **view an individual's NTS profile over multiple meetings** (radar chart, trend) so I can see development over time rather than a single snapshot.
- As an administrator, I want to **export reports** (PDF/CSV/JSON) so they can be shared through existing HR workflows.

### 5.4 Research

- As a data scientist, I want to **inspect extracted raw features** for a sample of meetings so I can validate the CV/audio pipeline against ground truth.
- As a data scientist, I want to **compare model versions** (e.g., old vs. new NTS scoring model) on the same held-out data so I can decide whether to promote a new model.
- As a researcher, I want to **inspect confidence/uncertainty** for every score so I understand when the model is guessing versus confident.
- As a researcher, I want to **evaluate predictions against dataset labels** (e.g., ELEA emergent-leadership labels) so I can quantify model accuracy honestly, without inflating reported metrics.

---

## 6. Functional Requirements

| Area | Requirement |
|---|---|
| **Authentication** | Support authenticated access (email/password and/or SSO) with role-based access (admin, manager, researcher, participant). |
| **Meeting creation** | Users can create a "meeting" record (metadata: title, date, participants, mode) before or alongside upload/live session start. |
| **Upload** | Users can upload video files (MP4, AVI, and other browser-supported formats) with client- and server-side validation (format, size, duration limits). |
| **Validation** | Reject or flag corrupted files, unsupported codecs, missing audio tracks, and excessively short/long durations before queuing expensive processing. |
| **Processing jobs** | All heavy processing (CV, audio, fusion, scoring, narrative) runs as asynchronous, resumable, idempotent jobs with visible status. |
| **Participant detection** | Detect distinct people present in the video (bounding boxes / face tracks) and assign each a session-scoped anonymous participant ID. |
| **Participant tracking** | Maintain consistent participant identity across frames/segments within one meeting (re-identification within-session, not cross-session facial recognition by default). |
| **Feature extraction (CV)** | Extract pose, face, gaze, emotion, hand, and gesture signals per participant per frame/segment using the Human library. |
| **Audio processing** | Extract speech-to-text transcript, speaker diarization, timestamps, turns, latency, interruptions. |
| **Feature aggregation** | Aggregate raw per-frame/per-segment features into derived, time-windowed behavioral metrics. |
| **NTS scoring** | Apply a configurable, versioned scoring model to derived metrics to produce per-dimension scores with confidence. |
| **Archetyping** | Cluster participants' feature vectors into a configurable set of behavioral archetypes; expose archetype label + nearest-cluster distance. |
| **Narrative generation** | Generate natural-language summary strictly from structured features/metrics/scores; never from raw video/audio directly. |
| **Visualization** | Render the visualizations listed in `00_MASTER_INSTRUCTIONS.md` §13 in an interactive dashboard. |
| **Report export** | Export a completed report as PDF, CSV (metrics/scores), and JSON (full structured payload). |

---

## 7. Non-Functional Requirements

| Category | Requirement |
|---|---|
| **Performance** | A 60-minute uploaded meeting should complete full processing within a bounded, monitored SLA (target: well under real-time multiple, e.g., ≤ 2× video duration on reference hardware); live mode should surface indicators with sub-few-second latency. |
| **Scalability** | Horizontally scale processing workers independently of the API tier; support many concurrent jobs via a queue. |
| **Reliability** | Jobs are retryable and idempotent; partial failures (e.g., audio pipeline fails but CV succeeds) degrade gracefully rather than losing all results. |
| **Privacy** | Raw video is not retained by default; retention is configurable per organization; features are pseudonymous by default. |
| **Security** | Authenticated, authorized (RBAC) access to all data; encrypted storage and transport; secrets never exposed to the frontend. |
| **Observability** | Structured logs, metrics, and traces for every pipeline stage; job status and failure reasons are visible to operators. |
| **Reproducibility** | The same input, run through the same pinned model/config versions, produces the same output; every result records the model/config versions used. |
| **Explainability** | Every NTS score can be traced back to the derived metrics and, from there, to the observed features that produced it. |
| **Maintainability** | Ingestion, feature extraction, scoring, and reporting are independently deployable, independently testable services with typed contracts between them. |

---

## 8. Input Modes

**A. Uploaded video** — user uploads a file (MP4, AVI, common browser formats), optionally with a separate audio file or transcript; processed asynchronously.

**B. Live webcam** — user grants camera/microphone access in-browser; Human may run client-side for immediate visual feedback while raw/derived data streams to the backend for full-fidelity processing and eventual report generation.

**C. Future Zoom/Teams integration** — a meeting bot (pattern adapted from `realtime-meeting-intelligence`) joins the call, captures each participant's raw audio/video stream, and forwards it into the same common internal stream representation used by modes A and B, so the downstream pipeline (feature extraction → scoring → reporting) requires no changes.

---

## 9. Output Contract

A completed analysis produces a single structured result containing, at minimum:

```
Meeting
├── metadata (id, title, date, duration, mode, org, created_by, retention_policy)
├── participants[] (anonymous_id, tracks, optional linked identity if explicitly enabled)
├── processing_status (per-stage: queued | running | partial | completed | failed | cancelled)
├── observed_features[] (participant_id, timestamp/window, modality, feature_type, value, model_version, confidence)
├── derived_metrics[] (participant_id, window, metric_type, value, computation_version)
├── nts_scores[] (participant_id, dimension, score, confidence_interval, model_version, contributing_metrics[])
├── archetype (participant_id, archetype_label, cluster_distance, model_version)
├── narrative (participant_id or meeting-level, text, generated_from_result_version, model_used)
└── visualizations (pre-computed chart data referencing the above, not independently sourced)
```

Every leaf record carries **timestamps** and **provenance** (which model/version produced it), per Master Instructions §10.

---

## 10. NTS Dimensions

Default configurable dimension set:

1. **Leadership**
2. **Communication**
3. **Teamwork**
4. **Influence**
5. **Engagement / Resilience**

Dimensions, their human-readable definitions, and their mapping to derived metrics are defined in configuration (not code), because the source presentation material contains multiple candidate dimension sets and different organizations may want different subsets or definitions.

**NTS scores are model outputs, not direct measurements.** Every score is presented with: the model/version that produced it, a confidence indicator, and a link to the contributing derived metrics and observed features. UI and reports must never present a score as a fact about the person's character or ability — only as "the model's estimate, based on this evidence, with this confidence."

---

## 11. Feature Categories

| Category | Examples |
|---|---|
| Pose | body keypoints, posture changes, orientation |
| Gaze | gaze direction, gaze stability, eye contact proxy (camera-facing ratio) |
| Facial affect | emotion probability distributions (not a single "true emotion" label) |
| Head orientation | head pose/rotation over time |
| Hand/gesture | hand presence, tracked gestures, gesture frequency |
| Movement | overall movement/activity level, variability |
| Speaking turns | turn count, turn order, turn-taking pattern |
| Speaking time | total and share of speaking time per participant |
| Response latency | time between end of one turn and start of the next by another speaker |
| Interruptions | overlapping speech events, who interrupted whom |
| Turn balance | distribution of speaking time/turns across participants |
| Participation | presence/absence of contribution over time windows |
| Engagement | composite of gaze, movement, and vocal-activity signals over time |

---

## 12. Model Requirements

| Layer | Requirement |
|---|---|
| **Pretrained CV models** | Human library models (pose, face, iris/gaze, emotion, hand, gesture) used as-is or fine-tuned only where the license and project scope allow; never retrained to output NTS labels directly. |
| **Speech models** | Off-the-shelf or fine-tuned ASR + diarization models; must expose word/segment-level timestamps and speaker labels. |
| **Feature engineering** | Deterministic, versioned, testable transformations from raw model outputs to derived metrics; no ML inside this layer. |
| **Supervised ML (NTS scoring)** | Trained on the datasets in §13, with documented train/validation/test splits, calibration, and reported (not invented) accuracy metrics. |
| **Clustering (archetyping)** | Unsupervised model trained on the derived-metric feature space; archetypes are descriptive labels validated qualitatively, not claimed to be clinically or scientifically validated personality types. |
| **LLM narrative generation** | Receives only structured JSON (features/metrics/scores/confidence); system prompt constrains it to never introduce facts not present in the input; output is reviewed against the source data before being finalized. |

---

## 13. Dataset Requirements

| Dataset | Usage |
|---|---|
| **AMI Meeting Corpus** | Primary dataset for meeting-level multimodal analysis: speaking turns, dialogue acts, and multi-party audio/video to train and validate the core feature-aggregation and fusion pipeline. |
| **MPIIGroupInteraction** | Used for behavior-related feature learning/validation — group interaction dynamics, gaze, and social signal validation. |
| **ELEA** | Used specifically where emergent-leadership supervision labels are available, to train/validate the leadership dimension of the NTS scoring model. |
| **NoXi** | Used for interaction, gesture, engagement, and conversational-behavior feature validation. |
| **First Impressions V2** | Auxiliary dataset — useful for personality/impression-adjacent signal exploration, but not treated as the primary meeting dataset and not used alone to justify any production claim. |

All dataset use must respect each dataset's original license/usage terms and documented consent conditions; no dataset subject's identity is exposed in production outputs.

---

## 14. Privacy and Ethics

- **Consent** — participants must be informed that a meeting is being analyzed and, in live/meeting-bot modes, notified in-session; org-level policy controls whether explicit per-meeting consent capture is required.
- **Anonymization** — participants are represented by stable, session-scoped anonymous IDs by default; any linkage to real identity is an explicit, separately-governed opt-in.
- **Raw video retention** — off by default; configurable retention window when enabled; raw media is deleted automatically at policy expiry.
- **Biometric data** — the system avoids storing persistent biometric identifiers (e.g., face-recognition embeddings used for cross-session identification) unless explicitly required and separately authorized.
- **Employee evaluation risks** — NTS scores must never be used as the sole input to a formal HR decision (hiring, promotion, termination); product documentation and UI must state this plainly.
- **Model bias** — scoring and archetyping models must be evaluated for differential performance across demographic groups where feasible, and limitations documented.
- **Uncertainty** — every score carries a confidence indicator; low-confidence results are flagged, not silently presented as equally reliable.
- **Human review** — a human-in-the-loop review step is required before any NTS output is used in a formal evaluation context.
- **Prohibited claims** — the system will not generate or display claims of the form "feature X proves trait Y" (see Master Instructions §5).

---

## 15. MVP Scope

The smallest usable version of the product:

```
Upload video
  → Human feature extraction (pose, face, gaze, emotion, hands)
  → audio/transcript processing (ASR + diarization)
  → feature aggregation (derived metrics)
  → basic NTS scoring (configurable dimensions, initial calibrated model)
  → dashboard (participant list, NTS radar chart, speaking-time chart, basic timeline)
```

MVP explicitly excludes live camera mode, meeting-bot integration, archetyping, and narrative generation, which are layered in after the MVP pipeline is validated end-to-end.

---

## 16. Future Scope

- Zoom integration (meeting-bot pattern from `realtime-meeting-intelligence`)
- Microsoft Teams integration
- True real-time streaming analysis (sub-second feedback loops)
- Multi-user, multi-tenant dashboard with org-level roles
- Improved/fine-tuned scoring models as more labeled data is collected
- Organization-level analytics (aggregate trends across teams, not just individuals)
- Behavioral archetyping and narrative generation (post-MVP)

---

## 17. Acceptance Criteria

| Feature | Acceptance Criteria |
|---|---|
| Upload | A valid MP4/AVI file under the configured size/duration limit uploads successfully and creates a "queued" processing job; an invalid file is rejected with a specific validation error. |
| Processing status | The UI reflects job status transitions (queued → running → completed/failed) within a defined polling/streaming interval; failed jobs show a human-readable reason. |
| CV feature extraction | For a video with clearly visible participants, pose/face/gaze/emotion/hand features are produced for ≥ a configured minimum fraction of frames where a person is detected, each with a timestamp and model version. |
| Audio processing | A transcript with speaker labels and turn timestamps is produced for a video with an audio track; turns are internally consistent (non-overlapping per speaker, ordered by time) except where interruption is explicitly modeled. |
| Feature aggregation | Derived metrics (e.g., speaking-time ratio) are deterministically reproducible from the same observed features and computation version. |
| NTS scoring | Every score returned includes a dimension, a numeric value within its defined scale, a confidence indicator, and references to the derived metrics that fed it. |
| Dashboard | All visualizations listed in Master Instructions §13 render without error for a completed meeting with ≥ 2 participants. |
| Report export | PDF/CSV/JSON exports are generated for a completed meeting and contain the full output contract (§9) or a documented subset. |
| Privacy | With raw-video retention disabled (default), the raw file is deleted from storage after feature extraction completes, verified by an automated test. |
| Live mode | A live session can be started, produces at least one live indicator update, is stopped cleanly, and produces a final report through the same output contract as file mode. |

---

## 18. Out of Scope

The following are explicitly **not** part of this project:

- Face recognition for identifying specific named employees (unless a future, separately-approved requirement explicitly authorizes it).
- Lie detection, deception analysis, or any claim of detecting truthfulness.
- Any claim of diagnosing mental health conditions from video/audio.
- Automated, human-review-free use of NTS scores in hiring, promotion, or termination decisions.
- Cross-meeting, cross-organization identity linkage without explicit, separately-governed consent.
- Real-time Zoom/Teams integration in the initial (MVP) release — this is future scope only.
- Guaranteeing any specific accuracy number for NTS predictions ahead of dataset-backed validation; no accuracy figures are to be published until measured against held-out data from the datasets in §13.
