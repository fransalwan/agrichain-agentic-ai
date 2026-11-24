#!/usr/bin/env bash
# Start the FastAPI gateway (internal) and the stakeholder portal (public, port 7860).
set -euo pipefail

python -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000 &
API_PID=$!

# Wait until the API answers before opening the portal (models load on startup).
for _ in $(seq 1 120); do
  if curl -fs http://127.0.0.1:8000/api/v1/health > /dev/null; then
    echo "API ready"
    break
  fi
  if ! kill -0 "$API_PID" 2>/dev/null; then
    echo "API process exited during startup" >&2
    exit 1
  fi
  sleep 1
done

exec python -m streamlit run src/portal/app.py \
  --server.port "${PORT:-7860}" \
  --server.address 0.0.0.0 \
  --server.headless true \
  --browser.gatherUsageStats false
