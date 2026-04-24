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
- Filesystem-agent calls now support a `backend` selector (`auto`, `alfred-cli`, `smolagents`); the default `auto` prefers `alfred-cli` and falls back to `smolagents` when the binary is unavailable.
- FastAPI exists only as a local bridge for the frontend.
- Runtime state is stored under `.alfred-runtime/`.
- Database support is optional and not part of the default path.

## Requirements

- Python 3.12+
- `uv`
- Node.js 20+
- A built or installed `alfred` binary from `../alfred-cli`
- `OPENROUTER_API_KEY` for Python-side inference
- Conda (for GPU/transcription features)

## Quick Start

```bash
# One-time setup: creates Conda env with CUDA, installs Python + frontend deps
just setup

# Run both backend and frontend
just dev

# Or run them separately:
just backend   # API on http://127.0.0.1:8000
just frontend # UI on http://127.0.0.1:5173
```

## Backend Setup (Manual)

If you don't use `just`:

```bash
# GPU environment (recommended for transcription)
conda env create -f environment.cuda.yml
conda activate alfred-cuda
uv sync --extra transcribe

# Or without GPU
uv sync

uv run uvicorn main:app --reload
```

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
If the backend is already running, `just frontend` is the browser entrypoint.

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
- `CORS_ORIGINS` (optional, defaults to `http://localhost:5173,http://127.0.0.1:5173`)

## Production

Build the frontend:

```bash
cd frontend && npm run build
```

Run the backend - it automatically serves the built frontend from `frontend/dist`:

```bash
uv run uvicorn main:app --host 0.0.0.0 --port 8000
```

The API and UI are served from the same origin, avoiding CORS issues.

## Transcription (Audio to Text)

Alfred supports local audio transcription using Whisper models via faster-whisper with CUDA acceleration.

### GPU Setup (Recommended for RTX 4080)

Create a Conda environment with CUDA 12.4 and PyTorch:

```bash
conda env create -f environment.cuda.yml
conda activate alfred-cuda
```

Then sync the project with the transcription extra:

```bash
uv sync --active --extra transcribe
```

Verify GPU access:

```bash
uv run --active python -c "import torch; print('CUDA:', torch.cuda.is_available(), 'Version:', torch.version.cuda)"
```

### Usage

1. Open the Alfred web interface
2. Click the microphone icon in the chat input area
3. Speak — click the microphone icon again to stop
4. The transcript appears in the input box, ready to send or edit

### Configuration

See `.env.example` for transcription settings:

- `ALFRED_TRANSCRIBE_BACKEND` (default: `faster-whisper`)
- `ALFRED_TRANSCRIBE_MODEL` (default: `openai/whisper-large-v3-turbo`)
- `ALFRED_TRANSCRIBE_DEVICE` (default: `cuda`)
- `ALFRED_TRANSCRIBE_COMPUTE_TYPE` (default: `float16`)
- `ALFRED_TRANSCRIBE_LANGUAGE` (default: `auto` - auto-detect, use `de` for German)
- `ALFRED_TRANSCRIBE_WORD_TIMESTAMPS` (default: `false`)
- `ALFRED_TRANSCRIBE_VAD` (default: `true` - voice activity detection)
- `ALFRED_TRANSCRIBE_CHUNK_SECONDS` (default: `30`)
- `ALFRED_TRANSCRIBE_BATCH_SIZE` (default: `8`)
- `ALFRED_TRANSCRIBE_MODEL_CACHE` (default: `.alfred-runtime/models/transcription`)

### Supported Models

- **Default**: `openai/whisper-large-v3-turbo` - fast, good quality
- **Quality fallback**: `openai/whisper-large-v3` - slower, highest quality
- **Alternative**: `nvidia/parakeet-tdt-0.6b-v3` - requires NeMo installation

### API Endpoints

- `POST /api/transcribe` - Upload audio file for transcription
- `GET /api/transcription/health` - Check transcription service status

## Notes

- `prompts/SOUL.md` is the canonical system prompt source.
- `scripts/fs_agent.py` assumes a future non-interactive `alfred run` contract in `../alfred-cli`.
- The health endpoint now reports both the available backends and the resolved default backend so the UI can show which one actually ran.
- The old Spring Boot, Next.js, and Postgres microservice setup has been retired from this repo.
