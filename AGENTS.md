# Repository Guidelines

## Identity & Persona
- **Name**: Alfred (**A**lgorithmic **L**ife-form **F**eigning **R**eal **E**motional **D**epth).
- **Tone**: Witty, dry, competent, slightly existential.
- **Reference**: See `core/prompts/SOUL.md` for the single source of truth regarding the agent's system prompt.

## Project Structure & Module Organization
- `core/` contains the FastAPI backend and LLM integration.
  - `core/main.py` defines the API routes and app lifecycle.
  - `core/llm/` wraps smolagents and the Ollama model connection.
  - `core/prompts/` stores reusable prompt strings.
  - `core/models.py` holds request/response schemas.
- `app/` is reserved for the frontend client (currently empty except `.gitkeep`).
- `requirements.txt` lists Python dependencies.
- `run_server.sh` starts the API server with uvicorn.

## Build, Test, and Development Commands
- `python -m venv .venv` and `source .venv/bin/activate` to create/activate a local virtualenv.
- `pip install -r requirements.txt` installs backend dependencies.
- `./run_server.sh` runs the FastAPI server at `http://0.0.0.0:8000` with reload.
- `python -m uvicorn core.main:app --reload` is a manual alternative to the script.

## Coding Style & Naming Conventions
- Python uses 4-space indentation and straightforward, imperative function names.
- Keep modules small and focused (API routing in `core/main.py`, logic in `core/llm/`).
- Prefer lowercase module names and `CapWords` class names (e.g., `LLMEngine`).
- No formatter or linter is currently configured; keep diffs minimal and consistent with existing style.

## Testing Guidelines
- No automated tests are present yet. If adding tests, place them under `tests/` and name files `test_*.py`.
- If you introduce tests, document how to run them (for example, `pytest -q`).

## Commit & Pull Request Guidelines
- Commit messages follow short, imperative summaries (e.g., “Add tech stack badges to README”).
- Keep commits focused; prefer one logical change per commit.
- PRs should include a clear description, testing notes (even if “not run”), and any relevant API examples.

## Configuration & Runtime Notes
- The LLM engine expects Ollama to be running and serving the model ID `ollama_chat/qwen2:7b` by default.
- If the model is unavailable, the API starts but `/run` and `/fibonacci` return `503` until fixed.
