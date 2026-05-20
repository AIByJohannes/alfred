set shell := ["bash", "-eu", "-o", "pipefail", "-c"]

default: dev

conda_env := "alfred-cuda"

setup-conda:
    conda env update -f environment.cuda.yml --prune || conda env create -f environment.cuda.yml

setup-python:
    conda run -n {{conda_env}} uv sync --active --extra transcribe

setup: setup-conda setup-python

backend:
    conda run -n {{conda_env}} --live-stream uv run --active uvicorn main:app --reload

frontend:
    conda run -n {{conda_env}} --live-stream uv run --active streamlit run frontend/app.py --server.port 8501

dev:
    #!/usr/bin/env bash
    set -eu -o pipefail -o posix
    trap 'kill $(jobs -p) 2>/dev/null' EXIT INT TERM
    conda run -n {{conda_env}} --live-stream uv run --active uvicorn main:app --reload &
    conda run -n {{conda_env}} --live-stream uv run --active streamlit run frontend/app.py --server.port 8501

test:
    conda run -n {{conda_env}} --live-stream uv run --active pytest -q

test-verbose:
    conda run -n {{conda_env}} --live-stream uv run --active pytest -v

lint:
    conda run -n {{conda_env}} --live-stream uv run --active ruff check .

typecheck:
    conda run -n {{conda_env}} --live-stream uv run --active mypy .

prod:
    conda run -n {{conda_env}} --live-stream uv run --active uvicorn main:app --host 0.0.0.0 --port 8000

clean:
    rm -rf .alfred-runtime

cli-clean:
    cargo clean --manifest-path cli/Cargo.toml

cli-build:
    cargo build --manifest-path cli/Cargo.toml --workspace

cli-build-release:
    cargo build --manifest-path cli/Cargo.toml --workspace --release

cli-test:
    cargo test --manifest-path cli/Cargo.toml --workspace

cli-run:
    cargo run --manifest-path cli/Cargo.toml -p alfred-cli

cli-check:
    cargo clippy --manifest-path cli/Cargo.toml --workspace --all-targets -- -D warnings

cli-install:
    cargo install --manifest-path cli/Cargo.toml --path cli/crates/alfred-cli --locked

cli-update-prompts:
    mkdir -p cli/prompts
    curl -o cli/prompts/SOUL.md https://raw.githubusercontent.com/AIByJohannes/alfred/refs/heads/main/core/prompts/SOUL.md
