#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [ ! -x ".venv/bin/streamlit" ]; then
  python3 -m venv .venv
  .venv/bin/pip install -r requirements.txt
fi

.venv/bin/streamlit run app.py \
  --server.port 8501 \
  --server.address localhost \
  --server.headless true \
  --browser.gatherUsageStats false
