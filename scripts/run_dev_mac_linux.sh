#!/usr/bin/env bash
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
(cd "$ROOT/backend" && bash run_backend.sh) &
(cd "$ROOT/frontend" && npm install && npm run dev) &
wait
