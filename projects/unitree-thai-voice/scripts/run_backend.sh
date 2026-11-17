#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_root"
exec bash "$project_root/scripts/run_python.sh" -m uvicorn backend.app.main:app \
  --host 127.0.0.1 --port 8000 "$@"
