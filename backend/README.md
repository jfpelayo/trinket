# Trinket Backend

Single FastAPI app (`backend/main.py`). One canonical uvicorn target,
run from the repo root:

```bash
venv/bin/uvicorn backend.main:app --reload --port 8000
```

## Configuration

`backend/config.py` loads `.env` from the repo root first, then
`backend/.env`, both with `override=False` — real OS environment
variables win, then root `.env`, then `backend/.env`. See
`.env.example` (root and backend) for the full list.

- `SUPABASE_URL`, `SUPABASE_KEY` — publishable/anon key used by the HTTP
  profiles API to build per-request clients.
- `SUPABASE_SERVICE_KEY` — privileged; used only by the document worker,
  never by HTTP routes.
- `CORS_ORIGINS` — comma-separated browser origins (defaults to local Expo
  web ports). Credentials/cookies are not allowed; clients send bearer tokens.
- `OLLAMA_URL`, `OLLAMA_MODEL`, `REDIS_URL`, `MAX_UPLOAD_MB` — document
  parsing / scheduler settings. `MAX_UPLOAD_MB` defaults to 10.

## Endpoints

- `GET /` — health/status.
- `POST /api/v1/upload` — multipart PDF or JPEG/PNG/BMP/TIFF upload;
  extracts events via PyMuPDF/EasyOCR + local Ollama. Uploads are
  limited to `MAX_UPLOAD_MB`; PDFs are limited to 100 pages and extracted
  text to 60,000 characters. Long documents are parsed in 12,000-character
  sections. Unsupported files return 415, oversized/unprocessable inputs
  return 413 or 422, and Ollama failures return 502 rather than fabricated
  events. Successful extracted events are drafts for user review; reminders
  are not scheduled during upload. `device_token` remains accepted for
  compatibility but is not used.
- `POST /api/v1/chat` — stub echo: `{"message": str}` ->
  `{"reply": "Trinket received your message: <message>"}`. No external
  model calls; real chat inference is deferred beyond launch scope
  (Phase 2 = trustworthy extraction, not chat). A legacy `POST /chat`
  alias exists but is hidden from the OpenAPI schema.
- `GET /api/v1/profiles/me` — read the caller's profile row.
- `PUT /api/v1/profiles/me` — upsert the caller's profile row. Body:
  required `display_name` plus optional `timezone`, `avatar_url`,
  `pronouns`, `communication_style` (concise|detailed|balanced),
  `motivation_style` (encouragement|accountability|small_challenges),
  `preferred_study_time` (HH:MM), `focus_session_minutes` (5-180),
  `reminders_enabled` (bool, non-null). Unknown fields are rejected;
  omitted fields are left unchanged.

### Profiles auth

Profiles endpoints require `Authorization: Bearer <supabase access
token>`. Each request creates a fresh Supabase client with the anon
key, verifies the JWT via `auth.get_user(token)`, and scopes PostgREST
to the same token so row-level security applies. No service key, no
shared signed-in client. Errors: 401 missing/malformed/invalid token
(`WWW-Authenticate: Bearer`), 503 missing config or auth transport
failure, 502 database failure, 404 no profile row, 422 invalid body.

## Phase 3: saved documents, events, and devices

All routes below require `Authorization: Bearer <supabase access token>`
and use the same per-request, RLS-scoped client as profiles. Every query
also filters by the verified user id. Bodies reject unknown fields, so a
client can never set `user_id`, `document_id`, `source`, or job fields.

