# 21 — Repository Audit (Phase 1)

## 1. Backend Structure
- Python 3.12, FastAPI, SQLAlchemy 2.0 async, PostgreSQL 15, Alembic.
- Jobs: Redis + ARQ.
- Storage: MinIO.

## 2. Database
Schema verified using `dump_schema.py`.
- `media_assets`: Contains UUIDs, sizes, durations, uploaded info, `annotated_video_key`.
- `participant_tracks`: Contains `track_label` (e.g., `person_0`), timestamps, confidence.
- `feature_extractions`: Massive table (~87k rows for a 9 min video). JSONB values.
- `processing_jobs`: Job state, `job_type`.
- `meetings`, `behavioral_metrics`, `nts_scores`, `nts_visual_reports`.

## 3. Participant Tracking
- `@vladmandic/human` assigns `f.id` for tracking.
- Tracking works reasonably well (produced 7 distinct tracks for a 7-person meeting).
- Tracks are stored in `participant_tracks`.

## 4. CV Features
- `human_cv_script.js` extracts bounding boxes, head rotation, gaze, and body keypoints.
- **Lip landmarks are NOT stored.** The script only exports `mesh_count`.
- This means Phase 7 will require a mouth-only CV extraction pass.

## 5. STT & Audio
- `stt_worker.py` downloads a **single mixed audio track** (`audio.mp4` / `audio.wav`).
- It uses `faster-whisper`.
- Diarization is currently mocked (`diarization_service.py` returns a single `speaker_0`).
- No per-participant audio tracks exist.

## 6. ARQ Cascade
- Job service provides `enqueue_job()`.
- Supports cascading via `extra_kwargs` and checking conditions in `base_worker.py`.

## 7. Annotation Worker
- Uses OpenCV to draw boxes and skeletons.
- Encodes via `ffmpeg` to H.264.
- **Does NOT include audio in the annotated video.**

## Decisions based on Audit
- **Ambiguity 1 (Audio tracks):** Single mixed track exists. Phase 6 (Audio diarization / cluster-lite) is required. Phase 8 will rely on lip-primary attribution.
- **Ambiguity 2 (Lip landmarks):** Not stored. Phase 7 (Mouth activity) requires a mouth-only pass.
- **Ambiguity 3 (Track ID stability):** `person_N` is somewhat stable (7 people in 9 mins), though occlusion handling may be weak.
- **Ambiguity 4 (Diarization):** Mocked in `diarization_service.py`. Phase 6 cluster-lite is needed as a prior.
- **Ambiguity 5 (Annotated audio):** Annotated video lacks audio. It will need an FFmpeg fix to multiplex the original audio back in.
