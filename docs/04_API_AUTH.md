# 04 — API & Authentication Specification
## Non-verbal Trust Score (NTS) Analysis Platform

**API style:** REST (JSON) + WebSocket for real-time job/analysis events
**Backend framework:** FastAPI (Python 3.11+) — chosen for native async support (needed for long-running upload/processing coordination), Pydantic request/response validation that maps directly onto the schema in `03_DATABASE_SCHEMA.md`, built-in OpenAPI generation, and first-class WebSocket support without a second framework. No compelling reason to deviate.
**Auth:** JWT (access + refresh), bcrypt/argon2 password hashing, RBAC
**Base path:** `/api/v1`

This spec assumes the media pipeline is CV-model-agnostic at the API boundary (the [vladmandic/human](https://github.com/vladmandic/human) library runs inside worker processes consumed via `processing_jobs`, never called synchronously from a request handler), and that real-time transport will eventually extend to bot-based ingestion in the style of [Umer-2612/realtime-meeting-intelligence](https://github.com/Umer-2612/realtime-meeting-intelligence) (Zoom/Teams bots feeding the same job/event model) — see Phase 13–15 of `05_IMPLEMENTATION_PLAN.md`. Nothing in this spec is upload-only; the same `processing_jobs` + WebSocket event contract serves both.

---

## 1. Authentication

### 1.1 Token model

- **Access token:** JWT, `exp` 15 minutes, signed with `HS256` (or `RS256` if multi-service verification is needed later) using a secret from environment variables (`JWT_ACCESS_SECRET`). Claims: `sub` (user_id), `org_id` (active organization), `role`, `jti`, `iat`, `exp`.
- **Refresh token:** opaque random token (not a JWT), 30-day expiry, stored hashed in a `refresh_tokens` table (new table, additive to `03_DATABASE_SCHEMA.md`; see §1.5) so it can be revoked server-side. Rotated on every use (refresh token rotation — old one invalidated the moment a new one is issued).
- **Logout/revocation:** deletes (or marks revoked) the refresh token row; access tokens are short-lived enough that no server-side blacklist is required for them, but a `jti` blacklist set in Redis is used for the rare "revoke immediately" case (e.g. admin force-logout).
- **Password hashing:** `argon2id` (preferred) or `bcrypt` (cost factor 12) via `passlib`. Never store or log plaintext.
- **Email verification:** required before a user can create/view meetings (configurable per org via `organizations.settings.require_email_verification`); a verification token (short-lived JWT or random token) is emailed on signup, consumed by `POST /auth/verify-email`.

### 1.2 Roles (RBAC)

| Role | Scope | Summary |
|---|---|---|
| `ADMIN` | Organization | Full control: billing/settings, member management, all projects/meetings, model promotion, dataset management |
| `MANAGER` | Organization/Project | Manages projects and members within assigned projects; can invite ANALYST/RESEARCHER/USER; cannot change org billing or promote model versions |
| `ANALYST` | Project | Creates/uploads meetings, triggers analysis, views scores/reports/dashboards within assigned projects; cannot manage members or datasets |
| `RESEARCHER` | Organization (read-mostly) | Read access to datasets, experiments, model_versions, aggregate metrics across projects for model development; cannot view individually-identifying meeting content unless also granted ANALYST on that project |
| `USER` | Project (limited) | Views only meetings/reports explicitly shared with them (e.g. an interviewer reviewing their own session); cannot create meetings, cannot see other participants' scores |

### 1.3 Permission matrix (selected actions)

| Action | ADMIN | MANAGER | ANALYST | RESEARCHER | USER |
|---|:---:|:---:|:---:|:---:|:---:|
| Manage org settings/billing | ✅ | ❌ | ❌ | ❌ | ❌ |
| Invite/remove members | ✅ | ✅ (project-scoped) | ❌ | ❌ | ❌ |
| Create project | ✅ | ✅ | ❌ | ❌ | ❌ |
| Upload media / create meeting | ✅ | ✅ | ✅ | ❌ | ❌ |
| Trigger analysis job | ✅ | ✅ | ✅ | ❌ | ❌ |
| View NTS scores/reports (assigned project) | ✅ | ✅ | ✅ | ✅ (aggregate only) | ✅ (own shares only) |
| Export report | ✅ | ✅ | ✅ | ❌ | ❌ |
| Manage datasets/experiments | ✅ | ❌ | ❌ | ✅ | ❌ |
| Promote model_version to `active` | ✅ | ❌ | ❌ | ✅ (to `staging` only) | ❌ |
| View audit logs | ✅ | ✅ (own project scope) | ❌ | ❌ | ❌ |

Every endpoint below states its role requirement as the **minimum** role; higher roles listed above always inherit lower-role read permissions within their scope, except `RESEARCHER`, which is a deliberately orthogonal (not hierarchical) role — a RESEARCHER is not automatically an ANALYST.

### 1.4 Auth flow example

```
POST /api/v1/auth/login  {email, password}
  → 200 {access_token, refresh_token, expires_in, user: {...}, organizations: [{id, name, role}]}

Client stores access_token in memory (not localStorage — see §6),
refresh_token in an httpOnly, Secure, SameSite=Strict cookie.

Every request: Authorization: Bearer <access_token>

On 401 with error.code == "token_expired":
POST /api/v1/auth/refresh  (refresh_token via httpOnly cookie)
  → 200 {access_token, expires_in}  (+ rotated refresh cookie)
```

### 1.5 New supporting table: `refresh_tokens`

Additive to `03_DATABASE_SCHEMA.md` (not in the original required-entity list, but necessary to implement "refresh tokens" and "logout/revocation" safely):

```sql
CREATE TABLE refresh_tokens (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  token_hash TEXT NOT NULL,          -- sha256 of the opaque token, never the raw value
  organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
  issued_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at TIMESTAMPTZ NOT NULL,
  revoked_at TIMESTAMPTZ,
  replaced_by_token_id UUID REFERENCES refresh_tokens(id) ON DELETE SET NULL,
  ip_address INET,
  user_agent TEXT
);
CREATE INDEX idx_refresh_tokens_user ON refresh_tokens(user_id);
CREATE UNIQUE INDEX uq_refresh_tokens_hash ON refresh_tokens(token_hash);
```

---

## 2. Standardized Response Envelope

### 2.1 Success

```json
{
  "data": { "...": "..." },
  "meta": { "request_id": "req_9f1c2b" }
}
```

Collections use `data` as an array plus a `pagination` object (see §4).

### 2.2 Error format (uniform across every endpoint)

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "The request could not be processed because of invalid input.",
    "details": [
      { "field": "email", "issue": "must be a valid email address" }
    ],
    "request_id": "req_9f1c2b"
  }
}
```

- `code` is a stable machine-readable string (`VALIDATION_ERROR`, `NOT_FOUND`, `UNAUTHORIZED`, `FORBIDDEN`, `CONFLICT`, `RATE_LIMITED`, `PAYLOAD_TOO_LARGE`, `UNSUPPORTED_MEDIA_TYPE`, `INTERNAL_ERROR`).
- `message` is safe to show a user; it never contains a stack trace, SQL fragment, file path, or internal exception text. A FastAPI global exception handler catches all unhandled exceptions, logs the full trace server-side (with `request_id` as the correlation key), and returns only `INTERNAL_ERROR` with a generic message to the client.
- `details` is present only for `VALIDATION_ERROR` (mirrors Pydantic's error list, field-by-field).

### 2.3 HTTP status code conventions

| Status | Meaning |
|---|---|
| 200 | success (GET, successful PATCH/PUT) |
| 201 | resource created (POST) |
| 202 | accepted — analysis/job enqueued, not yet complete |
| 204 | success, no body (DELETE) |
| 400 | validation error |
| 401 | missing/invalid/expired token |
| 403 | authenticated but not authorized (role/tenant mismatch) |
| 404 | resource not found (or not visible to this tenant — see §6 tenant isolation) |
| 409 | conflict (duplicate, idempotency key reuse with different body) |
| 413 | payload too large (upload exceeds max size) |
| 415 | unsupported media type |
| 422 | semantically invalid (e.g. valid JSON but business-rule violation) |
| 429 | rate limited |
| 500 | internal error (generic, no detail) |

---

## 3. API Versioning

- URL-path versioning: `/api/v1/...`. A breaking change ships as `/api/v2/...` running alongside `v1` for a documented deprecation window (minimum 90 days), announced via a `Deprecation` and `Sunset` HTTP header on `v1` responses once `v2` exists.
- Non-breaking additions (new optional field, new endpoint) never bump the version.
- The WebSocket path is versioned identically: `/api/v1/ws/...`.

---

## 4. Pagination, Filtering, Sorting

**Pagination** — cursor-based for high-volume/time-ordered collections (`feature_extractions`-adjacent endpoints), offset-based for everything else (simpler for UI page numbers on bounded lists like meetings/projects):

```
GET /meetings?limit=20&offset=40
GET /features?cursor=eyJ0cyI6MTIzNDU2fQ&limit=100
```

Response:
```json
{
  "data": [ ... ],
  "pagination": {
    "limit": 20,
    "offset": 40,
    "total": 187,
    "next_cursor": null
  }
}
```

**Filtering** — query params scoped to indexed/whitelisted fields only (prevents arbitrary-column DoS queries):

```
GET /meetings?status=analyzed&project_id=...&started_after=2026-08-01&started_before=2026-09-01
GET /reports?status=final
```

**Sorting** — `sort` param, whitelisted fields, `-` prefix for descending:

```
GET /meetings?sort=-started_at
GET /nts-scores?sort=-nts_score
```

---

## 5. API Groups & Endpoints

Each endpoint entry: **Method URL** — Auth — Role — Request — Response — Status codes — Notes.

### 5.1 `/auth`

**POST /auth/register** — No auth — none — `{email, password, full_name}` — `{user_id, status:"invited"}` — 201, 400, 409(email exists) — sends verification email; idempotent on email conflict returns 409 `RESOURCE_EXISTS`.

**POST /auth/verify-email** — No auth — none — `{token}` — `{verified:true}` — 200, 400(invalid/expired token)

**POST /auth/login** — No auth — none — `{email, password}` — `{access_token, refresh_token, expires_in, user, organizations}` — 200, 401(bad credentials — same generic message for wrong email vs wrong password, to avoid user enumeration), 403(unverified email, if org requires it) — rate-limited per §6.

**POST /auth/refresh** — Refresh cookie — none — (no body; cookie only) — `{access_token, expires_in}` — 200, 401(expired/revoked/reused-after-rotation → revokes entire token family as a compromise signal)

**POST /auth/logout** — Access token — none — (none) — 204 — revokes the current refresh token.

**POST /auth/logout-all** — Access token — none — (none) — 204 — revokes all refresh tokens for the user (e.g. "log out everywhere").

**POST /auth/password/forgot** — No auth — none — `{email}` — 202 always (never reveals whether the email exists) — rate-limited aggressively.

**POST /auth/password/reset** — No auth — none — `{token, new_password}` — 200, 400(invalid/expired token) — revokes all existing refresh tokens for that user on success.

### 5.2 `/users`

**GET /users/me** — Access token — any — — `{id, email, full_name, organizations:[...]}` — 200

**PATCH /users/me** — Access token — any — `{full_name?}` — updated user — 200, 400 — email change requires re-verification, handled as a separate `POST /users/me/email` flow, not silently accepted here.

**DELETE /users/me** — Access token — any — — 204 — triggers the privacy deletion flow in `03_DATABASE_SCHEMA.md` §9; requires `{"confirm": true}` in body to avoid accidental calls, 400 if missing.

**GET /users** — Access token — ADMIN\|MANAGER (org-scoped) — query: `role`, `status` — list of org members — 200

**POST /users/invite** — Access token — ADMIN\|MANAGER — `{email, role}` — `{invitation_id}` — 201, 403(MANAGER inviting ADMIN role → forbidden, role escalation check)

**PATCH /users/{id}/role** — Access token — ADMIN — `{role}` — updated membership — 200, 403, 404

**DELETE /users/{id}** *(remove from org, not account deletion)* — Access token — ADMIN — — 204

### 5.3 `/organizations`

**GET /organizations** — Access token — any — — orgs the user belongs to — 200

**POST /organizations** — Access token — any (becomes ADMIN of the new org) — `{name}` — created org — 201

**GET /organizations/{id}** — Access token — member — — org detail incl. `plan_tier`, `settings` (settings redacted to safe subset for non-ADMIN) — 200, 403, 404

**PATCH /organizations/{id}** — Access token — ADMIN — `{name?, settings?}` — updated org — 200, 400, 403

**GET /organizations/{id}/audit-logs** — Access token — ADMIN\|MANAGER — query: `action`, `resource_type`, `from`, `to`, pagination — audit log page — 200, 403

### 5.4 `/projects`

**GET /projects** — Access token — member — query: `status`, pagination, sort — 200

**POST /projects** — Access token — ADMIN\|MANAGER — `{name, description?}` — 201, 400, 409(duplicate name in org)

**GET /projects/{id}** — Access token — member with project access — — 200, 403, 404

**PATCH /projects/{id}** — Access token — ADMIN\|MANAGER — `{name?, description?, status?}` — 200, 400, 403, 404

**DELETE /projects/{id}** — Access token — ADMIN — — 204, 403, 404, 409(non-empty project requires `?force=true`)

### 5.5 `/meetings`

**GET /meetings** — Access token — ANALYST+ (USER sees only shared) — query: `project_id`, `status`, `source_type`, `started_after/before`, pagination, sort — 200

**POST /meetings** — Access token — ANALYST+ — `{project_id, title, source_type, scheduled_at?}` — `{id, status:"scheduled"}` — 201, 400, 403

```json
// Example request
{
  "project_id": "6d1e...",
  "title": "Candidate #482 — Round 2",
  "source_type": "upload"
}
```

**GET /meetings/{id}** — Access token — project member — — full meeting detail incl. nested `media_assets` summary, latest `nts_scores` — 200, 403, 404

**PATCH /meetings/{id}** — Access token — ANALYST+ — `{title?, status?}` — 200, 400, 403, 404

**DELETE /meetings/{id}** — Access token — ADMIN\|MANAGER — — 204, 403, 404 — soft-delete, cascades per retention policy, writes `audit_logs`.

**POST /meetings/{id}/analysis** — Access token — ANALYST+ — `{pipeline?: "full"|"cv_only"|"rescoring", model_version_id?}` — **202** `{job_id, status:"queued", created_at}` — 202, 400(no media uploaded yet), 403, 404, 409(analysis already running — returns the existing `job_id` instead of creating a duplicate, idempotent-by-state) — **never runs synchronously**; the response is immediate, the client then polls `/jobs/{job_id}` or subscribes via WebSocket (§7).

```bash
curl -X POST https://api.nts-platform.com/api/v1/meetings/6d1e.../analysis \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"pipeline": "full"}'

