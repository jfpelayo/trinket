# Trinket

A productivity app. The backend extracts draft events from uploaded documents using local OCR and Ollama; persistence and real authentication are beyond the current preview scope.

## Layout

- `backend/` — FastAPI app (`backend.main:app`) with `/api/v1/upload`, `/api/v1/chat`, and `/api/v1/profiles/me`.
- `frontend/` — canonical Expo (SDK 57) app: login preview, sample quest board, document upload screen.
- `ClientApp/` — legacy copy of the earlier client, kept locally but no longer tracked or used.

## Local development

Requirements: Python 3.13, Node.js/npm, Redis, and [Ollama](https://ollama.com/).

1. Clone the repository, then create the local environment file:

   ```sh
   cp .env.example .env
   ```

2. Create and install the backend environment:

   ```sh
   python3.13 -m venv venv
   source venv/bin/activate
   python -m pip install -r backend/requirements.txt
   ```

3. Install the local Ollama model once:

   ```sh
   ollama pull qwen2.5:3b
   ```

4. Install the Expo client dependencies:

   ```sh
   cd frontend
   npm ci
   cd ..
   ```

   Copy `frontend/.env.example` to `frontend/.env` and set
   `EXPO_PUBLIC_API_URL` for your platform (see that file for web,
   device, and Android emulator values).

5. Start the local services and client:

   ```sh
   ./start.sh
   ```

The script starts Redis and Ollama when they are not already reachable, waits for Redis, Ollama, and FastAPI to become ready, then starts Expo from `frontend/`. Press Ctrl-C to stop the processes started by the script. Redis and Ollama output is written to `/tmp/trinket-redis.log` and `/tmp/trinket-ollama.log`.

The `.env` file is local and ignored by Git. `SUPABASE_URL`, `SUPABASE_KEY`, and `SUPABASE_SERVICE_KEY` are reserved for the Supabase integration; do not put service credentials in the client. `MAX_UPLOAD_MB` is enforced by the backend (`/api/v1/upload` returns 413 over the limit). Keep `OLLAMA_URL` pointed at infrastructure you control; a production model host has not been selected (free-only, controlled infrastructure required).

## Status

- Phase 2 extraction safeguards are in place (upload size/type limits, extraction error mapping).
- The profiles API (`GET`/`PUT /api/v1/profiles/me`) exists and verifies Supabase bearer tokens — backend auth is implemented.
- The frontend login screen is a **preview**: frontend sign-in is not connected to that API yet, the quest board shows sample local content, and uploaded events are review-only drafts — nothing is saved, scheduled, or pushed.
- Frontend Supabase sign-in, task persistence, and Expo push delivery are beyond current scope; the production model host is unresolved.
