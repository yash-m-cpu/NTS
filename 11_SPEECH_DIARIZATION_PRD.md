# 11 — Audio-Visual Speaker Diarization, Speech Analysis & Listener Analysis: Product Requirements

| Field | Value |
|---|---|
| Phase | 12 (follows Phase 11: Annotated Video Generation) |
| Status | Draft for implementation |
| Companion document | `12_SPEAKER_ATTRIBUTION.md` (algorithm, data structures, pseudocode, evaluation) |
| Audience | Implementing engineers and AI coding agents |

> **Basis of this document.** Written from `project_history_summary.md` and the stack described in it. Docs `01`–`10` were not available while writing. Every reference to an existing table, column, worker, or file that is not named in the summary is marked **[VERIFY]** and must be checked against the repo before coding. Where an assumption is wrong, adapt the implementation and keep the *requirement* intact.

---

## 1. Problem Statement

The platform currently extracts per-participant visual behaviour (head pose, gaze, pose, hands, affect) and computes speaking duration/ratio and turn interaction matrices from `faster-whisper` output (Phases 8–9). Whisper produces *what was said and when*; it does not know *who* said it, and the visual pipeline knows *who is visible* but not *who is talking*. The current per-participant speaking statistics are therefore heuristic **[VERIFY how Phase 8/9 assigned segments to participants]** and cannot support trustworthy per-person speech analysis, listener analysis, or NTS interpretation.

**Core problem:** for every speech segment detected in the audio, determine **which visual participant (`participant_track_id`) is actually speaking**, or state explicitly that this cannot be determined (off-camera, ambiguous, occluded, no audio), and attach a calibrated confidence and the evidence that led to the decision.

Lip movement alone is insufficient: mouths move when people smile, chew, yawn, laugh, or listen; several people can move their mouths at once; faces can be turned, occluded, or absent while their owner speaks. The solution must fuse audio activity, temporal synchronisation, face/track quality, and turn continuity, and must degrade gracefully into `UNKNOWN` rather than guessing.

## 2. Goals

| ID | Goal |
|---|---|
| G1 | Attribute every detected speech segment (and sub-segment where the speaker changes) to a `participant_track_id` or a typed `UNKNOWN`. |
| G2 | Provide a **calibrated confidence** per attribution and per-modality evidence breakdown (explainable, auditable). |
| G3 | Run as an efficient CPU baseline inside the existing Docker/backend stack; **no GPU and no new heavyweight ML dependency in the MVP**. |
| G4 | Produce per-participant **speech analysis** metrics with stated uncertainty bounds derived from unattributed time. |
| G5 | Produce per-participant **listener analysis** metrics (behaviour while others speak) using only defensible observable proxies. |
| G6 | Strictly separate **OBSERVED**, **INFERRED**, and **MODEL-DERIVED INTERPRETATION** data in storage, API, UI, annotation, and LLM prompts. |
| G7 | Reuse existing `participant_tracks`, feature extraction, ARQ orchestration, annotation worker, and PDF/LLM reporting; extend, do not replace. |
| G8 | Be evaluable: ship metrics, a labelled-data protocol, and regression tests so accuracy claims are measured, not asserted. |
| G9 | Be pluggable: optional diarization / speaker embeddings / ASD models improve results when present without changing output schemas. |

## 3. Non-Goals

- No real-time/streaming attribution (batch, post-upload only).
- No speaker *identification* against a voice/face database (attribution is to in-meeting visual tracks only; no biometric enrolment).
- No new face tracker and no cross-track face re-identification (out of scope; fragmentation is *flagged*, not fixed).
- No training of deep models in the MVP; no mandatory GPU.
- No speech content understanding beyond timing/word counts (no topic, sentiment, or intent classification).
- No psychological, clinical, deception, personality, or competence claims. NTS reports may describe *observed behaviour patterns* with hedged language only (see §12.4).
- No audio-only participants are given visual tracks (they are `UNKNOWN_OFFSCREEN`).
- No speech separation of overlapping voices in the MVP (overlap is detected/flagged, not unmixed).

## 4. Evidence Taxonomy (mandatory, applies to every stored/served field)

| Class | Definition | Examples in this phase | Rules |
|---|---|---|---|
| **OBSERVED** (`O`) | Direct output of a sensor/detector on the media, no cross-modal reasoning. | VAD speech probability, audio RMS, Whisper word timestamps and text, face bbox/confidence, head yaw/pitch/roll, mouth landmarks, MAR, hand keypoints, raw emotion softmax. | Stored with detector name/version. Never overwritten by inference. |
| **INFERRED** (`I`) | Deterministic/statistical combination of observed data producing a new fact-like claim, with a stated method and uncertainty. | "Track 3 is speaking during 12.4–15.9 s (conf 0.86)", speaking time per person, turn boundaries, overlap events, nod events, response latency, listener "facing-screen ratio". | Must carry `confidence` and `method_version`. Must be reproducible from `O` data + config. |
| **MODEL-DERIVED INTERPRETATION** (`M`) | Output of a learned model or LLM that attaches meaning to `O`/`I` data. | Emotion label semantics, LLM narrative on communication style, any "engagement"/"attentiveness" wording. | Always labelled as interpretation; hedged wording; never used as input to attribution; blocked when evidence is insufficient (§12.4). |

**Schema requirement:** each metric row/JSON field carries `evidence_class ∈ {"O","I","M"}`. The UI and PDF render `I`/`M` fields with visible qualifiers (e.g., "estimated", "interpretation"). Speaker attribution itself is class `I`.

