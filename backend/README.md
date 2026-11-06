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
- `SUPABASE_SERVICE_KEY` — privileged; intentionally not used by the
  HTTP profiles endpoints.
- `OLLAMA_URL`, `OLLAMA_MODEL`, `REDIS_URL`, `MAX_UPLOAD_MB` — Phase 0
  document-parsing / scheduler settings (unchanged names/defaults).

## Endpoints

- `GET /` — health/status.
- `POST /api/v1/upload` — multipart file upload; extracts events via
  PyMuPDF/EasyOCR + local Ollama; optionally queues Redis-backed
  reminder jobs when `device_token` is provided.
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
  `trigger_notification_job` still only prints.
- Production model host is unresolved (free-only, controlled infra).
- Phase 2 scope (trustworthy extraction work, notification behavior,
  any broader restructure) is not implemented here; real chat
  inference is deferred beyond launch scope entirely.
