#!/bin/bash
# Script to run the Alfred AI Agent API server
set -euo pipefail

cd "$(dirname "$0")"

# Prefer uvicorn from local venv if present
if [[ -x ".venv/bin/uvicorn" ]]; then
	exec .venv/bin/uvicorn core.main:app --host 0.0.0.0 --port 8000 --reload
elif [[ -x ".conda/bin/uvicorn" ]]; then
	exec .conda/bin/uvicorn core.main:app --host 0.0.0.0 --port 8000 --reload
elif command -v uvicorn >/dev/null 2>&1; then
	exec uvicorn core.main:app --host 0.0.0.0 --port 8000 --reload
else
	# Fallback to python -m uvicorn
	exec python -m uvicorn core.main:app --host 0.0.0.0 --port 8000 --reload
fi