**Hard rule:** `M` outputs are never fed back into attribution scoring. Attribution uses only `O` data and `I` data derived from it.

## 5. Fit With Existing Architecture

### 5.1 Reused unchanged
FastAPI, SQLAlchemy async, Alembic, PostgreSQL, Redis/ARQ, `job_service.py` idempotent enqueue, MinIO, `useJobPolling`/`JobStatusBadge`, `MeetingAnalysis` dashboard, `reportlab` PDF generator, Groq LLM client, `video_annotation_worker.py`, `participant_tracks`, `feature_extractions`, `behavioral_metrics`.

### 5.2 Extended
| Component | Change |
|---|---|
| `human_cv_script.js` / `cv_extraction_worker` | Emit **compact mouth landmark set** per face per frame (see doc 12 §4.2) if not already persisted; emit `pts_time` per frame. **[VERIFY]** whether `face.mesh` landmarks or lip keypoints are currently stored in `feature_extractions`; if not, a one-time re-extraction (backfill) is required for existing meetings. |
| STT worker | Enable `word_timestamps=True`; persist per-segment `avg_logprob`, `no_speech_prob`, and word list; persist audio-extraction offset. |
| `job_service.py` | Support a **join dependency**: `speaker_attribution` runs only when both `cv_extraction` and `stt` have succeeded (current cascade is linear "one job triggers next" — add `enqueue_when_ready(meeting_id, requires=[...])`, still idempotent). |
| `video_annotation_worker.py` | Overlay attributed speaker (colour/label, confidence tier, UNKNOWN banner) and optional subtitle strip. Zero re-inference remains true. |
| LLM report prompt | Inject attribution coverage/confidence and speech/listener metrics with evidence classes and guardrails (§12.4). |

### 5.3 New pipeline stages (appended to cascade)
```
upload → cv_extraction ─┐
                        ├─(join)→ speaker_attribution → speech_analysis → listener_analysis → [nts_visual_report (existing, re-runnable)] 
upload → stt ───────────┘                                                    └→ [video_annotation (existing, consumes attribution)]
```
Audio preparation (16 kHz mono extraction, VAD, energy envelope) is part of `stt` or a tiny `audio_prep` step preceding it; it must not duplicate ffmpeg decoding work already done by STT **[VERIFY]**.

### 5.4 Legacy compatibility
Existing Phase 8/9 speaking statistics remain readable. New results carry `attribution_version`. Frontend uses the new attribution when present, else falls back to legacy with a visible "heuristic attribution" badge. No destructive migration.

## 6. Input Data

### 6.1 Existing (consumed)
| Input | Source | Used for |
|---|---|---|
| Video/audio asset | `media_assets` (MinIO) | Audio extraction, frame timestamps |
| `participant_tracks` | DB | Candidate set (`participant_track_id`), track lifetime |
| CV features per track per frame | `feature_extractions` **[VERIFY]** | face bbox/confidence, yaw/pitch/roll, gaze, pose keypoints, hand keypoints, emotion |
| STT segments | STT worker output | Text, timestamps |
| Existing speaking turns/ratios | Phase 8/9 tables | Legacy comparison only |

### 6.2 New data required from extraction
| Data | Rate | Notes |
|---|---|---|
| Mouth landmarks (inner-lip polygon, outer corners, upper/lower lip mid-points, eye corners or iris for scale) | ≥ 12 fps, target 15–25 fps | Syllabic mouth motion is ~3–8 Hz; ≥ 12 fps required to avoid aliasing (Nyquist). Below 10 fps weights are auto-reduced (doc 12 §6.4). |
| Frame `pts_time` (seconds) | per frame | Frame index ÷ fps is **not** acceptable (variable frame rate). |
| Face landmark confidence / mesh-valid flag | per face per frame | Quality gating |
| Audio 16 kHz mono PCM, VAD probability (≤ 32 ms hop), RMS/band energy (≤ 25 ms hop) | | |
| Whisper word timestamps | | |
| Optional: diarization labels/RTTM, speaker embeddings | | Only when the optional plug-in is enabled |
| Optional metadata: `scene_layout_type ∈ {room_camera, gallery_tiles, unknown}` | per meeting | Determines which listener metrics are valid (§9.3). Default `unknown`; may be auto-suggested from the number/geometry of stable face tiles, but user-overridable. |

## 7. Output Data

### 7.1 Persisted (schemas in doc 12 §9)
| Artifact | Storage | Class |
|---|---|---|
| `attribution_runs` (config snapshot, versions, coverage stats, warnings) | PostgreSQL | I |
| `attributed_segments` (segment → `participant_track_id` or `UNKNOWN_*`, confidence tier, reason codes, secondary speakers, evidence summary) | PostgreSQL | I |
| `speaker_label_mappings` (diarization label ↔ track, optional) | PostgreSQL | I |
| `mouth_feature_series` (per track: summary + pointer) | PostgreSQL + MinIO `.npz` | O |
| `attribution_debug_<run>.json.gz` (per-slice score breakdown) | MinIO | I |
| `speech_metrics`, `conversation_metrics` | PostgreSQL | I (Whisper-derived word counts: O/M-ASR flagged) |
| `listener_metrics`, `listener_events` | PostgreSQL | I; interpretive labels M |