| Method | Path | Result |
|---|---|---|
| POST | `/api/v1/documents` | Multipart `file`. Extracts text, saves a `processing` document, returns 202 + `Location`. Timezone: profile, then `X-Timezone`, then UTC. |
| GET | `/api/v1/documents` | Caller's 100 most recent documents. |
| GET | `/api/v1/documents/{id}` | `{document, events}`; poll until `status` is `review` or `failed`. |
| POST | `/api/v1/documents/{id}/confirm` | Confirms all draft events (dismissed stay dismissed); 409 while processing/failed. |
| GET | `/api/v1/events?from&to&status&limit&offset` | Timezone-aware, half-open `[from, to)`, sorted by start time. |
| POST | `/api/v1/events` | Manual event: `title`, `category`, aware `starts_at`, `all_day`, `reminder_offset_minutes`. |
| PATCH | `/api/v1/events/{id}` | Edit fields or set `status` to `draft`/`dismissed`. Editing a confirmed event returns it to draft. |
| POST | `/api/v1/events/{id}/confirm` | Confirm one event; 409 if dismissed. |
| DELETE | `/api/v1/events/{id}` | 204. |
| POST | `/api/v1/devices` | Register an Expo push token (`ExponentPushToken[...]`, `ios`/`android`); 409 if another account owns it. |
| DELETE | `/api/v1/devices/{id}` | 204. |

Document and event responses never include extracted text or worker lease
fields. Confirmation returns `"reminders_scheduled": false`: it records the
user's review only. Reminder scheduling and Expo push delivery are Phase 4.

### Extraction worker

Uploads do not call the model. Run the worker on a team-controlled machine
with Ollama, from the repo root:

```bash
venv/bin/python -m backend.document_worker          # keep polling
venv/bin/python -m backend.document_worker --once   # one job, then exit
```

The worker claims one document with a 15-minute database lease, runs the
model with a 14-minute timeout, and saves all draft events plus the
`review` status in one transaction. A crashed job is reclaimed when its
lease expires; after three attempts it is marked `failed`
(`worker_timeout`). Ambiguous or nonexistent local times (DST changes) fail
the document with `invalid_dates` instead of guessing. Only the worker uses
`SUPABASE_SERVICE_KEY`. Uploads stay `processing` until a worker runs;
`start.sh` does not start one, because the production host is undecided.

Only extracted text is stored (in `documents.raw_text`); original files are
not kept.

### Migrations

`supabase/migrations/20261107000000_documents_events.sql` and
`20261107000100_extraction_jobs.sql` add the tables, RLS policies,
column-level grants, triggers, and worker RPCs. They have not been applied
to the team's Supabase project. Apply them with the Supabase CLI after
review.

To re-run the database regression checks, use a fresh, disposable
PostgreSQL 15+ database (never a Supabase project):

```bash
psql -v ON_ERROR_STOP=1 -f backend/tests/phase3_bootstrap.sql
psql -v ON_ERROR_STOP=1 -f backend/tests/phase3_regression.sql
```

## Offline checks

Run from the repo root:

```bash
venv/bin/python -m unittest discover -s backend/tests -v
```

Tests run entirely offline: scheduler start/shutdown, OCR, and Ollama
are stubbed; profiles tests cover both a mocked client factory
(query/payload assertions) and the real pinned Supabase SDK with
network faked at the httpx transport layer only. No network, Redis,
or Ollama needed.

## Manual scripts (caution)

`backend/test_profile.py` and `backend/test_profile_access.py` are
interactive scripts that sign in with real credentials and touch the
real Supabase project. Run them only from `backend/` (`python
test_profile.py`) and only when you intend to hit live data. Migrations
in `backend/supabase/migrations/` are applied via the Supabase CLI —
they are not executed by this codebase.

## Parked / deferred

- `frontend/src/chatbotAPI1` — empty file added by the incoming chatbot
  merge; retained as a placeholder. No active frontend integration;
  no existing frontend files were changed.
- Expo Push is the chosen push provider; delivery is not implemented —
  `trigger_notification_job` still only prints. Reminder scheduling is
  not connected to upload results; a future review/confirmation flow must
  schedule reminders explicitly.
- Production model host is unresolved (free-only, controlled infra).
- Phase 3 persistence and review are implemented (see above). Reminder
  scheduling for confirmed events and push delivery are Phase 4; real chat
  inference is deferred beyond launch scope entirely. The legacy
  `POST /api/v1/upload` stays for the current frontend and saves nothing.
