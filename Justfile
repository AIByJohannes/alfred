set shell := ["bash", "-eu", "-o", "pipefail", "-c"]

conda_env := "alfred-cuda"

default: run

alias dev := run

# ── Environment install ────────────────────────────────

# Update or create the CUDA conda environment
install-conda:
    conda env update -f environment.cuda.yml --prune || conda env create -f environment.cuda.yml

# Install Python dependencies (including transcribe extras)
install-python:
    conda run -n {{conda_env}} uv sync --active --extra transcribe

install: install-conda install-python

# ── Application ────────────────────────────────────────

# Launch the Gradio workbench with file watching / live reload
run:
    conda run -n {{conda_env}} --live-stream uv run --active gradio app/app.py --watch-dirs app

# ── Python checks ──────────────────────────────────────

# Run the test suite
test:
    conda run -n {{conda_env}} --live-stream uv run --active pytest -q

# Run tests with verbose output
test-verbose:
    conda run -n {{conda_env}} --live-stream uv run --active pytest -v

# Lint with ruff
lint:
    conda run -n {{conda_env}} --live-stream uv run --active ruff check .

# Type-check with mypy
typecheck:
    conda run -n {{conda_env}} --live-stream uv run --active mypy .

# Run lint, typecheck, and tests
check: lint typecheck test

# ── Cleanup ────────────────────────────────────────────

# Remove runtime session data
clean:
    rm -rf .alfred-runtime

# ── Rust CLI ───────────────────────────────────────────

# Clean CLI build artifacts
cli-clean:
    cargo clean --manifest-path cli/Cargo.toml

# Build the CLI in debug mode
cli-build:
    cargo build --manifest-path cli/Cargo.toml --workspace

# Build the CLI in release mode
cli-build-release:
    cargo build --manifest-path cli/Cargo.toml --workspace --release

# Run CLI tests
cli-test:
    cargo test --manifest-path cli/Cargo.toml --workspace

# Run the CLI crate directly
cli-run:
    cargo run --manifest-path cli/Cargo.toml -p alfred-cli

# Lint CLI with clippy (deny warnings)
cli-check:
    cargo clippy --manifest-path cli/Cargo.toml --workspace --all-targets -- -D warnings

# Install the CLI binary
cli-install:
    cargo install --path cli/crates/alfred-cli --locked

# ── Prompt sync ────────────────────────────────────────

# Download the latest SOUL.md prompt from the main branch
cli-update-prompts:
    mkdir -p cli/prompts
    curl -o cli/prompts/SOUL.md https://raw.githubusercontent.com/AIByJohannes/alfred/refs/heads/main/core/prompts/SOUL.md