### 7.2 Served (API)
```
POST /api/meetings/{id}/attribution/run              # enqueue (idempotent), body: {force?: bool, config_overrides?: {...}}
GET  /api/meetings/{id}/attribution                  # run summary, coverage, warnings
GET  /api/meetings/{id}/attribution/segments         # ?min_confidence=&track_id=&include_unknown=
GET  /api/meetings/{id}/attribution/segments/{seg}/evidence   # score breakdown for explainability
GET  /api/meetings/{id}/speech-metrics               # per participant + conversation-level, with bounds
GET  /api/meetings/{id}/listener-metrics
GET  /api/meetings/{id}/listener-events
PATCH /api/meetings/{id}/attribution/segments/{seg}  # optional manual override (audit-logged; see FR-UI-4)
```
Every response includes `attribution_version`, `evidence_class`, `confidence`, and `coverage` where applicable.

## 8. Functional Requirements

### 8.1 Audio preparation & VAD
- **FR-AUD-1** Extract 16 kHz mono PCM once; record the extraction start offset relative to container start (`audio_start_offset_s`) and any detected A/V offset.
- **FR-AUD-2** Compute frame-level VAD probability (Silero VAD via ONNX, reusing the copy bundled with `faster-whisper` if API-compatible **[VERIFY]**; fallback `webrtcvad`) and a smoothed binary speech mask with min speech 0.1 s, min silence 0.15 s, pad 0.05 s.
- **FR-AUD-3** Compute band-limited (100–4000 Hz) log-RMS envelope at ≤ 25 ms hop; normalise per meeting (5th–95th percentile).
- **FR-AUD-4** Compute quality indicators: SNR estimate, clipping ratio, long-term noise floor, speech-to-total ratio. Emit `audio_quality ∈ {good, degraded, poor}` and warnings.
- **FR-AUD-5** If no audio stream or > 95 % digital silence: fail the attribution stage gracefully with `no_audio` status (§13); other pipelines are unaffected.

### 8.2 Speech segmentation & STT alignment
- **FR-STT-1** Speech regions = VAD regions; Whisper segments/words provide text and are *aligned* to regions. Whisper segment boundaries are **not** trusted as speaker boundaries.
- **FR-STT-2** Whisper segments spanning a VAD pause ≥ 0.3 s, or an optional-diarization speaker change, or > 8 s, are split at word boundaries into **attribution units**.
- **FR-STT-3** Whisper text in low-confidence regions (`avg_logprob` < −1.0 or `no_speech_prob` > 0.6) is flagged `asr_unreliable`; such units still receive attribution if VAD says speech.
- **FR-STT-4** Whisper-hallucinated text over non-speech (VAD says silence) is discarded from attribution and flagged.

### 8.3 Visual mouth features
- **FR-VIS-1** For every face detection tied to a `participant_track_id`, compute: mouth aspect ratio (MAR), mouth opening ratio (MOR), mouth width, inner-lip area, all normalised by a pose-robust face scale (inter-ocular distance in a roll-aligned frame), plus first temporal derivatives.
- **FR-VIS-2** Compute per-frame face-quality/reliability: detector confidence, landmark validity, face size, |yaw|, |pitch|, landmark jitter, mouth-region occlusion (hand or other object overlap), blur proxy if available.
- **FR-VIS-3** Per-track robust baselines (closed-mouth noise floor from globally-silent frames; speech-amplitude scale) so that people with naturally large/small mouth motion are comparable.
- **FR-VIS-4** Interpolate short gaps (< 0.2 s) in landmark series; mark longer gaps as invalid, never interpolated.

### 8.4 Speaker attribution (details in doc 12)
- **FR-ATT-1** Candidate set per time slice = tracks present (or recently present within grace period) + virtual states `UNKNOWN_OFFSCREEN` and `UNKNOWN_AMBIGUOUS`.
- **FR-ATT-2** Score candidates using the fused evidence (lip activity, audio-visual synchrony, onset/offset alignment, diarization consistency when available, pose/visibility as reliability, continuity via temporal model).
- **FR-ATT-3** Temporal smoothing with hysteresis (HMM/Viterbi + forward-backward posteriors) to prevent rapid speaker flipping; allow rapid switches only with strong evidence.
- **FR-ATT-4** Output per attribution unit: winner, calibrated confidence, tier, runner-up, margin, reason codes, secondary speakers (overlap), evidence summary.
- **FR-ATT-5** Never force an assignment. If no candidate satisfies thresholds → `UNKNOWN_*` with a `candidate_hint` (best guess) that is **excluded** from headline metrics.
- **FR-ATT-6** Detect within-segment speaker changes and split units accordingly.
- **FR-ATT-7** Deterministic: same inputs + config + versions → identical output (fixed seeds, stable sort order).
- **FR-ATT-8** Config snapshot and algorithm version persisted per run.

### 8.5 Diarization
See §10.

### 8.6 Speech analysis
See §11.

### 8.7 Listener analysis
See §12.

### 8.8 Annotation & reporting
- **FR-ANN-1** Annotated video shows the attributed speaker's box in a distinct style (e.g., thick border + "SPEAKING" tag) with tier-dependent style: HIGH solid, MEDIUM dashed, LOW dotted; `UNKNOWN` shows a frame-corner banner ("Speech: off-camera/unknown").
- **FR-ANN-2** Optional subtitle strip with text from Whisper for the current unit, prefixed by speaker label or "?".
- **FR-ANN-3** Debug overlay toggle: mouth landmarks, MAR trace, per-candidate score bars.
- **FR-RPT-1** LLM prompt receives aggregated speech/listener metrics, coverage, confidence, and warnings; never raw per-frame data.
- **FR-RPT-2** PDF gains a "Speech & Listening Evidence" section including method notes, coverage, confidence, and limitations paragraph.

