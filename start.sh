#!/bin/bash

# Cleanup background tasks when you press CTRL+C
cleanup() {
  echo ""
  echo "Stopping all services..."
  kill $(jobs -p) 2>/dev/null
  exit
}
trap cleanup EXIT INT TERM

echo "=========================================="
echo " Starting DocExtract Services"
echo "=========================================="

# 1. Start Redis
echo "[1/4] Starting Redis..."
redis-server > /dev/null 2>&1 &

# 2. Start Ollama
echo "[2/4] Starting Ollama (qwen2.5:3b)..."
ollama run qwen2.5:3b > /dev/null 2>&1 &

# 3. Start FastAPI
echo "[3/4] Starting FastAPI backend..."
source venv/bin/activate
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload &

# Wait briefly for backend components to bind ports
sleep 3

# 4. Start Expo (ClientApp)
echo "[4/4] Starting Expo dev server..."
cd ClientApp
npx expo start