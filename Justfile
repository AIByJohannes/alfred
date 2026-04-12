set shell := ["bash", "-eu", "-o", "pipefail", "-c"]

default: dev

setup:
    uv sync
    cd frontend && npm install

backend:
    uv run uvicorn main:app --reload

frontend:
    cd frontend && npm run dev

dev:
    bash scripts/dev.sh

test:
    pytest -q

test-verbose:
    pytest -v

lint:
    ruff check .
    cd frontend && npm run build

typecheck:
    mypy .
    cd frontend && npx tsc -b

build: build-frontend

build-frontend:
    cd frontend && npm run build

prod: build-frontend
    uv run uvicorn main:app --host 0.0.0.0 --port 8000

clean:
    rm -rf frontend/dist
    rm -rf .alfred-runtime
