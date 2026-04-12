set shell := ["bash", "-eu", "-o", "pipefail", "-c"]

default: dev

conda_env := "alfred-cuda"

setup-conda:
    conda env update -f environment.cuda.yml --prune || conda env create -f environment.cuda.yml

setup-python:
    conda run -n {{conda_env}} uv sync --active --extra transcribe

setup-frontend:
    cd frontend && npm install

setup: setup-conda setup-python setup-frontend

backend:
    conda run -n {{conda_env}} uv run --active uvicorn main:app --reload

frontend:
    cd frontend && npm run dev

dev: backend frontend

test:
    conda run -n {{conda_env}} uv run --active pytest -q

test-verbose:
    conda run -n {{conda_env}} uv run --active pytest -v

lint:
    conda run -n {{conda_env}} uv run --active ruff check .
    cd frontend && npm run build

typecheck:
    conda run -n {{conda_env}} uv run --active mypy .
    cd frontend && npx tsc -b

build: build-frontend

build-frontend:
    cd frontend && npm run build

prod: build-frontend
    conda run -n {{conda_env}} uv run --active uvicorn main:app --host 0.0.0.0 --port 8000

clean:
    rm -rf frontend/dist
    rm -rf .alfred-runtime
