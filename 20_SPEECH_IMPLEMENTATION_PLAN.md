# 20 — Speech Implementation Plan (Roadmap)

**Scope:** Add speech diarization, speaker attribution, prosody, listener analysis, interaction metrics, annotated video, and LLM reporting to the existing NTS platform.
**Principle:** Extend the existing architecture. Reuse working components. Add heavy models only as optional enhancement tracks.

---

## 0. Read this first: what this plan is and is not based on

I could **not** inspect the repository. The only material available was `project_history_summary.md`. Docs `11`–`18` were not provided either. Therefore:

- **"Known"** = stated in the history summary.
- **"Assumed"** = my proposed name/shape. Every assumed path, table, function or column is marked ** and must be confirmed or renamed in **Phase 1**.
- Where doc 12/13/14/15/16/17/18 content would normally constrain a decision (thresholds, schema, attribution algorithm), this plan gives a **working default** and flags it *reconcile with doc N*.
- The Phase 1 audit is therefore the one phase that is a hard gate. Do not start Phase 2 until its checklist is complete and this document is updated with real names.

### 0.1 What the history summary tells us (Known)

| Area | Known |
|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.0 async, PostgreSQL 15, Alembic |
| Jobs | Redis + ARQ; `job_service.py` gives idempotent enqueue, prevents duplicate concurrent processing per meeting; pipeline **cascade** (job success triggers next) |
| Storage | MinIO; presigned PUT for uploads, presigned GET for playback; generated PDFs and annotated videos stored there |
| Tables | `users, organizations, projects, meetings, media_assets, processing_jobs, participant_tracks, feature_extractions, behavioral_metrics, nts_scores`, plus `nts_visual_reports` (UPSERT cache) |
| CV | `@vladmandic/human` via `human_cv_script.js`; `cv_extraction_worker` spawns Node, pipes video through ffmpeg, parses JSON lines. Features: head yaw/pitch/roll, gaze bearing, body keypoints, hands, emotions |
| STT | `faster-whisper`, offline; "speaking turns" and speaking ratio/duration per participant; interaction matrix (who talks after whom) already visualized |
| LLM/PDF | Groq (Qwen), strict system prompt, statistical summaries of CV data, `reportlab` PDF, UPSERT cache |
| Annotation | `video_annotation_worker.py` (OpenCV) reads DB features, draws boxes, BlazePose skeletons, head rotation/emotion; encodes MP4; uploads to MinIO; presigned GET |
| Frontend | React 18, TS, Vite, Tailwind, Zustand `authStore`, `apiClient` with 401 refresh, `useJobPolling`, `JobStatusBadge`, `VideoUploader`, `MeetingAnalysis` dashboard with Recharts |

### 0.2 Things the summary leaves ambiguous (must be answered in Phase 1)

1. **How are existing "speaking turns per participant" attributed to participants today?** Separate audio tracks per participant? A single mixed track with heuristic mapping? The summary says "Processed audio tracks", which may mean separate per-participant audio. This changes Phases 6 and 8 substantially. If per-participant audio exists, attribution becomes nearly deterministic and Phase 7 mouth activity becomes a validation signal instead of the primary one.
2. **Are face/mouth landmarks stored?** The summary lists head rotation, gaze, pose, hands, emotion. Lip landmarks are not listed. If they are not stored, Phase 7 needs one lightweight extra CV pass. That is an exception to "avoid rerunning CV" and must be justified explicitly, see Phase 7.
3. **What identifies a participant track across the whole video?** `participant_tracks.id` stability (re-identification after occlusion) determines attribution quality.
4. **Is there existing diarization?** The summary says `faster-whisper` gives "local transcription and diarization". faster-whisper itself does not diarize, so something else provides it.
5. **Does the annotated MP4 have audio, and is it double-encoded?** (See doc 19 §16.)

---

## 1. Global conventions

### 1.1 Timeline

- Canonical clock: **video clock, integer milliseconds** (`*_ms` columns). Audio start offset is applied **once**, in Phase 3.
- Storage grids: VAD/segments at ms precision; lip activity and speech activity at 10 Hz; prosody at 100 ms hop.

### 1.2 Provenance model (applies to every phase)

Every derived row and metric carries:

| Field | Meaning |
|---|---|
| `run_id` → `pipeline_runs.id` | Which execution produced it (stage, params hash, code version, model versions) |
| `derivation` | `observed` (directly measured signal or transcript), `derived` (deterministic computation over observed data), `inferred` (heuristic/model judgment) |
| `method` | e.g. `silero_vad_v5`, `lip_vad_corr_v1` |
| `evidence` (JSONB) | Source row ids, intervals, and the numeric inputs used |

Rules:

1. A metric may only cite rows from succeeded runs of upstream stages; the `inputs` list records `run_id`s so staleness is detectable.
2. `inferred` is the ceiling: nothing derived from an `inferred` input can be labeled `observed`. Downstream derivation class = the weakest input class.
3. Re-running a stage creates a **new** `run_id`; old rows are retained until a retention job removes them, so reports remain reproducible.

Provenance classes for the final questions are mapped in §3.

### 1.3 Language rule

No absolute psychological labels anywhere (DB enums, UI, video, LLM report). Behavioral states are worded as `POSSIBLE …` / "consistent with …".

### 1.4 Job pattern

New stages are ARQ jobs registered as **new links in the existing cascade** in `job_service.py`. Do not create a parallel orchestration path. Each job:

- is idempotent on `(meeting_id, stage, params_hash)`,
- writes a `pipeline_runs` row (`running` → `succeeded|failed`),
- upserts results in one transaction, keyed by `(meeting_id, stage, run_id)`,
- exposes progress through the existing `processing_jobs` + `useJobPolling` path.

### 1.5 Proposed cascade

```
upload → [existing] cv_extraction ─────────────────────────────┐
       → [NEW] audio_preprocess → [NEW] vad → [existing↑] stt ─┤
                                                               ├→ [NEW] mouth_activity (needs cv tracks)
       → [NEW, optional] audio_diarization ────────────────────┤
                                                               ↓
                              [NEW] speaker_attribution → [NEW] prosody
                                                        → [NEW] listener_analysis
                                                        → [NEW] speech_fusion (metrics + interactions)
                                                        → [existing] llm_report (extended)
                                                        → [existing] video_annotation (extended)
```

`cv_extraction` and the audio branch run in parallel; `speaker_attribution` waits for both (join). Verify in Phase 1 whether `job_service.py`'s cascade supports fan-in. If it only supports linear chains, add a small "all prerequisites succeeded" check at the head of `speaker_attribution` (job re-enqueues itself with delay until satisfied) rather than rewriting the cascade.

---

## 2. MVP definition and priorities

### 2.1 MVP (ship first)

| Included | Phase |
|---|---|
| Existing participant tracks | reused |
| Audio extraction + A/V sync | 3 |
| VAD (bundled with faster-whisper) | 4 |
| faster-whisper word timestamps | 5 |
| Mouth/lip activity | 7 |
| Lip↔audio speaker attribution, unknown handling | 8 |
| Basic prosody (pitch, rate) | 9 |
| Turn/overlap/interruption/response metrics, participation balance | 11 |
| API endpoints | 12 |
| Annotated video with speech overlay | 14 |
| Testing and performance | 16, 17 |

### 2.2 MVP+ (immediately after)

Listener analysis (10), dashboard (13), LLM speech report (15).

