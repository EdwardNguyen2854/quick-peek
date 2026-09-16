#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -x ".venv/bin/python" ]; then
  echo "Creating backend virtual environment..."
  python3 -m venv .venv
fi

echo "Installing backend dependencies..."
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt

echo "Starting Quick Peek API on http://127.0.0.1:8000"
exec .venv/bin/python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
