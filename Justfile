set shell := ["bash", "-eu", "-o", "pipefail", "-c"]

setup:
    uv sync
    cd frontend && npm install

backend:
    uv run uvicorn main:app --reload

frontend:
    cd frontend && npm run dev

dev:
    bash scripts/dev.sh