# → 202
# {"data": {"job_id": "b3f2...", "status": "queued", "created_at": "2026-09-06T10:15:00Z"}}
```

**GET /meetings/{id}/participants** — Access token — project member — — list of `meeting_participants` — 200

### 5.6 `/media`

**POST /media/uploads/initiate** — Access token — ANALYST+ — `{meeting_id, asset_type, content_type, size_bytes, checksum_sha256?}` — `{media_asset_id, upload_url, upload_method:"PUT", expires_in}` — 201, 400(size exceeds `MAX_UPLOAD_BYTES`), 415(content_type not in allow-list), 403, 404

  Large files use a **pre-signed direct-to-object-storage upload** (S3/GCS presigned PUT, or presigned multipart for files > 100MB) — the file bytes never transit through the FastAPI process. This is the safe pattern for "large file uploads" required above.

**POST /media/uploads/{media_asset_id}/complete** — Access token — ANALYST+ — `{}` — `{status:"verified"|"quarantined"}` — 200, 409(checksum mismatch), 422(failed malware/type scan) — server-side, after the client confirms the direct upload finished, a background check re-verifies: (a) actual content-type via file signature sniffing (never trust the client-supplied `Content-Type`), (b) checksum match, (c) antivirus/malware scan hook, (d) resolves `storage_key` to a canonicalized, non-traversable path (`orgs/{org_id}/meetings/{meeting_id}/raw/{uuid}.{ext}` — the server generates this key, it is never derived from a client-supplied filename, which eliminates path-traversal risk entirely).

**GET /media/{id}** — Access token — project member — — asset metadata (never a raw byte stream — returns a short-lived presigned **download** URL instead) — 200, 403, 404

**DELETE /media/{id}** — Access token — ADMIN\|MANAGER — — 204 — see privacy deletion strategy.

### 5.7 `/jobs`

**GET /jobs/{id}** — Access token — project member — — `{id, job_type, status, progress_pct, error_message?, started_at, finished_at}` — 200, 403, 404 — the polling endpoint referenced by `POST /meetings/{id}/analysis`.

**GET /jobs** — Access token — project member — query: `meeting_id`, `status`, `job_type`, pagination — 200

**POST /jobs/{id}/cancel** — Access token — ANALYST+ — — `{status:"cancelled"}` — 200, 409(already finished), 403, 404

**GET /jobs/{id}/events** — Access token — project member — query: `since` (timestamp or event id) — list of `processing_job_events` — 200 — used as an HTTP fallback if the WebSocket connection drops, so the client can replay missed events by polling this instead of losing history.

### 5.8 `/features`

**GET /meetings/{id}/features** — Access token — project member — query: `participant_track_id`, `feature_type`, `from_ms`, `to_ms`, pagination (cursor) — raw `feature_extractions` rows — 200, 403, 404 — heavily rate-limited/paginated given volume; not intended for full-scan use by the frontend (that's what `feature_windows`/`behavioral_metrics` are for).

**GET /meetings/{id}/feature-windows** — Access token — project member — query: `participant_track_id`, `feature_type` — aggregated windows — 200

### 5.9 `/participants`

**GET /meetings/{id}/tracks** — Access token — project member — — `participant_tracks` for the meeting, with resolved `meeting_participant` display name if available — 200

**PATCH /tracks/{id}/resolve-identity** — Access token — ANALYST+ — `{meeting_participant_id}` — links a detected track to a roster entry — 200, 400, 403, 404

**GET /participants/{id}** — Access token — project member (canonical identity) — — cross-meeting participant summary — 200, 403, 404

**POST /participants/{id}/link** — Access token — MANAGER+ — `{meeting_participant_id}` — links a roster entry to a canonical identity (explicit, audited action per §9 of the schema doc) — 200, 403, 404

### 5.10 `/metrics`

**GET /tracks/{id}/metrics** — Access token — project member — query: `metric_key`, `category` — `behavioral_metrics` rows — 200, 403, 404

### 5.11 `/scores`

**GET /meetings/{id}/scores** — Access token — project member — query: `participant_track_id`, `model_version_id` — `nts_scores`, latest-first — 200, 403, 404

**GET /scores/{id}** — Access token — project member — — full score detail incl. `component_scores`, linked `model_version` — 200, 403, 404

**GET /scores/{id}/explain** — Access token — project member — — the underlying `behavioral_metrics` / `feature_windows` referenced by `input_metric_ids` (explainability view) — 200, 403, 404

### 5.12 `/reports`

**POST /meetings/{id}/reports** — Access token — ANALYST+ — `{export_format?:"pdf"|"html"|"json"}` — **202** `{report_id, job_id, status:"queued"}` — 202, 400, 403, 404 — report generation is itself a `processing_job` (`job_type = 'report_generation'`), same async pattern as analysis.

**GET /reports/{id}** — Access token — project member — — report detail incl. `report_sections` — 200, 403, 404

**GET /reports/{id}/download** — Access token — project member — — presigned download URL for the exported file — 200, 403, 404, 409(not yet generated)

**PATCH /reports/{id}/sections/{section_id}** — Access token — ANALYST+ — `{content_markdown}` — allows manual edit of an LLM-generated section (sets `content_source = 'manual_edit'`) — 200, 400, 403, 404

### 5.13 `/models`

**GET /models** — Access token — RESEARCHER\|ADMIN — query: `model_family`, `status` — `model_versions` list — 200, 403

**GET /models/{id}** — Access token — RESEARCHER\|ADMIN — — model detail incl. `metrics`, `training_dataset_id` — 200, 403, 404

**POST /models/{id}/promote** — Access token — ADMIN (RESEARCHER limited to `staging` per permission matrix) — `{status:"staging"|"active"|"deprecated"|"retired"}` — 200, 400(invalid transition, e.g. `retired`→`active`), 403, 404 — every promotion writes an `audit_logs` entry (`action = 'model_version.promoted'`).

### 5.14 `/datasets`

**GET /datasets** — Access token — RESEARCHER\|ADMIN — — 200, 403

**POST /datasets** — Access token — RESEARCHER\|ADMIN — `{name, purpose}` — 201, 400, 403

**POST /datasets/{id}/samples** — Access token — RESEARCHER\|ADMIN — `{meeting_id?, participant_track_id?, label?, split?}` — 201, 400, 403, 404

### 5.15 `/experiments`

**GET /experiments** — Access token — RESEARCHER\|ADMIN — query: `dataset_id`, `status` — 200, 403

**POST /experiments** — Access token — RESEARCHER\|ADMIN — `{dataset_id, name, config?}` — `{id, status:"running"}` — 201, 400, 403, 404

**PATCH /experiments/{id}** — Access token — RESEARCHER\|ADMIN — `{status?, metrics?, resulting_model_version_id?}` — 200, 400, 403, 404

### 5.16 `/health`

**GET /health** — No auth — none — — `{status:"ok", version:"1.0.0"}` — 200 — liveness probe, no DB call.

**GET /health/ready** — No auth — none — — `{status:"ok", checks:{db:"ok", redis:"ok", storage:"ok"}}` — 200, 503(any dependency down) — readiness probe for k8s; DB/Redis/storage checked with short timeouts; never leaks connection strings or internal hostnames in the response.

---

## 6. Security Requirements — Implementation Notes

- **JWT validation:** every protected route depends on a shared FastAPI dependency (`get_current_user`) that verifies signature, expiry, and issuer/audience claims before any handler code runs; invalid tokens short-circuit to 401 before touching the DB.
- **Password hashing:** `argon2id` via `passlib.context.CryptContext`; hashing parameters (memory cost, iterations) stored alongside the hash string so they can be upgraded without a mass-invalidation migration.
- **Rate limiting:** `slowapi` (Redis-backed) — global default 100 req/min/IP; `/auth/login` and `/auth/password/forgot` limited to 5 req/min/IP + 10 req/hour/email to blunt credential stuffing; `429` responses include `Retry-After`.
- **CORS:** explicit allow-list of frontend origins from an environment variable (`ALLOWED_ORIGINS`), never `*` when credentials are involved; `Access-Control-Allow-Credentials: true` only for those listed origins.
- **File type validation:** upload allow-list by real content sniffing (`python-magic` / file signature check) against `{video/mp4, video/quicktime, video/webm, audio/mpeg, audio/wav}` — the client-declared `Content-Type` header is never trusted alone.
- **Max file size:** enforced at three layers — object-storage presigned POST/PUT policy (hard cap), reverse-proxy/ingress `client_max_body_size` for any non-presigned path, and application-level check on `size_bytes` before issuing the presigned URL. Default 5GB/video, configurable per `organizations.settings.max_upload_bytes`.
- **Path traversal protection:** as noted in §5.6, storage keys are always server-generated UUIDs, never built from user-supplied filenames or paths — traversal has no attack surface because there is no user-controlled path segment.
- **Malicious upload protection:** async antivirus scan (e.g. ClamAV sidecar) runs as part of `POST /media/uploads/{id}/complete`; the asset stays `upload_status = 'pending'`→ never `'verified'` (and thus never eligible for a processing job) until the scan clears; a `'quarantined'` result blocks all downstream processing and notifies an ADMIN.
- **Authorization on every resource:** no endpoint trusts a path-parameter ID alone — every handler's DB query includes `organization_id = current_org` (backed by the RLS policy in `03_DATABASE_SCHEMA.md` §10) so a request for someone else's `meeting_id` returns 404, not 403 (avoids confirming the resource's existence to an unauthorized caller).
- **Tenant isolation:** the FastAPI dependency that opens a DB session issues `SET LOCAL app.current_org_id = '<org_id>'` from the validated JWT's `org_id` claim before any query runs in that request's transaction.
- **Secrets via environment variables:** `JWT_ACCESS_SECRET`, `JWT_REFRESH_PEPPER`, `DATABASE_URL`, object-storage credentials, LLM API keys — all read via a typed `pydantic-settings` `Settings` class at startup; never hardcoded, never committed, never logged (a logging filter redacts any field whose key matches `*_SECRET|*_KEY|*_TOKEN|PASSWORD`).
- **No secrets in frontend:** the SPA holds only the short-lived access token (in memory) and calls the backend for everything else; presigned upload/download URLs are generated server-side per-request and expire quickly (default 15 minutes), so no long-lived storage credential is ever shipped to the browser.
- **Audit logging:** every state-changing request (POST/PATCH/DELETE) on `auth`, `users`, `organizations`, `meetings`, `media`, `models`, `reports` writes an `audit_logs` row inside the same DB transaction as the change, so an audit gap is impossible without the underlying change also having failed.
- **No internal stack traces exposed:** see §2.2 — the FastAPI exception handler distinguishes `HTTPException` (safe, intentional) from anything else (converted to a generic `INTERNAL_ERROR`), and `debug=False` in every non-local environment so FastAPI's own traceback page is never served.

---

## 7. WebSocket — Real-Time Analysis Events

**Endpoint:** `wss://api.nts-platform.com/api/v1/ws/meetings/{meeting_id}?token=<access_token>`
(Token passed as a query param because browser WebSocket clients cannot set an `Authorization` header; the server validates it identically to the HTTP path and closes the connection with code `4401` if invalid/expired — the client then re-authenticates over HTTP and reconnects with a fresh token.)