### 8.9 Frontend
- **FR-UI-1** Speaker timeline (swimlane per track + UNKNOWN lane) with confidence-tier shading; click to seek video.
- **FR-UI-2** Segment inspector showing evidence breakdown (bar per component) and reason codes.
- **FR-UI-3** Metrics tables show value, uncertainty interval, evidence class, and "insufficient evidence" states.
- **FR-UI-4** Optional manual correction of a segment's speaker; stored as `override` (original retained), audit-logged, and used for evaluation ground truth export.
- **FR-UI-5** Job status uses existing `useJobPolling`; `completed_with_warnings` state displayed.

## 9. Speaker Attribution Requirements (summary; normative detail in doc 12)

1. **Multimodal necessity.** A candidate may not be selected on lip activity alone: selection requires at least one *temporal-synchrony* or *diarization* evidence source with positive support, otherwise the unit is at most MEDIUM and normally `UNKNOWN_AMBIGUOUS`. Exception: exactly one viable candidate with reliable landmarks and speech present may be attributed on lip + sync + continuity (still confidence-capped at 0.85 when sync evidence is unavailable).
2. **Negative evidence counts.** A reliable (valid landmarks, near-frontal) candidate with a closed, motionless mouth during strong speech is *vetoed* for that slice.
3. **Reliability weighting.** Each evidence source is weighted by its reliability at that moment (occlusion, pose, FPS, audio quality). Unreliable ≠ negative; it lowers influence.
4. **Off-camera as first-class.** `UNKNOWN_OFFSCREEN` competes as a hypothesis with its own evidence (no viable candidates, or speech with no matching mouth activity anywhere).
5. **Calibrated confidence.** Confidence values must be calibrated on labelled data (ECE ≤ 0.08). Until calibration data exists, thresholds are provisional and the UI labels confidence "uncalibrated".
6. **Hysteresis.** Minimum dwell and switch penalties as in doc 12 §11; short backchannel exceptions per doc 12 §13.
7. **Explainability.** Every attribution has a persisted per-slice/per-segment breakdown.
8. **Timing.** Lag search ± 0.3 s between audio and mouth motion; explicit A/V offset handling.

## 10. Diarization Requirements

Diarization here means *"which voice is this, consistently across the meeting"*. It is **optional** and used as consistency evidence, not as the decision-maker.

| ID | Requirement |
|---|---|
| DIA-1 | **Level 0 (MVP baseline):** no audio speaker labels. Consistency comes from visual synchrony + temporal model. Output still includes `speaker_turn_id` (contiguous same-track run). |
| DIA-2 | **Level 1 (optional plug-in):** accept external diarization as RTTM/JSON (`label, start, end`) from an adapter (e.g., pyannote.audio) behind a feature flag. The adapter interface is defined in doc 12 §17. |
| DIA-3 | Diarization labels are mapped to visual tracks by a global assignment (Hungarian) over co-occurrence of label activity and visual evidence, with an explicit "no matching track" option (off-camera voice). Mapping confidence persisted. |
| DIA-4 | Attribution must not blindly trust diarization: if a label→track mapping has confidence < 0.6, diarization evidence is down-weighted proportionally. |
| DIA-5 | Diarization–visual disagreement (label mapped to track A but strong sync evidence for track B over ≥ 1.0 s) yields `reason: diar_visual_conflict`, lower confidence, and is logged for evaluation. |
| DIA-6 | Diarization may split or merge voices erroneously (over/under-segmentation). Mapping stage supports many-labels→one-track and one-label→many-tracks (the latter flagged as suspected merge). |
| DIA-7 | Overlap flags from diarization are honoured; without diarization, overlap is only flagged as `possible_overlap` (visual multi-activity) and never claimed as observed. |
| DIA-8 | Model weights required by optional adapters must be **baked into the Docker image or mirrored in MinIO** (the project has previously suffered HuggingFace DNS failures). No runtime downloads from external hubs. |
| DIA-9 | Diarization error rate against reference is reported by the evaluation harness (doc 12 §18) but is not a gate for MVP. |

## 11. Speech Analysis Requirements

Computed from attributed segments. Per participant: **hard** estimate (HIGH+MEDIUM only) and **upper bound** (hard + LOW/UNKNOWN units whose `candidate_hint` is that participant). Both are stored; UI displays the hard value with the interval.

