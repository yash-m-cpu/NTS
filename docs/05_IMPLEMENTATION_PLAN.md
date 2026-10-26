# 05 — Implementation Plan
## Non-verbal Trust Score (NTS) Analysis Platform — Zero to Production-Ready MVP

This plan is written to be executed by Claude Code, phase by phase, in order. It assumes `03_DATABASE_SCHEMA.md` and `04_API_AUTH.md` as the source of truth for schema and API shape — every phase below references specific tables/endpoints from those documents rather than re-deriving them.

**Foundational references:**
- CV/pose/face/gaze/emotion extraction is powered by **[vladmandic/human](https://github.com/vladmandic/human)**, run server-side under Node.js (`tfjs-node`, optionally CUDA-accelerated) inside a worker process — never in the FastAPI request thread.
- Real-time/bot-based ingestion (Zoom SDK, Teams Graph+Psi) follows the multi-service topology demonstrated in **[Umer-2612/realtime-meeting-intelligence](https://github.com/Umer-2612/realtime-meeting-intelligence)** (platform-specific bot processes fanning out to a shared Python analytics/stream-processor service) — but that architecture is **not built until Phase 15**, deliberately last.

---

## 0. Governing Rules for Every Phase

1. **The app stays runnable after every phase.** If a phase can't be fully finished in one pass, it must still leave `main` in a state where existing tests pass and the app boots.
2. **Vertical slices over horizontal layers.** Prefer "upload → job → status" working end-to-end over "the entire database layer, fully generalized, with nothing plugged in yet."
3. **No phase jumps ahead of its prerequisites.** Phase order below is the required order — see §12 for the explicit list.
4. **What Claude Code must NOT attempt early** (repeated at the top because it's the most common failure mode in a plan like this):
   - Do not build Zoom/Teams bot integration (Phase 15) before the local file-upload pipeline (Phases 5–11) fully works end-to-end.
   - Do not implement the NTS scoring model (Phase 10) before feature extraction (Phase 9) is producing real, inspectable data.
   - Do not add horizontal scaling / multi-worker orchestration (Phase 14) before a single-worker pipeline is correct.
   - Do not write Docker/deployment manifests (Phase 17) before there is something stable worth deploying.
   - Do not implement live camera capture (Phase 13) before the recorded-file pipeline (Phases 5–11) is the default, proven path.
   - Do not add authentication complexity (SSO, org-switching UI polish) beyond what Phase 3 specifies until the core analysis loop works — auth should be minimal-but-correct first, feature-rich later.

---

## 1. PHASE 0 — Repository Initialization

**Objective:** A single monorepo skeleton that can install, lint, and boot an empty backend + empty frontend, with CI wired from commit one.

**Prerequisites:** none.

**Files to create:**
```
/README.md
/.gitignore
/.editorconfig
/.env.example
/pyproject.toml                  (backend: FastAPI, ruff, pytest, alembic deps declared)
/backend/app/__init__.py
/backend/app/main.py             (FastAPI app, mounts /health only)
/backend/app/core/config.py      (pydantic-settings Settings class)
/backend/tests/test_health.py
/frontend/package.json
/frontend/src/main.tsx
/frontend/src/App.tsx
/docker-compose.dev.yml          (postgres + redis only, for local dev — not app containers yet)
/.github/workflows/ci.yml        (lint + test on push)
/docs/                           (this doc set lives here)
```

**Files to modify:** none (greenfield).

**Dependencies:** Python 3.11+, Node 20 LTS, PostgreSQL 15 client libs, Docker (for the dev-compose Postgres/Redis only).

**Implementation tasks:**
- Initialize backend as a `uv`/`poetry`-managed Python package; add FastAPI, Uvicorn, SQLAlchemy 2.x, Alembic, Pydantic v2, pydantic-settings, pytest, ruff, httpx (test client).
- Initialize frontend with Vite + React + TypeScript.
- `docker-compose.dev.yml` brings up Postgres 15 and Redis 7 only, with named volumes; no application containers yet (those come in Phase 17).
- `.env.example` documents every environment variable that will ever be needed (`DATABASE_URL`, `JWT_ACCESS_SECRET`, `JWT_REFRESH_PEPPER`, `REDIS_URL`, `STORAGE_*`, `ALLOWED_ORIGINS`) even though most aren't consumed yet — this is the single checklist for secrets, satisfying "secrets through environment variables" up front.
- CI workflow: `ruff check`, `pytest`, `npm run build` on every push/PR.

**API requirements:** `GET /health` only (per `04_API_AUTH.md` §5.16).

**Database migrations:** none yet — Alembic is installed and initialized (`alembic init`) but has zero revisions.

**Tests:** `test_health.py` asserts `GET /health` returns `200 {"status":"ok"}`.

**Acceptance criteria:**
- `docker compose -f docker-compose.dev.yml up -d` starts Postgres+Redis cleanly.
- `uvicorn app.main:app` boots and serves `/health`.
- `npm run dev` serves an empty React shell.
- CI passes on the initial commit.

**Expected outputs:** a bootable, empty, testable monorepo.

**Common failure modes:** committing a real `.env` instead of `.env.example`; forgetting to pin Python/Node versions (leads to "works on my machine" drift) — pin both in `pyproject.toml`/`package.json` engines and CI matrix.

---

## 2. PHASE 1 — Backend Foundation

**Objective:** A structured FastAPI application (routers, dependency injection, DB session management, error handling, logging) with nothing business-specific yet, but every cross-cutting concern from `04_API_AUTH.md` §2 and §6 in place.

**Prerequisites:** Phase 0.

**Files to create:**
```
/backend/app/api/v1/__init__.py         (router aggregator)
/backend/app/api/deps.py                (get_db, get_current_user stub, get_current_org stub)
/backend/app/core/db.py                 (SQLAlchemy engine/session factory, async)
/backend/app/core/errors.py             (standardized error envelope, exception handlers)
/backend/app/core/logging.py            (structured JSON logging, secret redaction filter)
/backend/app/core/security.py           (password hashing helpers — implemented fully in Phase 3)
/backend/tests/test_error_format.py
```

**Files to modify:** `app/main.py` (register exception handlers, include the v1 router, add CORS middleware from `ALLOWED_ORIGINS`).

**Dependencies:** Phase 0 packages; add `python-json-logger`, `slowapi` (rate limiting scaffolding, rules added in Phase 3).

**Implementation tasks:**
- Implement the error envelope from `04_API_AUTH.md` §2.2 as a global exception handler; map `HTTPException`, Pydantic `ValidationError`, and a catch-all `Exception` → `INTERNAL_ERROR` (no traceback ever serialized to the client).
- Implement async SQLAlchemy session-per-request dependency; this is also where the tenant-scoping `SET LOCAL app.current_org_id` will be added in Phase 3 (stubbed as a no-op now since there's no auth yet).
- Structured logging with a redaction filter for any field matching `*_SECRET|*_KEY|*_TOKEN|PASSWORD`.
- CORS middleware configured from environment, never `*` with credentials.

**API requirements:** no new business endpoints; `/health/ready` added (checks DB connectivity).

**Database migrations:** none yet.

**Tests:** hitting a route that deliberately raises confirms the response body matches the error envelope exactly and contains no stack trace text.

**Acceptance criteria:** any unhandled exception anywhere in the app returns a clean `INTERNAL_ERROR` JSON body, never an HTML traceback; `/health/ready` reports DB status.

**Expected outputs:** an application shell that is safe to build real endpoints on top of.

**Common failure modes:** leaving FastAPI's `debug=True` on (leaks tracebacks) — must default `False` and only be overridden by a `DEBUG` env var read at startup, never a hardcoded flag.

---

## 3. PHASE 2 — Database

**Objective:** The full schema from `03_DATABASE_SCHEMA.md` (all 26 required tables + `refresh_tokens` from `04_API_AUTH.md`) exists via Alembic migrations, with RLS policies and the `set_updated_at` trigger applied.

**Prerequisites:** Phase 1 (needs `app/core/db.py`).

**Files to create:**
```
/backend/app/models/__init__.py
/backend/app/models/{users,organizations,projects,meetings,media,jobs,
  participants,features,metrics,scores,models_registry,archetypes,
  reports,llm,datasets,experiments,audit,auth}.py   (SQLAlchemy ORM models, one module per domain)
/backend/alembic/versions/0001_core_identity.py      (users, organizations, organization_members)
/backend/alembic/versions/0002_projects_meetings.py
/backend/alembic/versions/0003_media_jobs.py
/backend/alembic/versions/0004_participants_tracks.py
/backend/alembic/versions/0005_model_versions.py
/backend/alembic/versions/0006_features_metrics_scores.py   (incl. partitioning for feature_extractions)
/backend/alembic/versions/0007_archetypes_reports_llm.py
/backend/alembic/versions/0008_datasets_experiments_audit.py
/backend/alembic/versions/0009_refresh_tokens.py
/backend/alembic/versions/0010_row_level_security.py
/backend/scripts/seed_reference_data.py               (archetypes, initial model_versions rows)
/backend/tests/test_schema_migrations.py              (migrate up, assert every table exists)
```

**Files to modify:** `app/core/config.py` (add `DATABASE_URL` validation).

**Dependencies:** Phase 1; `psycopg[binary]` or `asyncpg` driver.

**Implementation tasks:** transcribe the DDL in `03_DATABASE_SCHEMA.md` §4 into ordered Alembic revisions exactly as sequenced there (identity → org → project/meeting → media/jobs/model_versions → participants/tracks → features/metrics/scores → archetypes/reports/llm → datasets/experiments/audit → refresh_tokens → RLS policies last, since RLS requires every table to already exist). Run `seed_reference_data.py` after migrations to populate `archetypes` and placeholder `model_versions` rows (`cv_extraction/human-cv/0.0.0-unconfigured`, etc., updated with real versions in Phase 7/10).

**API requirements:** none new — this phase is pure schema.

**Database migrations:** all of them (this phase's entire output).

**Tests:** `alembic upgrade head` succeeds from empty; a test asserts row counts in `archetypes` after seeding; a round-trip test inserts/reads one row per major table to confirm FKs are wired correctly (mirrors the example records in `03_DATABASE_SCHEMA.md` §5).

**Acceptance criteria:** fresh database + `alembic upgrade head` + seed script produces exactly the schema documented in `03_DATABASE_SCHEMA.md`, including RLS policies enabled on every tenant-scoped table.

**Expected outputs:** a fully migrated, empty-but-correct database.

**Common failure modes:** creating tables out of FK dependency order (fixed by the sequencing above); forgetting `CREATE INDEX CONCURRENTLY` cannot run inside a transactional Alembic migration by default — mark those migrations `with autocommit_block()` or run outside a transaction.

---

## 4. PHASE 3 — Authentication

**Objective:** The full `/auth` and `/users` (org-membership subset) API from `04_API_AUTH.md` §5.1–5.2 works end-to-end: register, verify, login, refresh, logout, RBAC-gated routes.

**Prerequisites:** Phase 2 (needs `users`, `organizations`, `organization_members`, `refresh_tokens`).

**Files to create:**
```
/backend/app/core/security.py            (argon2 hashing, JWT encode/decode — completed here)
/backend/app/core/rbac.py                (role-check dependency factory, e.g. require_role("ANALYST"))
/backend/app/schemas/auth.py             (Pydantic request/response models)
/backend/app/services/auth_service.py
/backend/app/api/v1/auth.py
/backend/app/api/v1/users.py
/backend/app/tasks/email.py              (verification/reset email sending, stubbed to console/log in dev)
/backend/tests/test_auth_flow.py
/backend/tests/test_rbac.py
```

**Files to modify:** `app/api/deps.py` (real `get_current_user`/`get_current_org` reading the JWT, setting `app.current_org_id`), `app/api/v1/__init__.py` (mount routers).

**Dependencies:** Phase 2; `python-jose` or `pyjwt`, `argon2-cffi`.

**Implementation tasks:** implement every endpoint in `04_API_AUTH.md` §5.1–§5.2 exactly as specified, including token rotation-on-reuse detection (§1.1), rate limiting on `/auth/login` and `/auth/password/forgot` (§6), and the RLS session variable being set per-request now that `org_id` is a real JWT claim.

**API requirements:** `/auth/*`, `/users/me`, `/users` (list), `/users/invite`, `/users/{id}/role`.

**Database migrations:** none new (Phase 2 covered `refresh_tokens`).

**Tests:** register→verify→login→access-protected-route→refresh→logout full flow; a MANAGER attempting to invite an ADMIN is rejected (403); an expired access token on a protected route returns 401 with `code: "token_expired"`; a refresh-token-reuse-after-rotation revokes the whole family.

**Acceptance criteria:** every endpoint in `04_API_AUTH.md` §5.1–§5.2 passes its documented status codes; RLS demonstrably blocks a cross-org query (test creates two orgs, confirms org A's token cannot read org B's row even via a crafted query).

**Expected outputs:** a real, securable multi-tenant auth system — the foundation every later phase's endpoints depend on for `Authorization` handling.

**Common failure modes:** forgetting to hash the refresh token before storing it (must never store the raw opaque token); testing RBAC only at the router-decorator level and forgetting the DB-level RLS check (both must be verified independently, since RLS is the defense-in-depth layer if a dependency is ever misconfigured).

---

## 5. PHASE 4 — Frontend Foundation

**Objective:** An authenticated React shell — login/register screens, token storage per `04_API_AUTH.md` §6 (access token in memory, refresh in httpOnly cookie), a protected route wrapper, and an org/project switcher, with nothing meeting-specific yet.

**Prerequisites:** Phase 3 (needs a working `/auth` API to call).

**Files to create:**
```
/frontend/src/lib/apiClient.ts          (fetch wrapper: attaches Authorization, handles 401→refresh→retry once)
/frontend/src/state/authStore.ts        (in-memory access token + user/org state)
/frontend/src/routes/Login.tsx
/frontend/src/routes/Register.tsx
/frontend/src/routes/ProtectedLayout.tsx
/frontend/src/components/OrgSwitcher.tsx
/frontend/src/routes/Dashboard.tsx      (empty placeholder — populated in Phase 12)
/frontend/tests/apiClient.test.ts
```

**Files to modify:** `App.tsx` (router setup).

**Dependencies:** Phase 3; add `react-router-dom`, a query/cache library (`@tanstack/react-query`).

**Implementation tasks:** implement the fetch wrapper's 401→refresh→retry-once logic exactly as sketched in `04_API_AUTH.md` §1.4; never persist the access token to `localStorage`/`sessionStorage` (in-memory JS variable/React context only), matching the "no secrets in frontend" security requirement.

**API requirements:** consumes `/auth/*`, `/organizations`, `/projects` (list, for the switcher — even though project CRUD UI comes later, the switcher needs the list endpoint).

**Database migrations:** none.

**Tests:** apiClient test simulates a 401 response and confirms exactly one refresh call + one retry (not an infinite loop); login form validation.

**Acceptance criteria:** a user can register (dev-mode email verification logged to console), verify, log in, see their orgs, switch org, and land on an empty dashboard; refreshing the browser tab does not silently log the user out if the refresh cookie is still valid.

**Expected outputs:** a working, authenticated SPA shell.

**Common failure modes:** storing the access token in `localStorage` (explicitly disallowed); building a generic retry loop that can recurse forever on a persistently-401ing endpoint — must cap at exactly one retry.

---

## 6. PHASE 5 — Video Upload

**Objective:** **Vertical Slice 1** completes here: a user can create a meeting, upload a video via presigned direct-to-storage upload, and see the media asset recorded — no processing yet.

**Prerequisites:** Phase 3 (auth), Phase 4 (frontend shell), Phase 2 (`meetings`, `media_assets` tables).

**Files to create:**
```
/backend/app/schemas/meetings.py
/backend/app/schemas/media.py
/backend/app/services/storage_service.py     (presigned URL generation, provider-agnostic interface)
/backend/app/services/upload_verification.py (content-type sniff, checksum check, AV scan hook)
/backend/app/api/v1/projects.py
/backend/app/api/v1/meetings.py
/backend/app/api/v1/media.py
/frontend/src/routes/ProjectDetail.tsx
/frontend/src/routes/MeetingCreate.tsx
/frontend/src/components/VideoUploader.tsx   (chunked/presigned upload with progress bar)
/backend/tests/test_projects_api.py
/backend/tests/test_meetings_api.py
/backend/tests/test_media_upload.py
```

**Files to modify:** `app/api/v1/__init__.py` (mount new routers).

**Dependencies:** Phase 3, 4; add an S3-compatible SDK (`boto3` or `aioboto3`); local dev uses MinIO (add to `docker-compose.dev.yml`).

**Implementation tasks:** implement `/projects`, `/meetings` (create/list/get), and the full `/media/uploads/initiate` → direct PUT → `/media/uploads/{id}/complete` flow exactly per `04_API_AUTH.md` §5.4–§5.6, including the file-type allow-list, max-size enforcement, and server-generated (never client-supplied) storage keys.

**API requirements:** `/projects` (POST/GET), `/meetings` (POST/GET/GET-by-id), `/media/uploads/initiate`, `/media/uploads/{id}/complete`, `/media/{id}`.

**Database migrations:** none new (tables already exist from Phase 2).

**Tests:** end-to-end test creates a project, a meeting, initiates an upload, PUTs a small fixture video to MinIO, completes the upload, and asserts `media_assets.upload_status == 'verified'`; a test asserts an upload with a spoofed `Content-Type` (real bytes don't match) is rejected.

**Acceptance criteria:** Slice 1 end state — "Upload video → (no processing yet) → media asset visible with status" — works via both API and the minimal UI.

**Expected outputs:** the first real, demoable feature.

**Common failure modes:** trusting client-declared `Content-Type` without sniffing; forgetting `client_max_body_size` at the reverse-proxy layer even though presigned uploads bypass the API (matters for any non-presigned fallback path, e.g. local dev without MinIO configured).

---

## 7. PHASE 6 — Media Processing (Job Orchestration)

**Objective:** **Vertical Slice 1 completes fully** here: `POST /meetings/{id}/analysis` creates a `processing_jobs` row, a worker picks it up asynchronously, updates status through `processing_job_events`, and the frontend can poll `/jobs/{id}` to see it succeed — even though the "processing" itself is a no-op placeholder in this phase (real CV work starts Phase 7).

**Prerequisites:** Phase 5, Phase 2 (`processing_jobs`, `processing_job_events`, `model_versions`).

**Files to create:**
```
/backend/app/services/job_service.py         (enqueue, idempotent-by-state check)
/backend/app/api/v1/jobs.py
/backend/app/workers/__init__.py
/backend/app/workers/base_worker.py          (poll/claim a queued job, run, emit events, handle retries)
/backend/app/workers/noop_worker.py          (placeholder job_type handler — proves the loop end to end)
/backend/scripts/run_worker.py               (entrypoint: python -m app.workers, separate process from API)
/frontend/src/components/JobStatusBadge.tsx
/frontend/src/hooks/useJobPolling.ts
/backend/tests/test_job_lifecycle.py
```

**Files to modify:** `app/api/v1/meetings.py` (add `POST /meetings/{id}/analysis`), `docker-compose.dev.yml` (add a `worker` service running `run_worker.py` against the same Postgres).

**Dependencies:** Phase 5; Redis (already in dev-compose) used for a lightweight job queue (`arq` or `celery` — `arq` chosen for simplicity with async FastAPI, unless a documented reason favors Celery, e.g. needing Celery's more mature multi-queue routing at scale).

**Implementation tasks:** implement the exact async contract from `04_API_AUTH.md` §5.5 (`POST /meetings/{id}/analysis` → 202 immediately, never runs inline), the idempotent-by-state behavior (§9), `attempt_count`/`max_attempts` retry logic, and `processing_job_events` writes on every transition. The worker process is architected generically now (`job_type` dispatch table) so Phase 7–11 each add a new handler without touching this orchestration core.

**API requirements:** `POST /meetings/{id}/analysis`, `GET /jobs/{id}`, `GET /jobs`, `POST /jobs/{id}/cancel`, `GET /jobs/{id}/events`.

**Database migrations:** none new.

**Tests:** enqueue → worker claims → succeeds → client polling sees `succeeded`; enqueue → worker fails → retries up to `max_attempts` → terminal `failed` with sanitized `error_message`; calling `/analysis` twice while one is in-flight returns the same `job_id`.

**Acceptance criteria:** the full async job lifecycle works with a no-op worker payload — this is the scaffolding every real pipeline stage (Phases 7–11) plugs into without changing the API contract.

**Expected outputs:** a working, generic async job system.

**Common failure modes:** running the "worker" inside the same process/event loop as the API (blocks request handling) — must be a genuinely separate process (validated by the dev-compose service split); missing idempotency check leading to duplicate jobs on double-click "Analyze" in the UI.

---

## 8. PHASE 7 — Human CV Integration

**Objective:** **Vertical Slice 2**: Upload video → Human.js extracts pose/face/gaze per frame → results are stored as `participant_tracks` + `feature_extractions` → a simple chart displays one metric over time.

**Prerequisites:** Phase 6 (job orchestration), Phase 2 (`participant_tracks`, `feature_extractions`, `model_versions`).

**Files to create:**
```
/cv-worker/package.json                       (separate Node.js service — Human.js is a JS/TS library)
/cv-worker/src/index.ts                        (polls a Redis/DB queue for job_type='cv_extraction')
/cv-worker/src/humanConfig.ts                  (Human.js Config: backend='tensorflow' for node, model selection)
/cv-worker/src/extractFrames.ts                (ffmpeg-based frame sampling from the downloaded media asset)
/cv-worker/src/runHuman.ts                     (per-frame human.detect(), maps Result → feature_extractions rows)
/cv-worker/src/writeResults.ts                 (batched insert into participant_tracks/feature_extractions via HTTP call to backend or direct DB)
/cv-worker/Dockerfile
/backend/app/workers/cv_extraction_worker.py   (Python-side job_type handler: downloads media, invokes cv-worker, awaits completion, emits events)
/backend/tests/test_cv_extraction_integration.py
/frontend/src/components/FeatureChart.tsx      (single-metric line chart, e.g. gaze yaw over time)
/frontend/src/routes/MeetingAnalysis.tsx
```

**Files to modify:** `docker-compose.dev.yml` (add `cv-worker` service), `app/workers/base_worker.py` dispatch table (register `cv_extraction`).

**Dependencies:** Phase 6; `@vladmandic/human` (npm), `@tensorflow/tfjs-node` (or `-node-gpu` if CUDA available per Human's NodeJS compatibility notes), `ffmpeg` binary in the `cv-worker` Docker image for frame extraction from arbitrary video containers/codecs.

**Implementation tasks:**
- Frame sampling strategy: decode at a fixed rate (e.g. 5 fps, configurable) rather than every frame — matches Human's own "detection of frame changes to trigger only required models" philosophy and keeps `feature_extractions` volume manageable.
- Configure Human with only the modules actually needed for NTS features at this stage (`body`, `face` incl. `emotion`, `gaze` — skip `hand`/`gesture`/`segmentation` initially; add if the metric set in Phase 9 needs them).
- Map each per-person entry in a Human `Result` to a `participant_tracks` row (creating one on first detection of a new `track_label` within the asset, per `03_DATABASE_SCHEMA.md` §3.11) and each relevant `Result` sub-field to one `feature_extractions` row per `feature_type`, always populating `extraction_pipeline_version` (e.g. `human-cv@<npm-version>+cfg-<config-hash>`), `model_version_id` (a `model_versions` row registered for `human-cv`), `processing_job_id`, and `media_asset_id` — all four required references.
- **No face descriptor/embedding vectors are stored** — Human can produce a face embedding for recognition, but that field is deliberately dropped before persistence, per the "no unnecessary biometric identity information" requirement.
- Register the real `human-cv` model version in `model_versions` (replacing the Phase 2 placeholder).

**API requirements:** `GET /meetings/{id}/tracks`, `GET /meetings/{id}/features`, `GET /meetings/{id}/feature-windows` (feature-windows aggregation itself lands in Phase 9, but the endpoint can return raw-only data here).

**Database migrations:** none new (schema already supports this).

**Tests:** integration test runs a short fixture video (a few seconds, checked into `test-fixtures/`) through the real Human pipeline and asserts at least one `participant_tracks` row and multiple `feature_extractions` rows of type `body_pose`/`face_pose`/`gaze` are created with non-null `model_version_id`/`processing_job_id`/`extraction_pipeline_version`.

**Acceptance criteria:** Slice 2 complete — uploading a video, running analysis, and viewing a chart of (e.g.) gaze yaw over time works end-to-end through the real UI.

**Expected outputs:** the platform's first genuine computer-vision output.

**Common failure modes:** running Human.js's browser/WebGL backend inside a headless Node worker (wrong backend — must explicitly configure `tfjs-node`, matching Human's documented NodeJS compatibility); sampling every single frame at native video FPS and overwhelming `feature_extractions` insert throughput — fixed rate sampling avoids this; forgetting `human.warmup()` before the first real frame, which otherwise skews the first sample's latency/attention-pipeline behavior.

---

## 9. PHASE 8 — Audio/STT Integration

**Objective:** **Vertical Slice 3 (part 1)**: add audio track extraction, speech-to-text transcription, and speaker-turn detection as a second `feature_type` stream alongside the CV output from Phase 7.

**Prerequisites:** Phase 7 (extends the same `feature_extractions` model with new `feature_type`s), Phase 6 (job orchestration).

**Files to create:**
```
/backend/app/workers/stt_worker.py            (job_type='stt_transcription' handler)
/backend/app/services/stt_service.py          (wraps chosen STT engine — e.g. faster-whisper for self-hosted, or a cloud STT API behind an interface so the provider is swappable)
/backend/app/services/speaker_turns.py        (diarization → speaker-turn segments)
/backend/app/schemas/transcripts.py
/backend/tests/test_stt_integration.py
```

**Files to modify:** `app/workers/base_worker.py` (register `stt_transcription`), `cv-worker` pipeline unaffected (audio handled entirely in Python, not the Node CV worker, since Human.js is video/image-focused).

**Dependencies:** Phase 7; an STT engine (self-hosted `faster-whisper` recommended for no per-minute API cost and no audio leaving the org's infrastructure, satisfying the same "minimal unnecessary data movement" spirit as §1 of the schema doc) plus a lightweight diarization step (e.g. clustering embeddings, or reusing `meeting_participants` roster + track-based speaker-turn heuristics if diarization proves too heavy for MVP — documented as a scoping decision, not silently skipped).

**Implementation tasks:** extract the audio track from `media_assets` (ffmpeg), run STT to produce timestamped text segments, run speaker-turn segmentation, and persist both as `feature_extractions` rows with `feature_type IN ('voice_prosody', 'speaker_turn')` — transcript text itself is stored in `values` JSONB (e.g. `{"text": "...", "speaker_turn_id": "..."}`), keeping the same four-reference discipline (media asset, processing job, model version, pipeline version) as the CV extractions.

**API requirements:** extends `GET /meetings/{id}/features?feature_type=speaker_turn` (no new endpoint needed — the existing `/features` contract already parameterizes by `feature_type`).

**Database migrations:** none new — `feature_extractions.feature_type` CHECK constraint already includes `voice_prosody`/`speaker_turn` per `03_DATABASE_SCHEMA.md` §4.

**Tests:** a fixture audio clip with known speech produces a transcript with reasonable word-error tolerance; speaker-turn boundaries are monotonic and non-overlapping within a single track.

**Acceptance criteria:** a processed meeting has both visual and audio-derived `feature_extractions`, queryable by `feature_type`, both correctly attributed to the same `participant_track_id` where identity resolution allows.

**Expected outputs:** the second of the two raw signal streams needed for fusion.

**Common failure modes:** running STT synchronously inside the CV worker (couples two independently-scalable, differently-resourced workloads — GPU-bound CV vs. CPU-bound STT — must stay separate job types/queues per `04_API_AUTH.md` `queue_name` field); assuming one speaker per `participant_track_id` without handling overlapping speech.

---

## 10. PHASE 9 — Feature Engineering (Fusion)

**Objective:** **Vertical Slice 3 (part 2)**: `feature_windows` aggregation and `behavioral_metrics` computation — turning raw CV + audio signals into named, interpretable indicators (gaze aversion ratio, gesture rate, speech overlap, posture stability, vocal energy variance, etc.).

**Prerequisites:** Phase 7 (CV features), Phase 8 (audio features), Phase 2 (`feature_windows`, `behavioral_metrics`).

**Files to create:**
```
/backend/app/workers/feature_fusion_worker.py   (job_type='feature_fusion')
/backend/app/services/feature_windowing.py      (buckets feature_extractions into feature_windows)
/backend/app/services/metrics/                  (one module per metric family)
  gaze_metrics.py, gesture_metrics.py, posture_metrics.py, vocal_metrics.py, turn_taking_metrics.py
/backend/app/services/metrics/registry.py       (metric_key → compute function registry, versioned)
/backend/tests/test_feature_windowing.py
/backend/tests/test_behavioral_metrics.py
```

**Files to modify:** `app/workers/base_worker.py` (register `feature_fusion`; this job depends on both `cv_extraction` and `stt_transcription` jobs having succeeded for the same meeting — orchestration enforces this ordering).

**Dependencies:** Phase 7, 8.

**Implementation tasks:** window raw `feature_extractions` (e.g. 5-second buckets) into `feature_windows`, then compute each `behavioral_metrics` row from one or more windows via the metric registry, always writing `computed_by_pipeline_version` so a later change to a metric's formula produces distinguishable rows rather than silently mutating history. Cross-modal metrics (e.g. "gaze aversion during own speaking turns") join CV and audio-derived windows by timestamp — this is the actual "fusion" step.

**API requirements:** `GET /meetings/{id}/feature-windows`, `GET /tracks/{id}/metrics` become fully populated (endpoints existed structurally since Phase 7/2 but had no real aggregation logic until now).

**Database migrations:** none new.

**Tests:** windowing test confirms bucket boundaries and `source_extraction_count` are correct against a synthetic feature stream; each metric function is unit-tested against hand-computed expected values for a fixed synthetic input.

**Acceptance criteria:** Slice 3 complete — a processed meeting shows a populated, chartable set of named behavioral metrics per participant, derived from both modalities.

**Expected outputs:** the direct input layer for NTS scoring (Phase 10).

**Common failure modes:** computing a metric that silently divides by zero on a track with very few detections (e.g. someone off-camera most of the meeting) — every metric function must handle low-`n` windows explicitly (return `null`/skip rather than a misleading `0`).

---

## 11. PHASE 10 — NTS Model

**Objective:** **Vertical Slice 4 (part 1)**: a real (even if simple, e.g. gradient-boosted-tree baseline) NTS scoring model consumes `behavioral_metrics` and produces `nts_scores`, correctly attributed to a `model_versions` row.

**Prerequisites:** Phase 9 (`behavioral_metrics` populated), Phase 2 (`nts_scores`, `model_versions`, `model_predictions`), and — for training — Phase 16's dataset/experiment tables already exist from Phase 2 even though the full `/datasets` and `/experiments` *API* isn't built until this phase needs it for the training workflow.

**Files to create:**
```
/backend/app/workers/nts_scoring_worker.py       (job_type='nts_scoring')
/backend/app/ml/nts_model.py                     (inference wrapper: loads a model_versions artifact, predicts)
/backend/app/ml/feature_vector.py                (behavioral_metrics rows → fixed-order feature vector for the model)
/backend/app/api/v1/scores.py
/backend/app/api/v1/datasets.py
/backend/app/api/v1/experiments.py
/backend/app/api/v1/models.py
/backend/scripts/train_baseline_nts_model.py     (offline training script, writes to datasets/experiments/model_versions)
/backend/tests/test_nts_scoring.py
/backend/tests/test_models_api.py
```

**Files to modify:** `app/workers/base_worker.py` (register `nts_scoring`, which depends on `feature_fusion` having succeeded).

**Dependencies:** Phase 9; `scikit-learn` or `lightgbm` for the baseline model; `mlflow` (optional) or a simple JSON metrics file for experiment tracking, kept consistent with the `experiments.metrics` JSONB shape.

**Implementation tasks:** implement `/scores`, `/models`, `/datasets`, `/experiments` per `04_API_AUTH.md` §5.11, §5.13–§5.15 in full (these were deferred from earlier phases since they had no real data to serve until now); train a first baseline model against whatever labeled or heuristic dataset is available (MVP-acceptable: a rule-derived proxy label if no human-labeled ground truth exists yet, explicitly flagged as such in `model_versions.metrics`), register it as `model_versions` with `status='active'`, and have the worker compute `nts_scores.component_scores` + a top-level `nts_score`, storing `input_metric_ids` for explainability (`GET /scores/{id}/explain`).

**API requirements:** `/scores/*`, `/models/*`, `/datasets/*`, `/experiments/*` (full CRUD/list per `04_API_AUTH.md`).

**Database migrations:** none new.

**Tests:** scoring worker test asserts a `nts_scores` row is created referencing the correct `model_version_id` and that `component_scores` keys are stable/documented; `/models/{id}/promote` transition tests (valid/invalid transitions) per the permission matrix.

**Acceptance criteria:** Slice 4 (part 1) — a processed meeting produces an actual NTS score per participant, viewable via API, attributable to a specific model version, and re-explainable via the metrics that fed it.

**Expected outputs:** the platform's headline output.

**Common failure modes:** training and serving code diverging (feature order/scaling mismatch) — `feature_vector.py` must be the single shared source of the feature schema used by both `train_baseline_nts_model.py` and `nts_model.py`; treating the baseline model's output as more calibrated/validated than it is — `model_versions.metrics` and any user-facing report must be honest about MVP-stage confidence.

---

## 12. PHASE 11 — Reports

**Objective:** **Vertical Slice 4 (part 2)**: NTS scores get narrated into a human-readable report via an LLM, assembled into `report_sections`, and exportable.

**Prerequisites:** Phase 10 (`nts_scores` populated), Phase 2 (`reports`, `report_sections`, `llm_generations`).

**Files to create:**
```
/backend/app/workers/report_generation_worker.py   (job_type='report_generation')
/backend/app/services/llm_narrative_service.py     (prompt templates, calls the LLM provider)
/backend/app/prompts/executive_summary_v1.md
/backend/app/prompts/per_participant_breakdown_v1.md
/backend/app/services/report_export.py             (renders report_sections → PDF/HTML via the docx/pdf toolchain conventions used elsewhere in the org, or a simple HTML→PDF pipeline)
/backend/app/api/v1/reports.py
/frontend/src/routes/ReportView.tsx
/backend/tests/test_report_generation.py
```

**Files to modify:** `app/workers/base_worker.py` (register `report_generation`).

**Dependencies:** Phase 10; an LLM API (self-hosted or hosted — provider abstracted behind `llm_narrative_service.py` so it can be swapped, with the API key read from environment per `04_API_AUTH.md` §6).

**Implementation tasks:** implement `POST /meetings/{id}/reports`, `GET /reports/{id}`, `GET /reports/{id}/download`, `PATCH /reports/{id}/sections/{section_id}` per `04_API_AUTH.md` §5.12; the worker fetches the meeting's `nts_scores` + `behavioral_metrics`, builds a structured `input_context` per prompt template, calls the LLM, and writes both an `llm_generations` row (full audit trail: tokens, latency, `input_context`) and the corresponding `report_sections.content_markdown`; register the narrative model as a `model_versions` row with `model_family='llm_narrative'` so `llm_generations.model_version_id` is populated per the schema's required linkage. The prompt must instruct the model to only narrate the numbers it's given, and the report must visibly disclose it is a narrative *derived from* a model score, not an independent judgment — this is a product/ethics requirement, not just a technical one, given the sensitivity of a "trust score" about a real person.

**API requirements:** `/reports/*` full set per `04_API_AUTH.md` §5.12.

**Database migrations:** none new.

**Tests:** report generation produces a `reports` row with `report_sections` populated and matching `llm_generations` rows; a manual edit to a section correctly flips `content_source` to `manual_edit` and is not overwritten by a later regeneration of a *different* section.

**Acceptance criteria:** Slice 4 complete end-to-end — Upload → CV+audio → features → metrics → NTS score → narrated report, downloadable.

**Expected outputs:** the first complete, demoable product loop.

**Common failure modes:** letting the LLM invent numbers not present in `input_context` (mitigate with strict prompt constraints and, ideally, a post-generation numeric-consistency check comparing any numbers mentioned in `output_text` against `input_context`); PDF export failing silently on unusual characters/emoji in transcripts — must be tested with non-ASCII fixture data.

---

## 13. PHASE 12 — Dashboard

**Objective:** A real project/organization-level dashboard: meeting list, status, score trends, and drill-down into a single meeting's full analysis view — the UI layer that makes Phases 5–11's output actually usable by a non-technical analyst.

**Prerequisites:** Phase 11 (full pipeline exists to visualize), Phase 4 (frontend shell).

**Files to create:**
```
/frontend/src/routes/Dashboard.tsx              (replaces the Phase 4 placeholder)
/frontend/src/routes/MeetingList.tsx
/frontend/src/routes/MeetingDetail.tsx          (tabs: overview, features, metrics, score, report)
/frontend/src/components/ScoreTrendChart.tsx
/frontend/src/components/MetricsTable.tsx
/frontend/src/components/ParticipantCard.tsx
/frontend/tests/dashboard.spec.ts               (component/integration tests)
```

**Files to modify:** router config to wire the new routes under `ProtectedLayout`.

**Dependencies:** Phase 4, 11; a charting library already available in the environment's React runtime conventions (recharts).

**Implementation tasks:** build the meeting list (filterable/sortable per `04_API_AUTH.md` §4), the meeting detail view pulling `/meetings/{id}`, `/meetings/{id}/tracks`, `/meetings/{id}/feature-windows`, `/tracks/{id}/metrics`, `/meetings/{id}/scores`, `/reports/{id}`; an org-level trend view using the analogous aggregate query pattern from `03_DATABASE_SCHEMA.md` §6 query 5.

**API requirements:** none new — this phase is pure frontend consumption of Phases 5–11's endpoints.

**Database migrations:** none.

**Tests:** component tests for each view with mocked API responses; one true end-to-end test (Playwright/Cypress) walking upload → analyze → view dashboard.

**Acceptance criteria:** a non-technical user can, entirely through the UI, upload a meeting, watch it process, and read its NTS report.

**Expected outputs:** the platform's first fully polished, demo-ready surface.

**Common failure modes:** the dashboard polling too aggressively and hitting rate limits (§6) — should prefer the WebSocket (Phase 6 already wired the backend event stream; this phase is where the frontend actually subscribes to it for live UI updates, not just the raw job-progress bar).

---

## 14. PHASE 13 — Live Camera

**Objective:** Extend ingestion beyond uploaded files: a browser-based live camera/microphone capture that streams into the same `media_assets` → `processing_jobs` pipeline, proving the schema/API genuinely support `source_type = 'live_camera'` as designed back in Phase 2.

**Prerequisites:** Phases 5–12 fully working on uploaded files (explicitly do not start this earlier — see §0.4).

**Files to create:**
```
/frontend/src/components/LiveCameraCapture.tsx     (getUserMedia + MediaRecorder, chunked upload)
/backend/app/api/v1/media.py (extend)               (chunked/streaming upload variant)
/backend/app/services/live_chunk_assembler.py       (reassembles uploaded chunks into one media_asset, or processes near-real-time per chunk)
/backend/tests/test_live_capture_flow.py
```

**Files to modify:** `meetings.source_type` handling in `meetings.py` to accept `live_camera` and transition status through `recording`.

**Dependencies:** Phases 5–12; browser `MediaRecorder` API on the frontend.

**Implementation tasks:** capture short (e.g. 5–10 second) `MediaRecorder` chunks client-side, upload each via the same presigned-upload mechanism (or a small dedicated chunk endpoint), and either (a) assemble into a single `media_assets` row processed after the session ends (simpler, MVP-appropriate), or (b) begin processing chunks as they arrive for a near-real-time experience (more complex — only attempt if (a) is solid and there's time budget left; document as a stretch goal, not a blocker for this phase's Definition of Done).

**API requirements:** extends `/media` with a chunk-upload variant; reuses `/meetings/{id}/analysis` unchanged.

**Database migrations:** none — `meetings.source_type` and `media_assets` already support this from Phase 2.

**Tests:** simulated multi-chunk upload reassembles into a valid, playable media asset that the existing CV pipeline can process without modification.

**Acceptance criteria:** Slice 5 — a user can grant camera access, record a short live session in-browser, and see it flow through the exact same processing/scoring/report pipeline as an uploaded file, with no pipeline code forked for this source type.

**Expected outputs:** proof that the platform's core abstraction (a "meeting" with "media assets" and "jobs") was correctly source-agnostic from Phase 2 onward.

**Common failure modes:** building a parallel, live-specific processing pipeline instead of feeding the existing one — a strong signal the Phase 2 schema wasn't actually being honored; browser codec inconsistencies (`MediaRecorder` output format varies by browser) — the `cv-worker`'s ffmpeg step from Phase 7 already normalizes input formats, so this should be handled there, not with new format-specific code.

---

## 15. PHASE 14 — Real-Time Orchestration

**Objective:** Generalize the job/worker system (Phase 6) to support genuinely real-time, low-latency event flows — multiple concurrent live sessions, backpressure handling, and horizontal worker scaling — as the direct prerequisite for bot-based ingestion in Phase 15.

**Prerequisites:** Phase 13 (live camera proves single-session real-time works), Phase 6 (job orchestration core).

**Files to create:**
```
/backend/app/workers/scaling_config.py         (per-queue concurrency limits, backpressure thresholds)
/backend/app/services/session_coordinator.py   (tracks active live/bot sessions, analogous role to
                                                 TeamsCallSessionCoordinator in realtime-meeting-intelligence,
                                                 but generalized across source types)
/backend/app/services/stream_fanout.py         (Redis pub/sub fanout so multiple WebSocket subscribers
                                                 per meeting scale independently of worker count)
/backend/tests/test_concurrent_sessions.py
```

**Files to modify:** `docker-compose.dev.yml` (allow multiple `cv-worker`/`stt-worker` replicas), `job_service.py` (queue-aware routing so GPU-bound CV jobs and CPU-bound STT/fusion jobs don't compete for the same worker pool, extending the `queue_name` field already present since Phase 2).

**Dependencies:** Phase 13; load-testing tooling (`locust` or similar) to validate concurrency behavior.

**Implementation tasks:** introduce explicit per-queue concurrency caps and backpressure (reject/queue new jobs past a threshold rather than degrading every in-flight job); a `session_coordinator` service that mirrors — at a conceptual level, not a code dependency — the lifecycle-management role that `TeamsCallLifecycleService`/`TeamsCallSessionCoordinator` play in the reference architecture, but implemented generically (source-type-agnostic) rather than Teams-specific, since Teams/Zoom specifics don't arrive until Phase 15.

**API requirements:** no new public endpoints; internal scaling/ops concern. `GET /health/ready` extended to report queue depth.

**Database migrations:** none new (uses existing `processing_jobs.queue_name`/`priority`).

**Tests:** load test simulates N concurrent live sessions and asserts no job starves indefinitely and WebSocket fanout latency stays bounded.

**Acceptance criteria:** the platform can run several concurrent live analyses without one session's load degrading another's job latency beyond a documented threshold.

**Expected outputs:** the scaling foundation Phase 15's bots will run on top of.

**Common failure modes:** scaling worker replica count without also scaling the DB connection pool (connection exhaustion under load) — pool sizing must be validated under the same load test.

---

## 16. PHASE 15 — Zoom/Teams Architecture

**Objective:** Bot-based live ingestion from Zoom and Microsoft Teams meetings, directly informed by the topology in **[Umer-2612/realtime-meeting-intelligence](https://github.com/Umer-2612/realtime-meeting-intelligence)** — a Teams bot (.NET/Graph+Psi) and a Zoom bot (C++ Meeting SDK) each fan out raw audio/video to the platform's existing processing pipeline, rather than to a bespoke analytics service.

**Prerequisites:** Phase 14 (real-time orchestration proven under load) — **explicitly, do not start this phase before Phase 14 is done; this is the most common temptation to skip ahead, since Zoom/Teams integration is the most externally impressive-looking feature, and the most likely to be attempted prematurely.**

**Files to create:**
```
/apps/teams-bot/                      (mirrors realtime-meeting-intelligence's apps/teams-bot layout:
                                        .NET service using Teams Graph SDK + Microsoft.Psi for call
                                        lifecycle + media socket handling)
/apps/zoom-bot/                       (C++ Zoom Meeting SDK integration for raw audio/video capture,
                                        mirroring that repo's MeetingSdkDemo/ZoomSdkRenderer pattern)
/backend/app/api/v1/bot_ingest.py     (internal-only webhook the bots POST fan-out descriptors to,
                                        creating media_assets/meetings analogous to an upload but
                                        source_type='zoom_bot'/'teams_bot')
/backend/app/services/bot_auth.py     (service-to-service auth for the bot→backend webhook, separate
                                        from user-facing JWT auth — a scoped service credential, not a
                                        user token)
/infrastructure/k8s/overlays/{dev,staging,prod}/   (bots need Windows + Linux node pools — the reference
                                        repo's split-runner CI/CD approach applies here directly)
```

**Files to modify:** `meetings.py` (accept `source_type IN ('zoom_bot','teams_bot')`), `session_coordinator.py` (register bot sessions using the same generic interface built in Phase 14).

**Dependencies:** Phase 14; Zoom Meeting SDK license/credentials, Microsoft Teams/Graph app registration — both are external platform dependencies with their own approval lead times, which is an additional reason this phase must not be front-loaded.

**Implementation tasks:** stand up the Teams and Zoom bots following the reference repo's structure (call lifecycle service, media stream router, raw audio/video capture hooks), but instead of a bespoke "stream-processor," fan captured media into the **existing** `media_assets`/`processing_jobs` pipeline built in Phases 5–11 unchanged — the entire point of this phase is that it should require *no changes* to the CV/audio/feature/scoring/report pipeline, only a new ingestion front door and the service-to-service auth to protect it.

**API requirements:** one new internal endpoint (`POST /internal/bot-ingest`), authenticated via bot-scoped service credentials (never a user JWT), rate-limited and IP-allow-listed to the bot infrastructure's egress addresses.

**Database migrations:** none new — `meetings.source_type` already anticipates this from Phase 2.

**Tests:** a simulated bot-ingest webhook call (without a real Zoom/Teams meeting, using recorded fixture fan-out data in the shape the real bots would send) produces a correctly-typed `meetings`/`media_assets` pair that flows through the unchanged pipeline.

**Acceptance criteria:** a live Zoom or Teams meeting (staging environment, real credentials) produces an NTS report through the same pipeline as an uploaded file, with zero forked business logic.

**Expected outputs:** feature parity with the reference architecture's stated purpose, built on top of — not alongside — the platform's core.

**Common failure modes:** duplicating the reference repo's "unified Python intelligence server" as a second, parallel processing path instead of routing into the existing `processing_jobs` system — this would silently create two NTS pipelines to maintain; underestimating the operational complexity of a Windows-node Teams bot (per the reference repo's `.NET Framework`/Windows container requirement) with Linux-node everything else — infrastructure work here is genuinely the largest remaining phase and should be scoped/staffed accordingly, not treated as "just another integration."

---

## 17. PHASE 16 — Testing

**Objective:** Close every testing gap left as "basic coverage" in earlier phases: full integration suite, load/performance testing, security testing, and CI gating on all of it.

**Prerequisites:** Phase 15 (or, if Zoom/Teams is descoped for a given MVP timeline, Phase 14) — this phase assumes the feature set is functionally complete and is hardening it, not discovering new requirements.

**Files to create:**
```
/backend/tests/integration/test_full_pipeline_e2e.py   (upload→cv→stt→fusion→score→report, one real run)
/backend/tests/security/test_tenant_isolation.py        (exhaustive cross-org access attempts per table)
/backend/tests/security/test_auth_abuse.py               (rate limit, token replay, role escalation attempts)
/backend/tests/load/locustfile.py
/frontend/tests/e2e/full_flow.spec.ts                    (Playwright, real browser)
/.github/workflows/ci_full.yml                           (nightly: full e2e + load smoke test)
```

**Files to modify:** `.github/workflows/ci.yml` (ensure the fast unit/integration suite still runs on every PR; the heavier `ci_full.yml` runs nightly/pre-release only).

**Dependencies:** all prior phases.

**Implementation tasks:** write the exhaustive tenant-isolation test that attempts, for every tenant-scoped table in `03_DATABASE_SCHEMA.md`, to read/write a row belonging to a different organization using a valid-but-wrong-tenant token, asserting 404/403 and confirming RLS is the actual enforcement mechanism (not just an application-layer filter that could be bypassed by a raw query); load-test the full pipeline at a realistic concurrent-meeting volume from Phase 14's harness; run the full frontend e2e flow in CI using Playwright against a docker-composed full stack.

**API requirements:** none new — this phase tests existing surface area.

**Database migrations:** none new.

**Tests:** this phase *is* the tests.

**Acceptance criteria:** CI is green on the full suite; a documented load-test report shows the system meets its target concurrent-session count (define the number based on Phase 14's findings) within acceptable latency; a security test report shows no cross-tenant leakage across any table.

**Expected outputs:** a production-confidence test suite and a written test/security report.

**Common failure modes:** flaky e2e tests due to real timing dependencies on async job completion — use polling-with-timeout helpers, never fixed `sleep()`; load tests run against a dev-sized database that doesn't reflect production data volume, giving false confidence — seed the load-test environment with realistic `feature_extractions` volume first.

---

## 18. PHASE 17 — Docker/Deployment

**Objective:** Production-ready containerization and deployment manifests for every service (API, workers, cv-worker, frontend, and — if in scope — the Zoom/Teams bots), with environment-based configuration and no secrets baked into images.

**Prerequisites:** Phase 16 (nothing should be deployed that isn't tested).

**Files to create:**
```
/backend/Dockerfile
/frontend/Dockerfile                              (multi-stage: build static assets, serve via nginx)
/cv-worker/Dockerfile                              (already drafted in Phase 7 — finalized here)
/docker-compose.prod.yml                           (or /infrastructure/k8s/base + overlays if k8s is the target)
/infrastructure/k8s/base/{api,worker,cv-worker,frontend}-deployment.yaml
/infrastructure/k8s/base/postgres-statefulset.yaml (or managed-DB connection config if using RDS/Cloud SQL)
/infrastructure/k8s/overlays/{dev,staging,prod}/kustomization.yaml
/.github/workflows/cd.yml                          (build+push images, deploy overlay on tag)
/docs/RUNBOOK.md                                   (on-call operational notes)
```

**Files to modify:** none new business logic — purely operational.

**Dependencies:** Phase 16; a container registry, a Kubernetes cluster (or simpler VM/compose deployment if k8s is out of scope for MVP — document the choice explicitly rather than defaulting to k8s complexity the team doesn't need yet).

**Implementation tasks:** multi-stage Dockerfiles (no build tools/dev dependencies in the final image), all configuration via environment variables/mounted secrets (never baked in, matching the requirement carried since Phase 0's `.env.example`), health/readiness probes wired to `/health` and `/health/ready`, resource requests/limits sized from Phase 16's load-test findings, and — if the Zoom/Teams bots from Phase 15 are in scope — the split Windows/Linux node-pool CI/CD approach the reference repository itself documents (separate build runners, separate image bases).

**API requirements:** none new.

**Database migrations:** deployment pipeline runs `alembic upgrade head` as a pre-deploy job/init-container, never inside the running API container's startup path (avoids multiple replicas racing to migrate simultaneously).

**Tests:** a smoke-test job runs against the freshly-deployed staging environment (`GET /health/ready`, a scripted upload→analyze→score round trip) before promoting to production.

**Acceptance criteria:** a tagged release deploys to staging automatically, passes the smoke test, and can be promoted to production with a single documented step; rolling back is a single documented step too.

**Expected outputs:** a genuinely production-deployable system.

**Common failure modes:** running migrations from multiple replicas simultaneously (use a dedicated migration Job/init-container with a lock, not a startup hook in every pod); forgetting the Windows-node requirement for the Teams bot when sizing the cluster (it cannot run on the same Linux node pool as everything else) — flagged explicitly here since it's easy to overlook if Phase 15 was scoped by a Linux-only engineer.

---

## 19. Vertical Slices — Summary

| Slice | Spans phases | Demonstrates |
|---|---|---|
| **Slice 1** — Upload video → process (no-op) → store job → show status | 5–6 | The async job backbone works before any real ML exists |
| **Slice 2** — Upload video → Human → extract pose → store features → display chart | 7 | Real CV output flows all the way to the UI |
| **Slice 3** — Add audio → STT → speaker turns → feature fusion | 8–9 | Multi-modal signal fusion into interpretable metrics |
| **Slice 4** — NTS model → score → report | 10–11 | The full headline product loop, narrated |
| **Slice 5** — Live camera | 13 | The platform's core abstractions were source-agnostic all along |

---

## 20. Exact Suggested Implementation Order

`0 → 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10 → 11 → 12 → 13 → 14 → 15 → 16 → 17`

No phase should be started before the previous one meets its Definition of Done (below). If a phase is running long, prefer descoping within the phase (e.g. ship the baseline NTS model in Phase 10 without extensive hyperparameter tuning) over skipping ahead to the next phase.

---

## 21. Definition of Done — Per Phase

| Phase | Definition of Done |
|---|---|
| 0 | Repo boots empty backend + frontend; CI green |
| 1 | Error envelope, logging, CORS, `/health/ready` all verified by tests |
| 2 | `alembic upgrade head` reproduces the full schema in `03_DATABASE_SCHEMA.md`, RLS enabled |
| 3 | Full auth flow (register→verify→login→refresh→logout) + RBAC + tenant isolation, all tested |
| 4 | User can log in, see orgs, switch org, land on empty dashboard — token never in `localStorage` |
| 5 | Slice 1 upload step: create meeting, upload file, see verified media asset — via UI |
| 6 | Slice 1 complete: `/analysis` → job → polling/WebSocket → terminal status, with a no-op worker |
| 7 | Slice 2 complete: real Human.js output, chartable, no biometric identity data stored |
| 8 | Audio transcript + speaker turns stored as `feature_extractions`, correctly attributed |
| 9 | Slice 3 complete: named `behavioral_metrics` computed from fused CV+audio windows |
| 10 | Slice 4 (part 1): real `nts_scores` referencing a registered `model_versions` row, explainable |
| 11 | Slice 4 complete: downloadable, narrated report with full `llm_generations` audit trail |
| 12 | A non-technical user can complete the whole loop through the UI alone |
| 13 | Slice 5 complete: live camera capture flows through the unmodified existing pipeline |
| 14 | Multiple concurrent live sessions proven under load without cross-session degradation |
| 15 | A real Zoom or Teams meeting produces a report via the unmodified core pipeline |
| 16 | CI green on full integration + security + load suite; written test/security report exists |
| 17 | Tagged release auto-deploys to staging, passes smoke test, can be promoted/rolled back in one step |