### 7.1 Connection lifecycle

1. Client opens the socket after calling `POST /meetings/{id}/analysis` (or at any time to observe an in-progress meeting).
2. Server validates JWT + tenant/project access, subscribes the connection to that meeting's event channel (Redis pub/sub backing multiple FastAPI worker processes).
3. Server immediately sends a `sync` event with the current state of any in-flight jobs (so a client connecting mid-analysis isn't blind).
4. On disconnect, the client should call `GET /jobs/{id}/events?since=<last_seen>` to catch up on anything missed before reconnecting (WebSocket is a convenience stream, not the source of truth — `processing_job_events` is).

### 7.2 Event schema (stable envelope for every event type)

```json
{
  "event": "job.progress",
  "meeting_id": "6d1e...",
  "job_id": "b3f2...",
  "occurred_at": "2026-09-06T10:16:32Z",
  "data": { "...": "event-specific payload" }
}
```

### 7.3 Defined events

| Event | `data` payload | Emitted when |
|---|---|---|
| `job.started` | `{job_type, model_version_id}` | a `processing_jobs` row transitions to `running` |
| `job.progress` | `{pct, stage}` | a `processing_job_events` row of type `progress` is written |
| `feature.extracted` | `{feature_type, participant_track_id, count_since_last}` | batched, throttled to at most 1/sec per track (raw per-frame events are far too high-volume to stream individually) |
| `participant.detected` | `{participant_track_id, track_label, first_seen_at_ms}` | a new `participant_tracks` row is created |
| `analysis.completed` | `{meeting_id, scores: [{participant_track_id, nts_score}]}` | the terminal `nts_scoring` job for the meeting succeeds |
| `analysis.failed` | `{job_id, error_message}` (sanitized, no stack trace) | any job in the analysis chain fails after exhausting `max_attempts` |
| `sync` | `{jobs: [...]}` | sent once, immediately after connecting |

### 7.4 Frontend usage example

```javascript
const socket = new WebSocket(
  `wss://api.nts-platform.com/api/v1/ws/meetings/${meetingId}?token=${accessToken}`
);