### 2.3 Optional enhancement tracks (only if MVP validation shows a need)

| Track | Adds | Introduce when |
|---|---|---|
| E1 | `pyannote.audio` diarization | Single mixed audio track and cluster-lite (Phase 6) is insufficient |
| E2 | ECAPA-TDNN speaker embeddings | Cross-meeting speaker identity, or off-screen speakers need clustering |
| E3 | SyncNet / TalkNet active-speaker detection | Lip-correlation attribution accuracy is below the acceptance threshold on the labeled set |
| E4 | WhisperX / CTC forced alignment | Whisper word timestamps are too coarse for interruption/latency metrics |
| E5 | Head-pose-aware mouth features, mouth ROI super-resolution | Small/angled faces yield unusable mouth signal |

**Gate for every optional track:** a measured deficiency on the labeled evaluation set (Phase 16), not a preference for a better model.

---

## 3. Question coverage matrix (what the finished system must answer)

Class: **O** = observed, **D** = derived (deterministic from observed), **I** = inferred (heuristic).
"Speaker identity" is always **I**, because it is attributed from lip/audio evidence, so any answer that depends on *who* said something is at least **I** unless per-participant audio tracks exist.

| Question | Source (table / endpoint) | Class | Phase |
|---|---|---|---|
| Who was speaking at 01:24.5? | `speech_segments` at `t=84500` ms → `GET /speech/at?t=84.5` | **I** (that speech occurred: **O**) | 8, 12 |
| How long did each person speak? | `speech_metrics: speaking_time_ms` | **I** | 11 |
| What did each person say? | `speech_segments.text`, `speech_words` | text **O**, attribution **I** | 5, 8 |
| Speaking rate per person | `speech_metrics: articulation_wpm, overall_wpm` | **D** from **I** attribution | 9 |
| Pitch distribution | `speech_metrics: f0_p10/p50/p90, f0_range_st` | **D** from **I** attribution | 9 |
| Interruption frequency | `interaction_events(type='interruption')` | **I** | 11 |
| Who responded to whom | `interaction_events(type='response')` + matrix | **I** | 11 |
| Response latency | `interaction_events.latency_ms` | **D** from **I** | 11 |
| While P1 spoke, was P2 oriented toward P1? | `listener_states` (target = P1) + `gaze_on_target_pct` | **I** (gaze/head values: **O**) | 10 |
| Did P3 show behavior consistent with note-taking? | `listener_states(state='POSSIBLE_NOTE_TAKING')` + evidence | **I** | 10 |
| Who dominated? | `speech_metrics: speaking_share, turn_share, longest_turn` | **D** from **I** | 11 |
| How balanced was participation? | `speech_metrics: participation_entropy, gini` (meeting-level) | **D** from **I** | 11 |
| Speaker switch frequency | `speech_metrics: switches_per_min` | **D** from **I** | 11 |
| Where did overlap occur? | `interaction_events(type='overlap')` | **D**/**I** (overlap presence O when two VAD/ASR segments coincide; who: I) | 11 |
| Directly observed vs inferred? | `derivation` on every row; `GET /speech/provenance/{metric}` | — | all |

**"Dominated" caution:** the metric is *speaking share*. The word "dominant" is a report-language risk and is banned as a label (§1.3). Reports say "held X % of attributed speaking time".

---

## PHASE 1 — Repository audit

**Goal:** Replace every ** in this document with facts. Produce `docs/21_REPO_AUDIT.md`. No production code changes.

**Files to create:** `docs/21_REPO_AUDIT.md`, `scripts/audit/inspect_repo.sh`, `scripts/audit/dump_schema.py`
**Files to modify:** this document (replace assumptions).
**Functions/classes:** none.
**DB changes:** none (read-only introspection).
**Dependencies:** none new.

**Inputs:** repository, running Postgres, a sample processed meeting.
**Outputs:** audit report with the checklist below answered, plus the updated names in doc 20.

**Implementation sequence**

1. Backend structure

```bash
tree -L 3 backend | head -100
rg -n "class .*\(Base\)|__tablename__" backend/app/models
rg -n "@router\.(get|post|put|delete)" backend/app/api | sort
rg -n "async def .*ctx" backend/app/workers            # ARQ job signatures
rg -n "class WorkerSettings|functions *=" backend
```

2. Database: `alembic heads`, `alembic history | head`, then `dump_schema.py` prints columns/indexes/FKs for `media_assets, participant_tracks, feature_extractions, behavioral_metrics, nts_scores, nts_visual_reports, processing_jobs, meetings`. Record row counts and storage size for one long meeting, which sizes `feature_extractions` and tells us what indexing exists on `(meeting_id, participant_track_id, timestamp)`.
3. Participant tracking: where tracks are created (in `cv_extraction_worker`?), how ids are assigned, whether re-ID exists, whether track→display label (`P1`…) is stored, what happens on occlusion, and per-track visible-frame fraction on the sample meeting.
4. CV features: exact `feature_extractions` row shape (one row per frame per track? JSON blob?), timestamp unit (frame index vs ms vs seconds), bbox format, **whether face mesh/lip landmarks exist in the stored JSON** (`SELECT jsonb_object_keys(...)`), sampling rate (every frame or decimated).
5. STT: locate the faster-whisper call. Record model size, `word_timestamps`, `vad_filter`, language handling, audio extraction command, per-participant vs mixed audio, what is persisted (segments only? words?), and **where "speaking turns per participant" come from** (Ambiguity 1 and 4).
6. ARQ: list jobs, retry/timeout config, cascade mechanism in `job_service.py`, and fan-in support.
7. Annotation worker: read/write path, how bboxes per frame are looked up, what it returns, encode path (`cv2.VideoWriter` codec, any ffmpeg transcode), audio stream present in output (`ffprobe` a real output).
8. Reports: how `nts_visual_reports` UPSERT is keyed, prompt file location, summary aggregation function, `reportlab` layout module.
9. API: existing endpoint naming/versioning, auth dependencies (`get_current_org`), pagination/response schema conventions.
10. Frontend: `MeetingAnalysis` structure, `apiClient`, Recharts components reusable for timelines, video player component, interaction-matrix component, Zustand stores.
11. A/V sync reality check: on the sample meeting compare ffprobe `start_time` for audio and video streams.
12. Ground truth: identify 3–5 meetings (or clips) suitable for hand-labeling in Phase 16; measure duration, participants, camera setup, audio quality.

**Tests:** N/A. **Verification** is the audit checklist.

**Acceptance criteria**

- Every item above has an answer or "not present".
- Ambiguities 1–5 in §0.2 are resolved and Phase 6/7/8 branches chosen (see decision table below).
- This document is updated: no ** names remain for existing code.

**Decision table produced by the audit**

| Finding | Consequence |
|---|---|
| Separate per-participant audio exists | Phase 6 skipped; Phase 8 uses audio-track ownership as primary evidence, lips as validation |
| Single mixed audio, no diarization | Phase 6 cluster-lite (MVP), Phase 8 lip-primary |
| Lip landmarks stored | Phase 7 reads them, no video decode |
| Lip landmarks not stored | Phase 7 runs a **mouth-only** extraction pass (justified exception) |
| Participant IDs unstable across occlusion | Track-merge step added to Phase 8 pre-processing; note as risk |

---

## PHASE 2 — Database changes

**Goal:** Add speech schema. Additive only, no existing table is altered destructively.
*(Reconcile with doc 16: if doc 16 defines different names, doc 16 wins. Update doc 19 §3.2 to match.)*

**Files to create**
- `backend/alembic/versions/<rev>_speech_schema.py`
- `backend/app/models/speech.py` *(assumed path; follow the existing models layout)*
- `backend/app/schemas/speech.py` (Pydantic)
- `backend/app/repositories/speech_repo.py` *(assumed; follow existing data-access pattern)*
- `backend/scripts/seed_speech_reference.py` (enum reference rows, if the existing seeding script uses reference tables)

**Files to modify**
- `backend/app/models/__init__.py` (register)
- `backend/app/models/media.py` **: add `audio_start_offset_ms`, `video_start_offset_ms`, `av_offset_ms`
- `backend/app/models/meetings.py` **: add `speech_status` if `processing_jobs` does not already cover UI state

**Tables (new)**

```
pipeline_runs        id, meeting_id, stage, status, params jsonb, params_hash, code_version,
                     model_versions jsonb, input_run_ids jsonb, started_at, finished_at, error
vad_segments         id, meeting_id, run_id, start_ms, end_ms, mean_prob, method
speech_segments      id, meeting_id, run_id, start_ms, end_ms, text, language,
                     asr_avg_logprob, no_speech_prob, diar_cluster_id,
                     participant_track_id (nullable), attribution_confidence,
                     attribution_method, alt_track_id, alt_confidence, is_overlap,
                     words_per_min, derivation, evidence jsonb
speech_words         id, segment_id, idx, start_ms, end_ms, word, prob
diarization_turns    id, meeting_id, run_id, cluster_id, start_ms, end_ms, method   -- Phase 6
mouth_activity       meeting_id, run_id, participant_track_id, t_ms, mar, mar_delta,
                     lip_activity, visible bool, face_px                          -- 10 Hz
attribution_evidence id, segment_id, participant_track_id, lip_corr, lag_ms, visible_frac,
                     vad_overlap, cluster_prior, score, rank, details jsonb
track_speech_activity meeting_id, run_id, participant_track_id, t_ms, activity, lip_activity, vad_prob
prosody_windows      meeting_id, run_id, participant_track_id, t_ms, f0_hz, voiced, rms_db
listener_states      id, meeting_id, run_id, participant_track_id, start_ms, end_ms, state,
                     target_track_id, confidence, gaze_on_target_pct, derivation, evidence jsonb
interaction_events   id, meeting_id, run_id, type, from_track_id, to_track_id,
                     start_ms, end_ms, latency_ms, derivation, evidence jsonb
speech_metrics       id, meeting_id, run_id, participant_track_id (nullable = meeting-level),
                     metric_key, value double, unit, window_start_ms, window_end_ms,
                     derivation, method, evidence jsonb
speech_reports       id, meeting_id, kind, input_hash, report_json, pdf_key, created_at   -- UPSERT
```

**Indexes:** `(meeting_id, run_id, start_ms)` on time-interval tables; `(meeting_id, run_id, participant_track_id, t_ms)` on grid tables; `(meeting_id, metric_key)` on `speech_metrics`; unique `(meeting_id, stage, params_hash)` on succeeded `pipeline_runs` (partial index).
**Constraints:** `CHECK (end_ms > start_ms)`; `CHECK (attribution_confidence BETWEEN 0 AND 1)`; `derivation IN ('observed','derived','inferred')`; enum types or check constraints for `state`, `type`.
**Partitioning:** not now. Revisit if `mouth_activity`/`prosody_windows` exceed ~50 M rows (Phase 17).

**Implementation sequence:** models → Alembic autogenerate → hand-review (indexes, checks) → migrate on a copy of production data → downgrade test → repos → schemas.

**Reuse:** existing Alembic setup, async session factory, `get_current_org` filtering (every repo query filters by org through `meetings`).
**Dependencies:** none.

**Inputs:** Phase 1 audit. **Outputs:** migrated schema, ORM models, repos.

**Tests:** migration up/down on empty and populated DB; constraint tests (bad confidence, `end_ms<=start_ms`); org isolation test (org A cannot read org B rows through repos); insert/read throughput test for 1 M `prosody_windows` rows.

**Acceptance:** `alembic upgrade head` and `downgrade -1` succeed; existing tests still green; no existing table dropped or retyped; org isolation test passes.

---

## PHASE 3 — Audio preprocessing

**Goal:** One normalized 16 kHz mono WAV per meeting on the video clock, and a recorded A/V offset.

**Files to create**
- `backend/app/services/audio/ffmpeg_utils.py`: `probe_streams()`, `extract_audio()`, `measure_av_offset()`
- `backend/app/workers/audio_preprocess_worker.py`: ARQ job `audio_preprocess(ctx, meeting_id)`
- `backend/tests/audio/test_ffmpeg_utils.py`

**Files to modify**
- `backend/app/services/job_service.py`: register stage + cascade edge
- Existing STT worker: **only** switch its audio input to the new asset if the audit shows it re-extracts audio itself (reuse rather than duplicate extraction)

**Functions**

```python
def probe_streams(path) -> StreamInfo          # ffprobe JSON: start_time, duration, codec, sample_rate
def extract_audio(video_path, out_wav, *, sample_rate=16000, mono=True, loudnorm=False) -> None
    # ffmpeg -i in -vn -ac 1 -ar 16000 -af "aresample=async=1:first_pts=0" -c:a pcm_s16le out.wav
def compute_av_offset_ms(info: StreamInfo) -> int   # (audio.start_time - video.start_time) * 1000
```

The offset is stored in `media_assets.av_offset_ms`. Apply it as: `t_video_ms = t_audio_ms + av_offset_ms`. Decide the exact sign and verify it with the sync fixture below before anything else consumes it.

**DB changes:** writes `media_assets` offsets; registers an `audio_16k` `media_assets` row (MinIO key); `pipeline_runs` row.
**Dependencies:** ffmpeg/ffprobe (already present).
**Inputs:** source video asset. **Outputs:** `audio_16k.wav` in MinIO, offsets in DB.

**Sequence:** probe → extract → measure offset → upload → persist → enqueue VAD.

**Tests:** fixture video with a click at a known frame plus a beep at a known time; assert measured offset within ±20 ms; VFR fixture; no-audio-stream video → stage `succeeded` with `has_audio=false`, and downstream speech stages are skipped, not failed.

**Acceptance:** WAV is 16 kHz mono PCM; offset recorded; the sync fixture aligns to ≤ 40 ms; re-running is idempotent (same `params_hash` → no duplicate asset).

---

## PHASE 4 — VAD

**Goal:** Speech/non-speech intervals independent of ASR, used for clamping segment boundaries, silence handling and attribution correlation.

**Files to create**
- `backend/app/services/speech/vad.py`: `detect_speech(wav_path, *, threshold, min_speech_ms, min_silence_ms) -> list[Interval]`
- `backend/app/workers/vad_worker.py`: ARQ job `vad(ctx, meeting_id)`

**Files to modify:** `job_service.py`.
**Reuse:** faster-whisper already ships a Silero VAD (`faster_whisper.vad.get_speech_timestamps`), so **no new dependency for MVP**. Fallback: `webrtcvad` if the bundled VAD is unavailable in the installed version. Verify in the audit.

**Functions:** `detect_speech`, `merge_close_intervals(gap_ms=200)`, `to_grid(intervals, hop_ms=100) -> ndarray` (0/1 vad_prob envelope for Phase 8).

**DB changes:** writes `vad_segments`.
**Inputs:** `audio_16k.wav`. **Outputs:** `vad_segments` rows, 10 Hz envelope (recomputable, not stored, or stored in `track_speech_activity` after attribution).

**Sequence:** load audio (streaming, 30 s blocks) → VAD → merge → persist.
**Parameters (defaults, tune on labeled set):** threshold 0.5, min speech 250 ms, min silence 300 ms, pad 100 ms.

**Tests:** synthetic speech/silence WAV with known boundaries → boundaries within ±100 ms; pure silence → 0 segments; music/noise fixture (documented false-positive rate); very long file memory bound.

**Acceptance:** F1 of speech frames ≥ 0.9 on the labeled clips *(target, validate)*; runtime < 0.05× realtime on CPU; memory bounded.

---

## PHASE 5 — STT timestamp extraction

**Goal:** Persist word-level timestamps and confidence from the **existing** faster-whisper integration. Do not add a second STT run.

**Files to create:** `backend/app/services/speech/transcript_normalizer.py`
**Files to modify:** the **existing STT worker**: enable `word_timestamps=True`, pass the Phase 4 VAD result (or `vad_filter=True`), `condition_on_previous_text=False` (limits hallucination carry-over); persist segments + words through `speech_repo`. Keep the current speaking-turn code path working during migration, reading from the same source rows.

**Functions**
```python
def normalize_segments(raw_segments, vad_intervals) -> list[SegmentDraft]
    # clamp start/end into VAD intervals (±150 ms), drop segments with no_speech_prob>0.6 and
    # avg_logprob<-1.5 (configurable, flagged not deleted: keep row with `dropped=true` in evidence),
    # split segments at long internal pauses (>1.0 s) using word gaps
def apply_av_offset(draft, av_offset_ms) -> draft
```

**DB changes:** writes `speech_segments` (unattributed: `participant_track_id NULL`) and `speech_words`.
**Dependencies:** none new (faster-whisper already installed).
**Inputs:** `audio_16k.wav`, VAD intervals. **Outputs:** `speech_segments`, `speech_words`.

**Sequence:** run transcribe on the already-normalized WAV → normalize → offset → persist → cascade.

**Known risk:** Whisper word timestamps drift by 100–300 ms and can hallucinate on silence. Mitigations: VAD clamping (here), forced alignment (E4, only if needed).

**Tests:** golden transcript on a TTS fixture with known word times (assert median word-time error ≤ 250 ms); silence-only audio → 0 segments; non-English fixture preserves Unicode; idempotent re-run; **regression test that old speaking-turn output is unchanged** for a stored meeting.

**Acceptance:** words persisted with `s_ms < e_ms`, monotonic; VAD-clamped; hallucination filter flags recorded; existing speaking-ratio dashboard unchanged.

---

## PHASE 6 — Audio diarization (MVP-lite; neural is optional)

**Goal:** Audio-only grouping of segments into speaker *clusters* (`diar_cluster_id`). This is a **prior**, not the attribution decision.

**Branch by Phase 1 finding**
- **Per-participant audio tracks exist:** skip this phase. `diar_cluster_id = track id`.
- **Single mixed track (default MVP branch):** cluster-lite as below.

**Files to create**
- `backend/app/services/speech/cluster_lite.py`
- `backend/app/workers/audio_diarization_worker.py` (job is a **no-op success** when skipped)

**Functions**
```python
def segment_features(wav, seg) -> ndarray      # MFCC(20) mean/std + f0 median/IQR + spectral centroid
def cluster_segments(feats, n_speakers_hint: int | None) -> labels, silhouette
    # AgglomerativeClustering(ward); n_speakers_hint = distinct visible participant_tracks
def flag_uncertain(labels, silhouette) -> per-segment cluster_confidence
```

`n_speakers_hint` comes from the number of participant tracks, so no speaker-count estimation is needed. Clusters shorter than 1.5 s of speech are unreliable and must be marked `cluster_confidence=low`.

**DB changes:** writes `diarization_turns` and `speech_segments.diar_cluster_id`.
**Dependencies:** `scikit-learn`, `librosa` (or `python_speech_features`). Modest install cost. **No** torch requirement.
**Inputs:** WAV, segments. **Outputs:** cluster labels + confidence.

**Sequence:** features per segment → cluster → persist → cascade.

**Honesty note:** hand-crafted MFCC clustering is weak on similar voices and short turns. It is used only as a **consistency prior** (segments in one cluster should map to the same track) inside Phase 8, never as sole evidence. If the labeled evaluation shows it hurts, disable it (`use_cluster_prior=false`) rather than tune it further.

**Optional E1/E2 (later):** replace `cluster_lite` with `pyannote.audio` or ECAPA-TDNN embeddings behind the same interface (`cluster_segments`). Requires torch, model weights and (for pyannote) a license/token, all to be decided at that time.

**Tests:** two-voice synthetic fixture (distinct pitches) → 2 clusters, purity ≥ 0.9; identical voices → low silhouette → `low` confidence flag; skip branch works.

**Acceptance:** interface stable so E1/E2 are drop-in; ablation flag exists; clusters never displayed as identities.

---

## PHASE 7 — Mouth/lip activity extraction

**Goal:** Per-track, per-100 ms lip movement signal.

**Branch by Phase 1 finding**
- **Lip landmarks already stored:** read them; no video decode. (Preferred.)
- **Not stored (likely):** run a **mouth-only pass**. This is the one deliberate exception to "avoid rerunning CV," and it is **additive** (it does not recompute any existing feature): decode video at 10–15 fps, crop each existing track's face bbox from stored `feature_extractions`, run a face-mesh model on the crop only, emit lip landmarks. It costs a fraction of the original CV pass because it runs at 10–15 fps on small crops and does not repeat detection or tracking.

**Files to create**
- `backend/app/workers/mouth_activity_worker.py`: ARQ job `mouth_activity(ctx, meeting_id)`
- `backend/app/services/speech/mouth_features.py`
- `backend/scripts/mouth_mesh.js` **or** `backend/app/services/speech/mouth_mesh.py`: pick one after the audit. Prefer reusing `@vladmandic/human` (`face.mesh`) through the existing Node bridge pattern. Use MediaPipe FaceMesh (Python) only if Human's mesh is not enabled/available. One less runtime is worth a lot.

**Files to modify:** `job_service.py`. If landmarks can be emitted by the existing `human_cv_script.js` for **future** uploads with a config flag, add the flag (default on) so new meetings never need the extra pass; old meetings use the additive pass.

**Functions**
```python
def mouth_aspect_ratio(lm) -> float               # inner-lip height / mouth width, head-pose-normalized
def lip_activity_signal(mar_series, fps) -> ndarray
    # high-pass (remove static open-mouth), |d(MAR)/dt|, robust-normalize per track (median/MAD),
    # smooth 100–200 ms, clip 0..1
def visibility_mask(track, t) -> bool             # face_px >= min, |yaw|<70°, not occluded
```

Head pose (yaw/pitch/roll) from existing features normalizes MAR: at large yaw the apparent mouth width shrinks. Mark `visible=false` beyond limits instead of emitting noise.

**DB changes:** writes `mouth_activity` (10 Hz).
**Dependencies:** none new if using the Human mesh; `mediapipe` only if the fallback is chosen.
**Inputs:** video, `feature_extractions` bboxes, head pose, tracks. **Outputs:** `mouth_activity`.

**Sequence:** load bboxes per track → sample at 10–15 fps → mesh on crops → MAR → normalize → persist.

**Tests:** synthetic animated-mouth video (open/close at known times) → activity peaks align ±100 ms; closed-mouth/static video → activity ≈ 0; head turned away → `visible=false`; small face → `visible=false`; runtime benchmark vs original CV pass.

**Acceptance:** on labeled clips, lip activity's correlation with human-labeled speech intervals is measurable and reported per participant (no absolute threshold decided here); `visible` fraction reported; runtime ≤ ~25 % of `cv_extraction` *(target, validate)*.

---

## PHASE 8 — Audio-visual speaker attribution

**Goal:** For each `speech_segment`, decide `participant_track_id` (or unknown) with calibrated confidence and stored evidence.
*(Reconcile the algorithm with doc 12; the below is the working default.)*

**Files to create**
- `backend/app/services/speech/attribution.py`
- `backend/app/workers/speaker_attribution_worker.py`: ARQ job `speaker_attribution(ctx, meeting_id)`
- `backend/app/services/speech/calibration.py`

**Functions**
```python
def audio_envelope(wav, seg, hop_ms=100) -> ndarray          # log-energy ∩ VAD mask
def lip_vs_audio_score(lip: ndarray, env: ndarray, max_lag_ms=200) -> (corr, lag_ms)
    # normalized cross-correlation over ±200 ms lag; require ≥ 8 visible samples
def score_track_for_segment(seg, track) -> TrackScore
    # score = w1*corr_pos + w2*vad_overlap + w3*visible_frac + w4*cluster_prior
def attribute_segment(seg, scores) -> Attribution
    # softmax over tracks (+ "none" pseudo-candidate); best, runner-up, margin
def resolve_cluster_consistency(attributions) -> attributions
    # Hungarian mapping cluster→track by summed evidence; nudge conflicting segments; never flip confident ones
def calibrate(score) -> confidence   # isotonic/Platt fit on labeled set (Phase 16); before labels exist, monotone mapping, marked `uncalibrated` in evidence
```

**Decision rules (defaults, tune on labeled set)**

| Situation | Outcome |
|---|---|
| Best score high, margin ≥ 0.10 | attributed, `SPEAKING` tier per confidence |
| Top-2 margin < 0.10 | store `alt_track_id`/`alt_confidence`, renderer shows candidates |
| No track has ≥ 8 visible samples in segment | `participant_track_id = NULL` (unknown / possibly off-screen) |
| Best confidence < 0.35 | `NULL`, evidence retained |
| Single visible track and speech present | attributed with reduced confidence (cap 0.7) because the person may be lip-visible but silent while an off-screen speaker talks |
| Two segments overlap in time | attribute each independently; `is_overlap=true` |

If per-participant audio exists: `score = audio-track energy share` dominates; lips validate.

**Evidence stored:** one `attribution_evidence` row per (segment, track) so any label can be explained: `lip_corr, lag_ms, visible_frac, vad_overlap, cluster_prior, score, rank`. `speech_segments.evidence` summarizes; `derivation='inferred'`.

**DB changes:** updates `speech_segments` attribution columns (new run → new rows, or update within the run's rows, decide in audit for immutability vs update-in-place: prefer new rows), writes `attribution_evidence`, `track_speech_activity`.
**Dependencies:** `numpy`, `scipy`. Nothing heavy.
**Inputs:** `speech_segments`, `mouth_activity`, VAD, cluster labels, tracks. **Outputs:** attributed segments + evidence.

**Sequence:** load all → per segment compute envelopes/scores → attribute → cluster consistency → calibrate → persist evidence → persist `track_speech_activity`.

**Optional E3:** SyncNet/TalkNet replaces `lip_vs_audio_score` behind the same function signature, run only on segments where MVP confidence < threshold, to bound cost.

**Tests:** synthetic 2-person fixture with known speaker sequence → accuracy ≥ target; listener-with-moving-lips distractor (e.g., chewing) fixture documents the known failure; one person off-screen; overlapping speech; time-shift fixture (±150 ms audio offset) checks lag search; determinism (same inputs → same outputs); golden evidence rows.

**Acceptance:** on the labeled set, report frame-level speaker accuracy, unknown rate, precision at confidence ≥ 0.75, and a reliability (calibration) table. Numeric acceptance target to be **set from the labeled baseline, not assumed here**. Every attributed segment has explainable evidence rows. Confidence buckets are monotone with empirical accuracy.

---

## PHASE 9 — Speech / prosody analysis

**Goal:** Pitch, energy, speaking rate per attributed speaker, and per-speaker distributions.

**Files to create**
- `backend/app/services/speech/prosody.py`
- `backend/app/workers/prosody_worker.py`

**Functions**
```python
def extract_f0(wav, hop_ms=10) -> (f0, voiced)      # Praat via parselmouth (fast, robust); octave-jump filter
def per_track_prosody(wav, attributed_segments) -> prosody_windows
    # sample f0/rms at 100 ms; exclude overlap ticks and low-confidence attribution (<0.5) from pitch stats
def speaking_rate(words, vad) -> dict      # articulation_wpm (excl. pauses ≥250 ms), overall_wpm, pause_ratio
def pitch_distribution(f0_track) -> dict   # p10/p50/p90 Hz, range in semitones re: track median
def segment_wpm(segment) -> float | None   # same rules as doc 19 §8.4
```

Pitch is computed on the mixed audio at attributed times only. Pitch statistics are **descriptive of the attributed voice signal**, not an emotion or personality measure. Expressed in semitones for range so different voices compare fairly.

**DB changes:** writes `prosody_windows`, `speech_segments.words_per_min`, and `speech_metrics` rows (`f0_p10/p50/p90`, `f0_range_st`, `articulation_wpm`, `overall_wpm`, `pause_ratio`), with `derivation='derived'` and evidence listing the segment ids/thresholds used.
**Dependencies:** `praat-parselmouth` (small wheel). `librosa.pyin` is slower and is not needed.
**Inputs:** WAV, attributed segments, words. **Outputs:** prosody windows + metrics.

**Sequence:** f0 over whole WAV once → slice by attributed segments → windows → distributions → rates → persist.

**Tests:** synthetic sine/chirp with known f0 → error < 3 %; octave-error case; silence/unvoiced → NULL not 0; rate fixture with known words/time; overlap exclusion test; low-confidence exclusion test; metrics evidence lists real segment ids.

**Acceptance:** pitch errors within tolerance on synthetic data; metrics reproducible; each metric's `evidence` reproduces its value when recomputed from the cited rows (a test does exactly this).

---

## PHASE 10 — Listener behavior analysis

**Goal:** For non-speaking participants during another's speech, emit observations (never traits) with evidence.
*(Reconcile with doc 14.)*

**Files to create**
- `backend/app/services/speech/listener.py`
- `backend/app/workers/listener_analysis_worker.py`

**Reuse:** existing `feature_extractions` (gaze bearing, head yaw/pitch/roll, body keypoints, hands) and existing `participant_tracks`. **No new CV.** The frontend already renders these features, so the semantics for angles are established. Confirm coordinate conventions in the audit.

**Functions**
```python
def target_direction(listener_bbox, speaker_bbox) -> bearing_deg      # 2D image-plane approximation
def orientation_score(gaze, head_yaw, target_bearing, tol_deg) -> 0..1
def gaze_on_target_pct(frames, window_s=3.0) -> float | None          # min 15 valid frames
def detect_note_taking(frames) -> Interval[]                          # head pitch down ≥θ1 AND gaze down AND wrist keypoint motion below shoulder line, sustained ≥3 s
def detect_looking_away(frames, speaker_track) -> Interval[]          # head+gaze off target beyond θ2 for ≥1.5 s, not note-taking
def detect_distraction_pattern(frames) -> Interval[]                  # sustained off-target AND repeated head turns/hand-to-face or device-like posture; conservative
def merge_and_hysteresis(states, min_ms=1000, bridge_ms=400) -> list[ListenerState]
```

State priority when patterns overlap: `POSSIBLE_NOTE_TAKING` > `SPEAKER_ORIENTED` > `LOOKING_AWAY` > `POSSIBLE_DISTRACTION` (distraction requires stricter evidence than looking away).

**Constraints**
- States are only evaluated while an attributed speaker (conf ≥ 0.5) other than the listener is active.
- Camera geometry matters: on a single front camera, "toward speaker" is approximate. Store `method='image_plane_v1'` and a `geometry_caveat` in evidence.
- Every state stores its numeric inputs (`head_pitch_deg`, `gaze_pct`, `off_target_s`), `derivation='inferred'`, `confidence` from margin over thresholds. The doc 19 renderer displays those inputs.
- Wording is fixed by the enum (no trait words).

**DB changes:** writes `listener_states`; meeting-level `speech_metrics`, e.g. `oriented_pct_while_others_speak` per track.
**Dependencies:** `numpy`, `scipy`.
**Inputs:** `feature_extractions`, attributed `speech_segments`. **Outputs:** `listener_states`, metrics.

**Tests:** synthetic pose/gaze time series for each pattern with known intervals; boundary cases (glance vs sustained); missing features → `NULL`/no state, never a guess; frame-drop robustness; priority tests; test that a speaker never receives a listener state during their own speech.

**Acceptance:** each state reproducible from stored evidence; thresholds documented in `params`; precision/recall on hand-labeled note-taking and looking-away intervals reported; **no** state is emitted with insufficient valid frames. The "Did P3 show behavior consistent with note-taking?" question is answered with intervals, the observed values behind them, and `derivation='inferred'`.

---

## PHASE 11 — Multimodal fusion (interaction metrics and participation)

**Goal:** Turn attributed segments plus listener states into turn, overlap, interruption, response and balance metrics, all with provenance.
*(Reconcile with docs 13/15.)*

**Files to create**
- `backend/app/services/speech/fusion.py`
- `backend/app/services/speech/turns.py`
- `backend/app/workers/speech_fusion_worker.py`

**Reuse:** the existing interaction-matrix computation ("who talks after whom") and its dashboard component. Extend its input to the new attributed segments rather than reimplementing. Keep its output shape stable; add new fields.

**Functions and definitions (defaults, configurable, stored in `params`)**

```python
def build_turns(segments, gap_ms=1000) -> list[Turn]
    # merge consecutive same-track segments with gap < gap_ms; unknown-speaker segments stay separate
def detect_overlaps(segments, min_ms=200) -> events
    # any two attributed segments (different tracks) intersecting ≥200 ms; also records
    # unattributed overlaps (VAD+multiple ASR segments) as type='overlap' with track NULL
def classify_interruption(prev_turn, new_turn) -> 'interruption' | 'backchannel' | 'overlap_other' | None
    # new turn starts while prev still active AND prev ends within 2 s AND new speaker holds ≥ 1.5 s or ≥ 4 words → interruption
    # ≤1 s and ≤3 words (e.g. "yeah") → backchannel (not counted as interruption)
def response_events(turns, max_gap_ms=3000) -> events
    # from_track = previous speaker, to_track = new speaker, latency_ms = new.start - prev.end (negative = overlap)
def participation_metrics(turns) -> metrics
    # speaking_time_ms, speaking_share, turn_count, turn_share, longest_turn_ms, mean_turn_ms
    # meeting-level: participation_entropy (normalized), gini, switches_per_min
def response_matrix(events) -> (from,to)->count, median_latency
```

Interruption definitions are **conventions**, not facts. Each `interaction_events` row stores `definition_version` and the thresholds in `params`, and the API/report text says "overlapping onset meeting criteria X". Never "interrupted rudely".

**Provenance:** every event's `evidence` lists the segment ids and start/end times used; every metric row lists the event/segment ids or the query window. Derivation class = weakest input (attributed identity ⇒ `inferred`; unattributed overlap presence ⇒ `derived`).

**DB changes:** writes `interaction_events`, `speech_metrics`; optionally feeds `behavioral_metrics`/`nts_scores` **only if** the existing schema has an obvious slot (audit), otherwise leave existing tables untouched.
**Dependencies:** `numpy`, `pandas` (only if already present).
**Inputs:** attributed segments, listener states. **Outputs:** events + metrics.

**Tests:** hand-built turn sequences with known interruption/backchannel/overlap/latency; balanced vs one-sided fixtures for entropy/gini; unknown-speaker handling (excluded from per-person shares but reported as `unattributed_speech_ms`); metrics reproduce from cited evidence; matrix shape backward compatible.

**Acceptance:** the metric set covers every row of §3; all events/metrics have provenance; unattributed speech is **reported, never silently dropped or redistributed**; metrics change monotonically when confidence floor is raised (sanity test).

---

## PHASE 12 — API integration

**Goal:** Expose everything through endpoints that follow existing conventions.

**Files to create**
- `backend/app/api/v1/speech.py` *(assumed path/versioning; follow the audit)*
- `backend/app/services/speech/query_service.py`
- `backend/tests/api/test_speech_api.py`

**Files to modify:** router registration; existing job trigger endpoint (add `speech` pipeline option / status).

**Endpoints** (all under `/meetings/{meeting_id}/speech`, all org-scoped via existing `get_current_org`)

| Method + path | Returns |
|---|---|
| `POST /run` | Enqueue speech pipeline (idempotent via `job_service`) |
| `GET /status` | Per-stage status from `pipeline_runs` / `processing_jobs` |
| `GET /at?t=84.5` | Active segments, speakers + confidence, listener states, overlap flag at time |
| `GET /segments?from&to&track&min_conf` | Paginated transcript segments with words optional |
| `GET /timeline?bucket_ms=` | Swimlane data (per track speaking intervals, listener intervals) |
| `GET /metrics?track&keys` | `speech_metrics` rows |
| `GET /interactions?type=` | Events + response matrix |
| `GET /listeners?track&from&to` | `listener_states` with evidence |
| `GET /provenance/{metric_id or event_id}` | Run ids, method, evidence, derivation, source rows |
| `GET /annotated-video` | Presigned GET + manifest URL (extend existing annotated-video endpoint instead if it exists) |

All responses include `derivation` and `run_id`. `/at` accepts seconds and converts to integer ms internally.

**Query for `/at` (indexed):**
```sql
SELECT * FROM speech_segments
WHERE meeting_id=:m AND run_id=:r AND start_ms <= :t AND end_ms > :t;
```
Because a segment can span long, add `GiST` on `int4range(start_ms,end_ms)` if profiling shows a scan.

**Dependencies:** none. **Inputs:** DB. **Outputs:** JSON.

**Tests:** contract tests per endpoint; auth/org isolation; pagination; `/at` boundary semantics (`start` inclusive, `end` exclusive); provenance endpoint returns rows that recompute the metric; performance test (`/at` p95 < 50 ms on 10 k segments).

**Acceptance:** all 15 questions in §3 are answerable through these endpoints; OpenAPI schema published; no endpoint returns data from another org.

---

## PHASE 13 — Frontend dashboard

**Goal:** Extend `MeetingAnalysis` with speech views, reusing existing Recharts, video player, polling and stores.

**Files to create** *(paths assumed; follow existing frontend structure)*
- `frontend/src/features/speech/SpeechTab.tsx`
- `frontend/src/features/speech/SpeechTimeline.tsx`: swimlane per participant (speaking, listener states); custom SVG/canvas, since Recharts is weak for interval swimlanes
- `frontend/src/features/speech/TranscriptPanel.tsx`: click-to-seek, follows playback, low-confidence styling
- `frontend/src/features/speech/ParticipationCharts.tsx`: share, turns, balance (Recharts)
- `frontend/src/features/speech/ProsodyPanel.tsx`: pitch distribution (box/violin-style via Recharts), rate
- `frontend/src/features/speech/InteractionPanel.tsx`: response matrix (**reuse** existing interaction-matrix component), interruptions, overlaps
- `frontend/src/features/speech/ListenerPanel.tsx`
- `frontend/src/features/speech/ProvenanceBadge.tsx`: O / D / I badge + popover fed by `/provenance`
- `frontend/src/features/speech/WhoSpokeAt.tsx`: time input → `/at`
- `frontend/src/stores/speechStore.ts` (Zustand)
- `frontend/src/api/speech.ts` (uses existing `apiClient`)
- `frontend/src/hooks/useSpeechPipelineStatus.ts` (wraps existing `useJobPolling`)

**Files to modify:** `MeetingAnalysis` (add tab), routing if needed, existing video player (add WebVTT track + seek API + annotated-video toggle).

**UI rules**
- Every metric shows a provenance badge; inferred values use dashed styling consistent with doc 19.
- Copy uses the closed vocabulary; the "dominance" chart is titled "Share of attributed speaking time".
- Unattributed speech is a visible category in charts.

**Dependencies:** none new (Recharts, Tailwind, Zustand exist).
**Inputs:** Phase 12 API. **Outputs:** UI.

**Sequence:** API client + store → timeline + transcript with video sync → participation/prosody charts → interaction/listener panels → provenance → annotated-video toggle.

**Tests:** component tests (Vitest + Testing Library); MSW-mocked API; timeline renders overlapping intervals; transcript-seek round-trip; label lint on strings; accessibility (labels + not color-only); Playwright smoke: open a processed meeting, click a transcript line, video seeks.

**Acceptance:** all §3 questions are answerable in the UI; time sync between video, timeline, transcript within one tick (100 ms); polling reuses existing hook; no forbidden vocabulary.

---

## PHASE 14 — Annotated video

**Goal:** Implement **doc 19** in the existing `video_annotation_worker.py`.

**Files to create:** the `backend/app/annotation/speech_overlay/` package as specified in doc 19 §11.
**Files to modify:** `video_annotation_worker.py` (additive; see doc 19 §11.8), job options, annotated-video endpoint (return manifest + VTT).
**Reuse:** all current OpenCV drawing (boxes, skeletons, head rotation/emotion), CV feature loader, MinIO upload, presigned GET, frontend playback component.

**Sequence**
1. Confirm/adjust the "return bbox per track per frame" seam in the existing worker.
2. Implement `loader`, `alignment`, `timeline` with unit tests, no rendering yet.
3. Implement `style`, `text_cache`, `layout`, `renderer`.
4. Golden-frame tests on the synthetic clip.
5. Encoding path/audio mux changes (only if the audit shows they are needed).
6. Manifest + VTT.
7. Benchmark; only then consider chunked parallelism.

**DB changes:** none beyond Phase 2. **Dependencies:** `Pillow` (likely present through reportlab; verify), a bundled Noto font.
**Inputs/Outputs/Tests/Acceptance:** doc 19 §3, §13, §14.

---

## PHASE 15 — LLM report generation

**Goal:** Speech/interaction/listener narrative that cannot outrun the evidence.

**Files to create**
- `backend/app/services/reports/speech_summary.py`: aggregates DB metrics into compact JSON
- `backend/app/services/reports/speech_prompt.py`
- `backend/app/services/reports/speech_validator.py`
- `backend/app/workers/speech_report_worker.py`

**Files to modify:** the existing report generator/PDF module. **Reuse** the Groq client, model config, JSON-cleaning fixes from Phase 10 history (no `response_format` strictness), `reportlab` layout, and the UPSERT cache pattern (`speech_reports`, same `INSERT … ON CONFLICT DO UPDATE` approach). Add a speech section to the existing PDF, not a separate one.

**Functions**
```python
def build_speech_evidence(meeting_id) -> dict
    # {metric_key: {"value":..., "unit":..., "derivation":..., "id": metric_id, "confidence_note":...}}
    # includes unattributed_speech_ms, attribution_confidence distribution, coverage caveats
def render_prompt(evidence) -> (system, user)
def validate_report(report_json, evidence) -> issues
    # every number in the narrative must match a cited metric id; every claim must carry
    # "observed" | "derived" | "inferred"; banned vocabulary regex; no metric ids that don't exist
```

**Prompt rules (system prompt content)**
1. Only use provided metrics; cite metric ids per statement.
2. Separate sections: *Directly observed*, *Derived from observed data*, *Inferred (heuristic)*.
3. Use hedged language for inferred items ("the recorded head and gaze signals were consistent with …").
4. Forbidden: personality/trait/emotion/intent claims; words such as *dominant person, disengaged, rude, uninterested*.
5. State limitations: attribution confidence, unknown-speaker share, camera geometry caveat, threshold definitions for interruption.
6. If evidence is insufficient, say so rather than infer.

**Post-validation loop:** if `validate_report` finds issues, retry once with the issue list; if still failing, generate a deterministic **template-only** report from the metrics (no LLM prose) and mark `llm_status='fallback_template'`.

**DB changes:** `speech_reports` upsert keyed by `(meeting_id, kind, input_hash)`; `input_hash` covers evidence JSON + prompt version + model id, so unchanged evidence never re-calls the LLM.
**Dependencies:** none new.
**Inputs:** `speech_metrics`, `interaction_events`, `listener_states`, run metadata. **Outputs:** report JSON + PDF section.

**Tests:** validator catches fabricated numbers / missing citations / banned words (adversarial fixtures); mocked-LLM report round-trip; cache hit on unchanged inputs; fallback path; PDF renders with provenance legend; token budget test for a 2 h meeting summary.

**Acceptance:** 100 % of numeric claims in a sample report trace to metric ids; provenance section present; no banned vocabulary; unchanged inputs do not trigger LLM calls.

---

## PHASE 16 — Testing

**Goal:** Prove correctness where possible, measure accuracy where it's empirical.

**Files to create**
- `backend/tests/speech/…` (per-phase suites listed above)
- `backend/tests/fixtures/synth/` + `backend/scripts/make_synthetic_meetings.py`: generates a video (moving-mouth shapes or pre-recorded talking-head clips), audio (TTS or recorded), and ground-truth JSON of speakers/turns/pitch/listener behavior
- `backend/tests/eval/label_schema.json`, `backend/scripts/eval/score_attribution.py`, `score_vad.py`, `score_listener.py`
- `docs/22_EVALUATION_PROTOCOL.md`
- `.github/workflows/speech.yml` *(or existing CI config)*

**Test layers**

| Layer | Content |
|---|---|
| Unit | Pure functions (turns, interruption rules, entropy, f0 windows, tick painting, layout) |
| Property | Metric invariants: shares sum to 1 (+unattributed), no negative durations, event intervals inside meeting, listener never overlaps own speech |
| Integration | Full cascade on the synthetic meeting → DB rows match ground truth; idempotent re-run; failure/retry of each stage; partial data (no audio, no speech, single speaker) |
| Regression | Existing endpoints/dashboards/PDF unchanged with speech stages disabled; CV/STT outputs unchanged (hash of stored rows before/after) |
| Contract | API schemas; provenance endpoint recomputation |
| Empirical eval | **Human-labeled** 3–5 clips (speaker intervals, note-taking/looking-away intervals): frame-level speaker accuracy, unknown rate, calibration table, interruption precision/recall, VAD F1, word-time error |
| Alignment | A/V offset fixtures, VFR fixture |
| Visual | Golden frames for the overlay (doc 19 §14) |
| Language lint | Denylist scan on code constants, API responses, UI strings, report output |
| Question suite | One automated test per row in §3 that calls the API and checks the answer on the synthetic meeting |

**Acceptance:** CI green; the question suite passes; evaluation report generated and stored; accuracy numbers recorded as the baseline that gates Phase E tracks; no test needs network or GPU.

---

## PHASE 17 — Performance optimization

**Goal:** Meet budgets without changing results.

**Files to modify:** as profiling dictates. Candidate hot spots below.

| Area | Action |
|---|---|
| Bulk writes | `INSERT … SELECT`/`COPY` (asyncpg `copy_records_to_table`) for `mouth_activity`, `prosody_windows`; batch 10 k rows |
| Reads | Server-side cursors + `np.fromiter`; only needed columns; composite indexes from Phase 2; consider `BRIN` on `t_ms` for grid tables |
| Table growth | Partition grid tables by `meeting_id` hash if > ~50 M rows; retention job for superseded runs |
| Audio | Stream in blocks; compute f0 once per file; reuse the 16 kHz WAV across VAD/STT/prosody/attribution |
| Mouth pass | 10–15 fps crops only; batch crops per model call; skip invisible/small faces early |
| Attribution | Vectorize correlation (FFT-based `scipy.signal.correlate`); prune tracks with `visible_frac < 0.2` before scoring |
| Worker concurrency | Separate ARQ queues/`max_jobs` for CPU-heavy (mouth, prosody, render) vs light jobs; avoid starving the existing upload/CV queue |
| Caching | `pipeline_runs.params_hash` skips unchanged stages; render cache by input hash (doc 19 §12.3); report cache by evidence hash |
| Video | Doc 19 §12: tick grid, sprite cache, ROI blend, threaded reader/renderer/writer, raw-frame ffmpeg pipe; parallel chunks only if needed |
| API | `/at` and `/timeline` covered by indexes; response caching for finished meetings (ETag keyed by run ids) |
| Frontend | Virtualize transcript list; downsample timeline by bucket on server; lazy-load tabs |

**Targets (to validate, not measured):**

| Stage | Target (1 h meeting, 4 tracks, CPU) |
|---|---|
| Audio preprocess | < 2 min |
| VAD | < 2 min |
| Mouth-only pass (if needed) | ≤ 25 % of CV extraction time |
| Attribution | < 3 min |
| Prosody | < 3 min |
| Fusion | < 30 s |
| Annotated video | ≤ 1.25× current render time |
| Peak memory per job | < 2 GB |

**Method:** benchmark harness with stage timers written into `pipeline_runs.params.timings`; profile with `py-spy`/`pyinstrument`; change one thing at a time; confirm outputs are byte- or tolerance-identical via the golden tests.

**Acceptance:** targets met on the benchmark fixture, or documented deviations; result-equivalence tests pass after every optimization; no regression in the existing pipeline's runtime.

---

## Reuse map (do not rewrite)

| Existing component (Known) | Reuse in |
|---|---|
| `job_service.py` idempotent enqueue + cascade | Phases 3–8, 9–11, 15 |
| `processing_jobs`, `useJobPolling`, `JobStatusBadge` | 12, 13 |
| `participant_tracks` | 7, 8, 10, 11 (identity; never re-detect people) |
| `feature_extractions` (bbox, head pose, gaze, pose, hands) | 7 (bbox/head pose), 10, 14 |
| `cv_extraction_worker` + Node bridge pattern | 7 (mouth mesh), if needed |
| `faster-whisper` integration | 4, 5 (VAD, word timestamps) |
| Existing speaking-turn/ratio/interaction-matrix code + dashboard components | 11, 13 |
| `video_annotation_worker.py` drawing, MinIO upload, presigned GET | 14 |
| Groq client, prompt/JSON fixes, `reportlab`, `nts_visual_reports` UPSERT pattern | 15 |
| `apiClient`, Zustand, Recharts, `MeetingAnalysis` | 13 |
| Alembic, async session factory, `get_current_org` | 2, 12 |
| Docker Compose | add nothing for MVP; `libsndfile1` may be needed for audio libs; add to the backend image only |

## Risk register

| Risk | Impact | Mitigation |
|---|---|---|
| Lip landmarks not stored | Extra CV pass | Phase 7 branch; flag future uploads to emit landmarks |
| Participant ID switches after occlusion | Wrong attribution | Track-merge step; report `track_fragmentation`; lower confidence |
| Mixed-audio overlap corrupts pitch/rate | Bad metrics | Exclude overlap windows; mark `pitch_excluded_overlap_ms` |
| Listener lip movement (chewing, mouthing) | False attribution | Audio-envelope correlation with lag; margin rule; unknown fallback; E3 if measured deficiency |
| Off-screen speaker | Misattribution to visible person | Single-visible-track confidence cap; unknown fallback |
| Whisper hallucination / timestamp drift | Wrong text/timing | VAD clamp, filters, E4 only if needed |
| Image-plane gaze ≠ real 3D orientation | Overconfident listener claims | Hedged labels; `geometry_caveat`; report limitations |
| LLM overreach | Unsupported claims | Validator + template fallback |
| Schema mismatch with docs 12–18 | Rework | Phase 1 audit + reconcile step at each phase start |
| Storage growth | Cost/speed | Grids at 10 Hz/100 ms, partition/retention (Phase 17) |

## Suggested order of delivery

1. **Phase 1** (gate) → **2** → **3** → **4** → **5**: transcript on a shared clock. *Demo: transcript with word timestamps in the API.*
2. **7** → **8** (+ **6** if needed): attributed speech. *Demo: "Who was speaking at 01:24.5?"*
3. **9** → **11**: metrics and interactions. *Demo: participation, interruptions, response latency.*
4. **12** → **14**: API and annotated video. *MVP complete.*
5. **10** → **13** → **15**: listener analysis, dashboard, report.
6. **16** runs continuously from Phase 3 on; **17** after MVP measurements.
7. Optional E1–E5 only if Phase 16 measurements justify them.
