# Trinket

A productivity app. The current backend extracts dates from uploaded documents using local OCR and Ollama; persistence, authentication, and notifications are being integrated in later phases.

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
   cd ClientApp
   npm ci
   cd ..
   ```

5. Start the local services and client:

   ```sh
   ./start.sh
   ```

The script starts Redis and Ollama when they are not already reachable, waits for Redis, Ollama, and FastAPI to become ready, then starts Expo. Press Ctrl-C to stop the processes started by the script. Redis and Ollama output is written to `/tmp/trinket-redis.log` and `/tmp/trinket-ollama.log`.

The `.env` file is local and ignored by Git. `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, and `DATABASE_URL` are reserved for the upcoming Supabase integration; do not put service credentials in the client. `MAX_UPLOAD_MB` is configured for the planned upload-limit work and is not enforced yet. Keep `OLLAMA_URL` pointed at infrastructure you control; a production model host has not been selected.

The current upload client is in `ClientApp/`. The separate `frontend/` tree remains unchanged while the planned app-layout consolidation is handled in a later phase.
