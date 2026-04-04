#!/usr/bin/env bash
set -euo pipefail

uv sync

(
  uv run uvicorn main:app --reload
) &
backend_pid=$!

(
  cd frontend
  npm install
  npm run dev
) &
frontend_pid=$!

trap 'kill "$backend_pid" "$frontend_pid" 2>/dev/null || true' INT TERM EXIT
wait -n "$backend_pid" "$frontend_pid"
status=$?
kill "$backend_pid" "$frontend_pid" 2>/dev/null || true
wait "$backend_pid" "$frontend_pid" 2>/dev/null || true
exit "$status"