socket.onmessage = (msg) => {
  const evt = JSON.parse(msg.data);
  switch (evt.event) {
    case "job.progress":
      setProgress(evt.data.pct);
      break;
    case "analysis.completed":
      setScores(evt.data.scores);
      socket.close();
      break;
    case "analysis.failed":
      setError(evt.data.error_message);
      break;
  }
};

socket.onclose = async (ev) => {
  if (ev.code === 4401) {
    const newToken = await refreshAccessToken();
    // reconnect with newToken
  } else {
    // fall back to polling GET /jobs/{id} and /jobs/{id}/events?since=...
  }
};
```

---

## 8. Frontend API Usage Examples

```javascript
// Trigger analysis and poll as a fallback to the WebSocket
async function runAnalysis(meetingId) {
  const res = await fetch(`/api/v1/meetings/${meetingId}/analysis`, {
    method: "POST",
    headers: { Authorization: `Bearer ${accessToken}`, "Content-Type": "application/json" },
    body: JSON.stringify({ pipeline: "full" }),
  });
  const { data } = await res.json(); // { job_id, status, created_at }

  const poll = setInterval(async () => {
    const jobRes = await fetch(`/api/v1/jobs/${data.job_id}`, {
      headers: { Authorization: `Bearer ${accessToken}` },
    });
    const job = (await jobRes.json()).data;
    if (job.status === "succeeded" || job.status === "failed") clearInterval(poll);
  }, 3000);
}