| Metric | Definition | Class | Min evidence | Notes |
|---|---|---|---|---|
| `speaking_time_s` | Sum of attributed speech duration (VAD-bounded) | I | ≥ 1 attributed unit | Interval [hard, upper] |
| `speaking_share` | Participant time ÷ total attributed speech time | I | total attributed ≥ 30 s | Uses hard values; unattributed share reported separately |
| `turn_count`, `turn_durations` (mean/median/p90/max) | Turn = maximal same-speaker run allowing gaps ≤ 1.0 s | I | ≥ 3 turns for mean/median | |
| `longest_monologue_s` | Longest turn with no other attributed speaker | I | — | |
| `word_count`, `words_per_minute` | Whisper words within attributed units; WPM = words ÷ attributed speech minutes | O (ASR text) → I (rate) | ≥ 20 s attributed speech | ASR error caveat surfaced |
| `pause_stats` | Intra-turn pauses ≥ 0.25 s: count, mean | I | ≥ 3 turns | |
| `response_latency_s` | Onset of participant turn minus end of previous *different* speaker's turn (can be negative = overlap) | I | ≥ 3 transitions, both attributions ≥ MEDIUM | |
| `overlap_onset_events` | Participant starts while another attributed speaker is active, overlap ≥ 0.5 s | I | Both ≥ MEDIUM | Neutral name. Do **not** label "interruption" in stored data |
| `overlap_yield_events` | Other speaker stops within 2 s after overlap onset | I | as above | "Successful interruption" wording, if ever shown, is `M` and hedged |
| `backchannel_count` | Attributed units < 1.0 s and ≤ 3 words inside another's turn | I | ≥ MEDIUM | Lexicon-free by design |
| `silence_participation` | Fraction of meeting visible with zero attributed speech; `silent_participant` flag if speaking_time < 5 s **and** visible ≥ 60 % of meeting | I | visibility measured | Must state whether the person may have spoken while off-camera/unattributed |
| Conversation: `overlap_ratio`, `silence_ratio`, `turn_transition_matrix` (soft counts weighted by confidence), `speaking_share_gini`, `speaker_change_rate_per_min`, `unattributed_share` | | I | | |
| Time series: speaking share per 60 s bucket | | I | | |

Requirements:
- **SPE-1** Metrics computed for every participant with the minimum-evidence rule; otherwise return `{"status":"insufficient_evidence","reason":...}`.
- **SPE-2** Never report a speaking-share ranking if `unattributed_share` > 25 % or the upper bound overlaps rank ordering; report "ranking uncertain".
- **SPE-3** Metrics are recomputable from `attributed_segments` alone (pure function; unit-tested).
- **SPE-4** No metric may be phrased as a psychological trait in storage or UI (e.g., "dominance", "confidence", "assertiveness" are forbidden metric names; see §12.4).

## 12. Listener Analysis Requirements

**Definition.** For each participant track *P* and each interval in which another participant *S* is attributed as speaker with confidence ≥ 0.55 and *P* is not attributed as speaking (overlap intervals excluded), *P* is a **listener** for that interval. Listening intervals are *inferred* (class `I`), inheriting attribution confidence.

### 12.1 Metrics
| Metric | Definition | Class | Validity conditions |
|---|---|---|---|
| `listening_time_s`, `visible_listening_fraction` | Time in listener role; fraction with face visible & valid | I | — |
| `facing_screen_ratio` | Fraction of visible listening time with |yaw| < 20°, |pitch| < 15° (head roughly frontal) | O→I | All layouts; **this is head orientation only, not attention** |
| `gaze_toward_speaker_ratio` | Fraction of visible listening time where head-yaw/gaze bearing points toward the speaker's image-plane position within tolerance (±20°) | I | **Only** `scene_layout_type = room_camera`, both faces visible, camera roughly frontal to the group; otherwise `not_applicable` |
| `gaze_at_screen_center_ratio` | Gaze bearing near frontal | O→I | `gallery_tiles` alternative to previous |
| `head_nod_events` | Pitch oscillation 0.5–3 Hz, ≥ 2 cycles, peak-to-peak ≥ max(4°, 3× track pitch noise) | I | Head-pose confidence ≥ 0.6 during event |
| `head_shake_events` | Same on yaw | I | as above |
| `nod_rate_per_min_listening` | Events ÷ visible listening minutes | I | ≥ 60 s visible listening |
| `backchannel_vocal_events` | See §11 (`backchannel_count`) | I | |
| `looking_down_ratio` | Fraction with pitch < −20° | O→I | Ambiguous (notes/phone/thinking); never labelled "distracted" |
| `face_absent_or_turned_ratio` | Fraction of listening time with face absent or |yaw| > 60° | O→I | Reason unknown; reported as-is |
| `hand_to_face_events` | Hand keypoints overlapping face region ≥ 0.5 s | O→I | |
| `affect_distribution_during_listening` | Aggregated Human emotion softmax means during listening | **M** | Low reliability; aggregate only; min 60 s; never per-second claims |
| `reaction_to_speaker_change` (optional) | Head-orientation change toward new speaker within 1.5 s of confident switch | I | `room_camera` only |

### 12.2 Requirements
- **LIS-1** Every metric declares validity conditions; failing conditions produce `not_applicable` or `insufficient_evidence`, never a zero.
- **LIS-2** Listening intervals inherit uncertainty: confidence-weighted durations and an interval [hard, upper] as in §11.
- **LIS-3** Gaze-based metrics must consider that gaze from webcam-scale faces is low precision (Human gaze is approximate). Head orientation is the primary signal; gaze refines only when iris landmarks are valid.
- **LIS-4** Camera geometry caveat: in gallery/tile layouts, "looking at the speaker's tile" is not observable from a single participant's webcam; the system must not compute or imply it.
- **LIS-5** Events (nods, shakes, hand-to-face, looking down) stored in `listener_events` with `start, end, track_id, type, confidence, overlapped_speaker_track_id`.

### 12.3 What listener analysis must **not** claim
"Engaged", "interested", "bored", "agrees", "disagrees", "respectful", "distracted", "attentive" as **facts**. The permitted vocabulary is observational ("head oriented toward the screen 78 % of visible listening time", "6 nod events, 1.2/min"). Any interpretive wording appears only in the LLM narrative section, is class `M`, hedged ("may suggest"), and cites the underlying metrics and their evidence sufficiency.

