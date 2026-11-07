#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if [[ -f "$ROOT_DIR/.env" ]]; then
  set -a
  source "$ROOT_DIR/.env"
  set +a
fi

REDIS_URL="${REDIS_URL:-redis://localhost:6379/0}"
OLLAMA_URL="${OLLAMA_URL:-http://localhost:11434}"
PIDS=()

cleanup() {
  trap - EXIT INT TERM
  for pid in "${PIDS[@]}"; do
    kill "$pid" 2>/dev/null || true
  done
  for pid in "${PIDS[@]}"; do
    wait "$pid" 2>/dev/null || true
  done
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

for command in curl redis-cli ollama; do
  if ! command -v "$command" >/dev/null 2>&1; then
    echo "Required command not found: $command" >&2
    exit 1
  fi
done

if [[ ! -x "$ROOT_DIR/venv/bin/uvicorn" ]]; then
  echo "Backend environment is missing. Create venv and install backend/requirements.txt." >&2
  exit 1
fi

if [[ ! -x "$ROOT_DIR/ClientApp/node_modules/.bin/expo" ]]; then
  echo "Client dependencies are missing. Run npm ci in ClientApp/." >&2
  exit 1
fi

if ! redis-cli -u "$REDIS_URL" ping >/dev/null 2>&1; then
  if ! command -v redis-server >/dev/null 2>&1; then
    echo "Redis is not reachable and redis-server is not installed." >&2
    exit 1
  fi
  echo "Starting Redis..."
  redis-server > /tmp/trinket-redis.log 2>&1 &
  PIDS+=("$!")
fi

redis_ready=false
for ((attempt = 1; attempt <= 30; attempt++)); do
  if redis-cli -u "$REDIS_URL" ping >/dev/null 2>&1; then
    redis_ready=true
    break
  fi
  sleep 1
done
if [[ "$redis_ready" != true ]]; then
  echo "Redis did not become ready within 30 seconds." >&2
  exit 1
fi

if ! curl --fail --silent --max-time 2 "${OLLAMA_URL%/}/api/tags" >/dev/null 2>&1; then
  echo "Starting Ollama..."
  ollama serve > /tmp/trinket-ollama.log 2>&1 &
  PIDS+=("$!")
fi

ollama_ready=false
for ((attempt = 1; attempt <= 60; attempt++)); do
  if curl --fail --silent --max-time 2 "${OLLAMA_URL%/}/api/tags" >/dev/null 2>&1; then
    ollama_ready=true
    break
  fi
  sleep 1
done
if [[ "$ollama_ready" != true ]]; then
  echo "Ollama did not become ready within 60 seconds." >&2
  exit 1
fi

echo "Starting FastAPI backend..."
"$ROOT_DIR/venv/bin/uvicorn" backend.main:app --host 0.0.0.0 --port 8000 --reload &
API_PID="$!"
PIDS+=("$API_PID")

api_ready=false
for ((attempt = 1; attempt <= 60; attempt++)); do
  if curl --fail --silent http://127.0.0.1:8000/ >/dev/null 2>&1; then
    api_ready=true
    break
  fi
  if ! kill -0 "$API_PID" 2>/dev/null; then
    echo "FastAPI exited before becoming ready." >&2
    exit 1
  fi
  sleep 1
done
if [[ "$api_ready" != true ]]; then
  echo "FastAPI did not become ready within 60 seconds." >&2
  exit 1
fi

echo "Starting Expo client..."
cd "$ROOT_DIR/ClientApp"
npm run start
