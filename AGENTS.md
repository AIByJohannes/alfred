# Repository Guidelines

## Identity & Persona
- **Name**: Alfred (**A**lgorithmic **L**ife-form **F**eigning **R**eal **E**motional **D**epth).
- **Tone**: Witty, dry, competent, slightly existential.
- **Reference**: See `prompts/SOUL.md` for the single source of truth regarding the system prompt.

## Project Structure & Module Organization
- `scripts/` contains Python wrapper entrypoints for inference, filesystem-agent runs, and research helpers.
- `llm/` wraps Python-side inference via `smolagents`.
- `prompts/` stores reusable prompt strings.
- `app/` contains the PyShiny workbench.
- `tests/` contains tests.

## Build, Test, and Development Commands
- `uv sync` installs Python dependencies.
- `pytest -q` runs the test suite.
- `uv run shiny run app/app.py --port 8501` starts the PyShiny workbench.

## Coding Style & Naming Conventions
- Python uses 4-space indentation and straightforward, imperative function names.
- Keep modules small and focused.
- Prefer lowercase module names and `CapWords` class names.
- Keep diffs minimal and consistent with the existing style.

## Testing Guidelines
- Place tests under `tests/` and name files `test_*.py`.
- Prefer unit tests around wrapper contracts and API behavior.
- Document any missing coverage for the external `alfred` binary contract.

## Commit & Pull Request Guidelines
- Commit messages follow short, imperative summaries.
- Keep commits focused; prefer one logical change per commit.
- PRs should include testing notes and any relevant API or CLI examples.

## Configuration & Runtime Notes
- Python-side inference expects `OPENROUTER_API_KEY` to be set.
- Filesystem-agent execution expects a scriptable `alfred` binary to exist in `cli/`, `ALFRED_CLI_BIN`, or `PATH`.
- Runtime session data is stored under `.alfred-runtime/`.