### 12.4 Evidence sufficiency gate for reporting (LLM/PDF)
A participant is eligible for an interpretive narrative only if: attributed speech ≥ 30 s **or** visible listening ≥ 120 s; mean attribution confidence ≥ 0.6; face-valid fraction ≥ 50 %; audio quality ≠ `poor`. Otherwise the report says "insufficient evidence" for that participant. The LLM system prompt must contain the forbidden-claims list of §12.3 plus: no personality or clinical inferences, no inference of intent, no comparison between participants on single weak metrics, no conclusions from emotion labels alone, and mandatory mention of coverage and limitations.

## 13. Error Handling

| Condition | Detection | Behaviour | Job status |
|---|---|---|---|
| No audio stream / silent audio | ffprobe streams; speech ratio < 1 % | Skip attribution; write `attribution_run` with `status=no_audio`; speech/listener analyses skipped; visual reports unaffected | `completed_with_warnings` |
| No face tracks | `participant_tracks` empty | All speech `UNKNOWN_OFFSCREEN` (reason `no_face_tracks`); speech-only metrics (total speech, pauses) still produced; per-person metrics absent | `completed_with_warnings` |
| STT missing/failed | STT job failed | Attribution can still run on VAD alone (no text); text-dependent metrics absent | `completed_with_warnings` |
| CV missing/failed | CV job failed | Attribution not run (visual evidence required); return prerequisite error | `failed` (`prerequisite_failed`) |
| Mouth landmarks unavailable (legacy meeting) | No lip data in features | Offer/queue backfill extraction; if declined → fail with actionable message | `failed` (`landmarks_missing`) |
| Low FPS (< 10) | Measured from `pts_time` | Reduce sync weights (§6.4 doc 12), flag `low_fps`, cap confidence 0.75 | `completed_with_warnings` |
| Variable FPS / dropped frames | Δpts jitter | Use `pts_time`; resample onto uniform grid; flag when > 5 % dropped | warning |
| Audio/video duration mismatch > 1 s | ffprobe durations | Align by container start times; if drift detected, estimate linear drift via speech-onset ↔ mouth-onset correlation, else warn | warning |
| Corrupted frame / decode error | Worker exception | Skip frame, count; abort if > 10 % | warning/failed |
| Worker crash / OOM | ARQ exception | Idempotent retry (max 2), attribution writes are transactional (`run_id`-scoped, atomic swap of "current" pointer) | per retry policy |
| Diarization adapter failure | Exception/timeout | Fall back to Level 0; record `diarization_unavailable` | warning |
| Numerical anomalies (NaN/inf) | Guards | Sanitize to invalid-flag + zero reliability; count in run stats | warning |
| Config invalid | Pydantic validation | Reject enqueue with 422 | — |

All failures produce structured `warnings: [{code, severity, message, count?}]` on the run. No silent fallbacks.

## 14. Confidence Thresholds (defaults; all configurable; provisional until calibrated — doc 12 §18.4)

| Item | Default |
|---|---|
| Tier **HIGH** | calibrated conf ≥ 0.80 **and** margin to runner-up ≥ 0.30 **and** ≥ 1 independent sync/diar evidence |
| Tier **MEDIUM** | 0.55 ≤ conf < 0.80 (or HIGH conditions failing only on independence) |
| Tier **LOW** | 0.35 ≤ conf < 0.55 (retained, excluded from headline metrics) |
| **UNKNOWN_AMBIGUOUS** | conf < 0.35, or margin < 0.10 among visible candidates |
| **UNKNOWN_OFFSCREEN** | `UNKNOWN_OFFSCREEN` posterior ≥ 0.5, or no viable candidate |
| Min confidence for per-person metrics | 0.55 (MEDIUM+) |
| Min confidence for listener role of *speaker S* | 0.55 |
| Segments < 0.4 s | Tier cap MEDIUM, conf cap 0.60 |
| No sync evidence available (low FPS/occluded) | conf cap 0.65 |
| Diarization mapping confidence for full weight | ≥ 0.6 |
| Min face quality for lip evidence | `q_vis ≥ 0.35` (else lip evidence reliability scales to 0) |
| Min speech duration considered a unit | 0.15 s |

## 15. Edge Cases & Required Behaviour