// Direct-to-storage upload
async function uploadMedia(meetingId, file) {
  const initRes = await fetch("/api/v1/media/uploads/initiate", {
    method: "POST",
    headers: { Authorization: `Bearer ${accessToken}`, "Content-Type": "application/json" },
    body: JSON.stringify({
      meeting_id: meetingId,
      asset_type: "video",
      content_type: file.type,
      size_bytes: file.size,
    }),
  });
  const { data } = await initRes.json(); // { media_asset_id, upload_url }

  await fetch(data.upload_url, { method: "PUT", body: file }); // direct to S3/GCS, bypasses API

  await fetch(`/api/v1/media/uploads/${data.media_asset_id}/complete`, {
    method: "POST",
    headers: { Authorization: `Bearer ${accessToken}` },
  });
}
```

---

## 9. Idempotency

- **Client-supplied idempotency key:** all POST endpoints that create a billable/heavy resource (`POST /meetings/{id}/analysis`, `POST /media/uploads/initiate`, `POST /meetings/{id}/reports`) accept an optional `Idempotency-Key` header. The server stores `(idempotency_key, request_hash, response)` for 24 hours; a repeat request with the same key and same body returns the original response (200/201/202, cached) instead of creating a duplicate; the same key with a *different* body returns `409 CONFLICT`.
- **Natural idempotency without a key:** `POST /meetings/{id}/analysis` is additionally idempotent by state — if a non-terminal job of the same `job_type` already exists for the meeting, the endpoint returns that job instead of enqueuing a second one, regardless of whether an `Idempotency-Key` was sent.
- **Uploads:** `checksum_sha256` + the unique `(storage_bucket, storage_key)` constraint prevents the same bytes from being processed twice under two different `media_asset_id`s if a client retries an upload after a network blip.

---

## 10. OpenAPI

FastAPI generates the full OpenAPI 3.1 schema automatically from the Pydantic models and route decorators described above, served at `/api/v1/openapi.json` with interactive docs at `/api/v1/docs` (Swagger UI) — gated behind ADMIN auth in production, open in local/dev. Every request/response model in this document corresponds 1:1 to a Pydantic schema; no field described here is hand-documented separately from the code that enforces it.
