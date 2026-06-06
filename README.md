# A.L.F.R.E.D.

**A**lgorithmic **L**ife-form **F**eigning **R**eal **E**motional **D**epth

![PyShiny](https://img.shields.io/badge/-PyShiny-2176FF?style=flat&logo=shiny&logoColor=white)
![Python](https://img.shields.io/badge/-Python-3776AB?style=flat&logo=python&logoColor=white)
![Rust](https://img.shields.io/badge/-Rust-000000?style=flat&logo=rust&logoColor=white)

Alfred is a local-first Python orchestration repo. It provides a PyShiny workbench and Python wrapper scripts around the Rust `alfred` binary in `cli/`.

## Layout

```text
alfred/
├── frontend/     # PyShiny workbench
├── llm/          # Python-side inference wrapper
├── prompts/      # Canonical system prompts
├── scripts/      # Python wrappers for inference, fs-agent, research
├── tests/        # Tests
├── models.py     # Data models
└── pyproject.toml
```

## Runtime Model

- Python handles local orchestration, inference calls, web-grounded helper scripts, and filesystem session state.
- The Rust `alfred` binary handles filesystem-capable agent execution.
- Filesystem-agent calls support a `backend` selector (`auto`, `alfred-cli`, `smolagents`); the default `auto` prefers `alfred-cli` and falls back to `smolagents` when the binary is unavailable.
- The PyShiny workbench imports Python wrappers directly.
- Runtime state is stored under `.alfred-runtime/`.
- Database support is optional and not part of the default path.

## Requirements

- Python 3.12+
- `uv`
- A built or installed `alfred` binary from `cli/target/debug/alfred`
- `OPENROUTER_API_KEY` for Python-side inference
- Conda (for GPU/transcription features)

## Quick Start

```bash
# One-time setup: creates Conda env with CUDA, installs Python deps
just setup

# Run the PyShiny workbench (calls Python wrappers directly)
just frontend
```

## Frontend

The PyShiny workbench imports Python wrappers directly (no API proxy needed):

```bash
uv run shiny run frontend/app.py --port 8501
```

It runs on `http://localhost:8501` by default.

## CLI Wrapper Scripts

```bash
python -m scripts.infer "Summarize this repo"
python -m scripts.fs_agent "Refactor the logging layer" --cwd /path/to/repo
python -m scripts.research "ACP protocol Python examples"
```

## Environment

See [`.env.example`](.env.example) for settings. The most important variables are:

- `OPENROUTER_API_KEY`
- `ALFRED_CLI_BIN`
- `ALFRED_RUNTIME_ROOT`
- `ALFRED_AGENT_MODE`

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

## Notes

- `prompts/SOUL.md` is the canonical system prompt source.
- `scripts/fs_agent.py` assumes a future non-interactive `alfred run` contract in `cli/`.
- The old Spring Boot, Next.js, and Postgres microservice setup has been retired from this repo.