| # | Situation | Detection | Required behaviour | Flags / reason codes |
|---|---|---|---|---|
| E1 | **Multi-speaker (turn-taking)** | Speech regions separated by pauses with different best candidates | Independent attribution per unit; switch allowed after pause with lower penalty | — |
| E2 | **Overlapping speech** | Diarization overlap flag, or ≥ 2 candidates with strong lip+sync and elevated audio energy/band-limited noise | Primary + secondary speaker list; text flagged unreliable; excluded from response-latency calc | `overlap_detected`(diar) / `possible_overlap`(visual only) |
| E3 | **Off-camera speaker** | Speech with no candidate having positive sync; all visible mouths closed/silent | `UNKNOWN_OFFSCREEN` | `no_visual_match` |
| E4 | **Partially visible face** (edge crop, half-turned) | bbox clipped, |yaw| > 45°, landmark jitter | Reliability down-weighted; may still win if sync strong | `partial_face` |
| E5 | **Silent participants** | Visible, mouth quiet, no sync | Never attributed; metrics show visibility + zero attributed speech; flagged `silent_participant` only with visibility proof | — |
| E6 | **Enter/leave frame** | Track start/end | Candidate exists only within lifetime ± 1.0 s grace; speech during absence → OFFSCREEN; speech at boundary may keep previous speaker for grace period | `track_boundary` |
| E7 | **Multiple people moving mouths** (laughing, chewing, side-talk) | Multiple candidates with high activity | Sync-relative scoring; if margin < 0.10 → AMBIGUOUS; laughing bursts flagged | `multi_mouth_activity`, `possible_laughter` |
| E8 | **Background speech** (TV, hallway) | VAD speech with low energy, no sync, stable across meeting | Low-energy speech below `bg_energy_ratio` relative to meeting median → `UNKNOWN_OFFSCREEN`, `background_speech`; optionally excluded from speech totals | `background_speech` |
| E9 | **Audio noise** | SNR < 10 dB, VAD flapping | Lower audio-derived reliability; raise UNKNOWN prior; warn | `noisy_audio` |
| E10 | **Camera cuts / scene change** | Frame-wide histogram jump, track ID reset/mass appearance change, or CV-reported shot boundary | Break temporal model at cut (state reset, transition penalty ≈ 0.5); sync windows never straddle a cut | `camera_cut` |
| E11 | **Missing audio** | See §13 | No attribution | `no_audio` |
| E12 | **Missing face tracks** (for some period) | No tracks | OFFSCREEN | `no_face_tracks` |
| E13 | **Hand covering mouth** | Hand keypoints in mouth ROI | Lip reliability → 0 for interval | `mouth_occluded` |
| E14 | **Masks / non-standard faces** | Landmark confidence low, MAR variance abnormal | Lip evidence off; rely on diar/continuity only; cap MEDIUM | `landmarks_unreliable` |
| E15 | **Screen-share / video tile of a recorded person** | Track whose mouth moves in sync with audio *but* is a video-in-video source | Not detectable in MVP; document as known false-positive risk | — |
| E16 | **Speakerphone / remote participant heard in room** | Room camera, audio speech, nobody's mouth moving | OFFSCREEN | `no_visual_match` |
| E17 | **Whisper hallucination / no speech** | Text with VAD silence | Drop unit | `asr_hallucination_suspected` |
| E18 | **Very short utterances / backchannels** | < 0.8 s | Special handling doc 12 §13 | `short_utterance` |
| E19 | **A/V desync or drift** | Onset lag consistently outside ±0.3 s | Estimate offset from confident onsets; else warn | `av_desync` |
| E20 | **Track fragmentation** (same person, new track) | Spatially adjacent track starts within 2 s of another ending, similar bbox | Attribute independently; flag; optional post-hoc merge suggestion | `track_fragmentation_suspected` |
| E21 | **Two tracks on one face (duplicate)** | High IoU tracks at same time | Treat as one candidate group; ties are AMBIGUOUS | `duplicate_track` |
| E22 | **Speaker turned away/looking down while talking** | Landmarks invalid but continuity + audio | Continuity (hysteresis) may retain speaker; conf capped MEDIUM | `speaker_pose_degraded` |
| E23 | **Laugh / cough / non-speech vocalisation** | Whisper text empty/`[Laughter]`, VAD ambiguous | Attribute if evidence strong, tag non-speech; excluded from WPM | `non_speech_vocalisation` |

## 16. Non-Functional Requirements

| ID | Requirement |
|---|---|
| NFR-1 | **Performance:** attribution + analysis stages ≤ 0.10× media duration on 4 vCPU (excl. STT/CV, which are existing costs). Peak extra memory ≤ 1.5 GB for a 1-hour, 8-track meeting. |
| NFR-2 | **Scalability:** linear in duration × tracks; per-slice cost O(N tracks); no per-frame DB round trips (batch reads; bulk inserts; columnar `.npz` for dense series). |
| NFR-3 | **Determinism & idempotency:** identical inputs+config → identical outputs; re-running replaces the "current" result atomically; ARQ job keyed by `(meeting_id, stage, config_hash)`. |
| NFR-4 | **Explainability:** persisted per-slice breakdown ≤ 50 MB per hour compressed. |
| NFR-5 | **Observability:** structured logs with `run_id`; stage timings; counters (slices, unknown rate, warnings); Prometheus-style metrics if the project already has them **[VERIFY]**. |
| NFR-6 | **Configurability:** all thresholds in a Pydantic `AttributionConfig` with defaults, per-project overrides, stored in run snapshot. |
| NFR-7 | **Privacy/security:** no biometric identity storage beyond existing tracks; face landmark series treated as sensitive: same RLS/org scoping as other `feature_extractions`; retention follows existing policy; debug artifacts in org-scoped MinIO prefix; presigned URLs short-lived. |
| NFR-8 | **Compatibility:** Python 3.12, no torch required for MVP; optional extras isolated in a separate `requirements-attribution-optional.txt` and Docker build arg `WITH_DIARIZATION=0/1`. |
| NFR-9 | **Testability:** pure-function core (`app/services/attribution/*`) with no DB/network access; synthetic scenario generator (doc 12 §19). |
| NFR-10 | **Versioning:** `attribution_version` semver; DB migration additive only (Alembic); old runs retained. |
| NFR-11 | **Robustness:** never crash on missing modalities; every degraded mode has a code path and a test. |
| NFR-12 | **Fairness caveat:** landmark quality varies with skin tone, facial hair, glasses, masks, head coverings, lighting, camera quality; evaluation must report accuracy stratified by these conditions where data permit; limitations documented. |

