# Alfred Local Workbench Architecture

## Overview

This repository is a local-first orchestration layer around the Rust `alfred` binary in `../alfred-cli`.

- **React + Vite workbench**: single-page local UI for prompt submission and streamed output
- **FastAPI bridge**: local-only API that relays requests to Python wrappers
- **Python wrappers**: inference, filesystem-agent execution, and web-grounded helper scripts
- **Rust `alfred` binary**: filesystem-capable agent runtime
- **Filesystem runtime**: session logs, artifacts, and results under `.alfred-runtime/`

## Flow

```mermaid
graph TD
    User[User]
    UI[React + Vite Workbench]
    API[FastAPI Bridge]
    PY[Python Wrappers]
    CLI[../alfred-cli / alfred run]
    FS[(.alfred-runtime)]
    LLM[OpenRouter]

    User --> UI
    UI -->|SSE requests| API
    API --> PY
    PY -->|inference| LLM
    PY -->|fs-agent| CLI
    PY --> FS
    CLI --> FS
    API -->|SSE events| UI
```

## Responsibilities

### FastAPI bridge

- Exposes `/health`, `/api/infer/stream`, and `/api/fs-agent/stream`
- Owns no business logic beyond request validation and SSE relaying
- Reports `alfred` binary availability to the frontend

### Python wrapper layer

- Creates session directories and persists request/event/result files
- Runs Python-side inference via `smolagents`
- Runs quick research helpers via Python
- Invokes `alfred run` for filesystem-capable work
- Normalizes outputs into `meta`, `delta`, `artifact`, `done`, and `error` events
- Determines the filesystem-agent backend (`alfred-cli` or `smolagents`) per request, defaulting to the CLI but falling back to `smolagents` when the binary is missing and including the chosen backend in the metadata stream.

### Rust CLI dependency

The Python filesystem wrapper invokes the non-interactive CLI contract in `../alfred-cli`:

- Command: `alfred run --jsonl --mode <mode> --prompt <prompt> --cwd <cwd>`
- Input: prompt, cwd, mode flags
- Output: JSONL/ACP-aligned structured events over stdout (`meta`, `delta`, `tool_request`, `tool_result`, `done`, `error`)

The CLI contract is now implemented. The Rust binary serves both the interactive TUI and the scriptable run subcommand.
