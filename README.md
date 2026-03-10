# A.L.F.R.E.D.

**A**lgorithmic **L**ife-form **F**eigning **R**eal **E**motional **D**epth

![FastAPI](https://img.shields.io/badge/-FastAPI-009688?style=flat&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/-React-61DAFB?style=flat&logo=react&logoColor=000000)
![Vite](https://img.shields.io/badge/-Vite-646CFF?style=flat&logo=vite&logoColor=white)
![Python](https://img.shields.io/badge/-Python%203.12-3776AB?style=flat&logo=python&logoColor=white)
![Rust](https://img.shields.io/badge/-Alfred%20CLI-000000?style=flat&logo=rust&logoColor=white)

Alfred is now a local-first Python orchestration repo. It provides a thin FastAPI bridge, a small React + Vite workbench, and Python wrapper scripts around the Rust `alfred` binary in `../alfred-cli`.

## Layout

```text
alfred/
├── frontend/     # React + Vite workbench
├── llm/          # Python-side inference wrapper
├── prompts/      # Canonical system prompts
├── scripts/      # Python wrappers for inference, fs-agent, research
├── tests/        # Backend tests
├── main.py       # FastAPI bridge for the local workbench
├── models.py     # API request/response models
└── pyproject.toml
```

## Runtime Model

- Python handles local orchestration, inference calls, web-grounded helper scripts, and filesystem session state.
- The Rust `alfred` binary handles filesystem-capable agent execution.
- FastAPI exists only as a local bridge for the frontend.
- Runtime state is stored under `.alfred-runtime/`.
- Database support is optional and not part of the default path.

## Requirements

- Python 3.12+
- `uv`
- Node.js 20+
- A built or installed `alfred` binary from `../alfred-cli`
- `OPENROUTER_API_KEY` for Python-side inference

## Backend Setup

```bash
uv sync
uv run uvicorn main:app --reload
```

The API runs on `http://127.0.0.1:8000`.

### FastAPI Endpoints

- `GET /health`
- `POST /api/infer/stream`
- `POST /api/fs-agent/stream`

Both POST routes return SSE streams with event types `meta`, `delta`, `artifact`, `done`, and `error`.

## Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The Vite workbench runs on `http://127.0.0.1:5173`.

## CLI Wrapper Scripts

```bash
python -m scripts.infer "Summarize this repo"
python -m scripts.fs_agent "Refactor the logging layer" --cwd /path/to/repo
python -m scripts.research "ACP protocol Python examples"
```

## Environment

See [`.env.example`](.env.example) for backend settings. The most important variables are:

- `OPENROUTER_API_KEY`
- `ALFRED_CLI_BIN`
- `ALFRED_RUNTIME_ROOT`
- `ALFRED_AGENT_MODE`

## Notes

- `prompts/SOUL.md` is the canonical system prompt source.
- `scripts/fs_agent.py` assumes a future non-interactive `alfred run` contract in `../alfred-cli`.
- The old Spring Boot, Next.js, and Postgres microservice setup has been retired from this repo.