## 17. Acceptance Criteria

Targets are provisional until the first labelled set exists (≥ 10 meetings, ≥ 3 h, ≥ 3 layouts). Change requires an explicit sign-off note in the repo.

### 17.1 Functional
| ID | Criterion |
|---|---|
| AC-F1 | For any meeting with audio + CV + STT completed, the pipeline creates an `attribution_run` and `attributed_segments` covering **100 %** of VAD speech time (each moment is attributed or typed UNKNOWN; no gaps > 50 ms inside speech). |
| AC-F2 | No segment is attributed without a stored evidence breakdown and reason codes. |
| AC-F3 | UNKNOWN types are never merged into participant totals; `unattributed_share` reported. |
| AC-F4 | All edge cases E1–E23 have handling code and at least one automated test (test IDs in doc 12 §19). |
| AC-F5 | Missing audio, missing CV, missing STT, missing landmarks, low FPS produce the specified statuses without unhandled exceptions. |
| AC-F6 | Job cascade correctly waits for both CV and STT (join), remains idempotent under duplicate enqueue and worker restarts. |
| AC-F7 | Annotated video renders speaker overlays and UNKNOWN banner from stored attribution with zero model re-inference. |
| AC-F8 | API endpoints of §7.2 implemented with typed schemas and org-scoped access control (RLS simulation applied). |
| AC-F9 | Evidence classes (`O/I/M`) present on all metric payloads; UI shows qualifiers. |
| AC-F10 | Reports gate interpretive language per §12.4; automated test asserts forbidden phrases never appear in prompts' allowed-claims template. |
| AC-F11 | Determinism test: two runs identical (hash equal) on the same input. |

### 17.2 Quality (evaluation harness, doc 12 §18)
| ID | Metric | Target on "clean" tier (frontal, ≥ 15 fps, SNR ≥ 15 dB, ≤ 6 people) | Target on "hard" tier (occlusion, off-camera speakers, noise) |
|---|---|---|---|
| AC-Q1 | Segment-level accuracy among **attributed** (HIGH+MEDIUM) segments | ≥ 90 % | ≥ 75 % |
| AC-Q2 | Attribution coverage (HIGH+MEDIUM share of speech time) | ≥ 80 % | ≥ 55 % |
| AC-Q3 | Time-weighted speaker accuracy on all speech frames counting UNKNOWN as wrong for on-camera speech | ≥ 78 % | ≥ 55 % |
| AC-Q4 | Speaker-attribution DER (collar 0.25 s, fixed track↔reference mapping) | ≤ 15 % | ≤ 30 % |
| AC-Q5 | False speaker activation (FSA) rate | ≤ 5 % of speech time | ≤ 12 % |
| AC-Q6 | Missed speaker activation (MSA) rate for on-camera speakers | ≤ 12 % | ≤ 30 % |
| AC-Q7 | Off-camera speech correctly typed OFFSCREEN (recall) | ≥ 80 % | ≥ 60 % |
| AC-Q8 | Spurious speaker switches | ≤ 1.0 / min | ≤ 2.0 / min |
| AC-Q9 | Switch boundary error (median) | ≤ 0.35 s | ≤ 0.6 s |
| AC-Q10 | Calibration: ECE | ≤ 0.08 | ≤ 0.12 |
| AC-Q11 | Baseline must beat lip-activity-only baseline by ≥ 10 points segment accuracy (validates multimodal design) | required | required |

### 17.3 Non-functional
- AC-N1 NFR-1 measured on the reference 1 h/6-track fixture.
- AC-N2 No new mandatory runtime download at container start; image builds offline-capable after dependency install.
- AC-N3 Docker image size increase for MVP ≤ 150 MB.
- AC-N4 Test suite: unit coverage ≥ 85 % on `attribution/*`; integration test with tiny fixture video (≤ 20 s) runs in CI < 3 min.

## 18. Delivery Plan (suggested increments)

1. **M1 – Foundations:** timeline/pts handling, audio prep, VAD, envelope, DB migrations, job join.
2. **M2 – Mouth features:** CV script extension/backfill, mouth series, quality/reliability.
3. **M3 – Baseline attribution:** scoring, HMM, segments, confidence tiers, debug output, evaluation harness with synthetic tests.
4. **M4 – Analysis:** speech metrics, listener metrics, API, frontend timeline.
5. **M5 – Integration:** annotation overlays, report/prompt guardrails, PDF section.
6. **M6 – Calibration:** labelled data collection, threshold tuning, ECE; decide on optional models (doc 12 §17).

## 19. Open Questions (resolve before/while implementing M1–M2)

1. Are lip/mesh landmarks currently persisted? At what fps does the CV script sample? (Determines backfill scope.)
2. How were Phase 8/9 speaking turns assigned to participants? (Defines legacy fallback and comparison baseline.)
3. Does the existing tracker preserve identity across re-entry, and does `participant_tracks` carry a face descriptor?
4. Are uploads predominantly room cameras or gallery/tile recordings? (Sets default `scene_layout_type` and which listener metrics matter.)
5. Is there any existing shot-boundary/scene-cut signal from the CV pipeline?
6. Retention/consent policy for face-landmark series and manual corrections.
7. Availability of labelled meetings (or budget for annotation) for calibration.
