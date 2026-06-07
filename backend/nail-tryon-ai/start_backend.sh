#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [ ! -x ".venv/bin/python" ]; then
  uv venv
  uv pip install -r requirements.txt
fi

exec .venv/bin/python -m uvicorn api:app --host 127.0.0.1 --port 8000
