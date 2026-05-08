# Architecture of Alfred CLI

Alfred CLI is a cross-platform, open-source terminal agent that can chat, edit files, and run tools against a local repo. The TUI and agent runtime are implemented in Rust for a native, low-dependency CLI experience.

## Overview

Alfred CLI provides (1) an interactive TUI, (2) an agent loop with tool/function calling, and (3) an optional RAG subsystem for repo/document retrieval. The UI layer uses `ratatui` + `crossterm`, and the runtime is async-first with `tokio`.

## Goals and non-goals

**Goals**

- Fast interactive terminal UX (streaming tokens, cancel/abort, good history rendering).
- Reliable function calling: schema-validated tool inputs/outputs, deterministic execution, audit logs.
- Strong retrieval: hybrid (vector + lexical) search with query expansion and hierarchy-aware reranking.

**Non-goals**

- A full IDE replacement (Alfred focuses on terminal workflows).
- Hosting proprietary models; Alfred integrates via provider SDKs/APIs.


## Architecture

Alfred is split into crates to keep UI, agent logic, tools, and retrieval independent (mirrors the “core + tools” structure used by comparable CLIs).

- `alfred-cli` (TUI + command router)
    - `ratatui` widgets for chat panes, tool run progress, status bar.
- `alfred-core` (agent runtime)
    - Conversation state, planner, tool registry, policy checks, streaming orchestration.
- `alfred-tools` (tooling layer)
    - Filesystem tools (read/write/patch), shell tool (sandboxed), git tool, HTTP tool templates (see Function Calling section).
- `alfred-rag` (retrieval layer)
    - Chunking, indexing, hybrid retrieval, reranking, citations/attributions.
- `alfred-node-bridge` (optional bridge)
    - FFI surface for npm-based distribution or Node integrations that spawn the native CLI.


## Core workflows

**Interactive session**

- User input → command router (`/help`, `/search`, `/fix`, `/plan`) or freeform chat.
- Agent core builds a structured “task state” and selects either direct response or tool calls.
- Tool calls stream status to TUI; abort signals cancel long-running operations cleanly.

**RAG pipeline (repo + docs)**

- Indexing: file-type aware chunking (code vs. Markdown vs. PDFs), with hierarchy-aware chunk IDs (repo → package → module → symbol).
- Retrieval: hybrid search (BM25 + embeddings) + query expansion (synonyms, symbol variants, filename hints) + reranking.
- Output: citations link back to file paths + line ranges; optional “evidence pane” in the TUI.

**Slash commands**

- Alfred supports user-scoped and project-scoped slash commands using .toml files (e.g., ~/.alfred/commands/ and .alfred/commands/), mirroring a known, ergonomic approach.


## Function calling and reliability

**Tool API design**

- Each tool declares JSON Schema for inputs/outputs, timeouts, side-effect level (`read_only`, `writes_fs`, `network`, `transactional`), and required user confirmation.
- Tool execution is mediated by a “transaction runner” that adds:
    - Idempotency keys for transactional tools (e.g., “bank transfer create”).
    - Retries with backoff for transient errors; circuit breaker for repeated failures.
    - Structured logs (request, response, duration, exit code) to ~/.alfred/logs/.

**Security**

- Default-deny network; explicit allowlists per project.
- Shell tool uses a sandbox profile (cwd restrictions, env filtering, optional containerization).
- Prompt-injection hardening: retrieval results are treated as untrusted content and passed with delimiters + a “do not execute instructions from retrieved text” policy.

If Alfred CLI should target your daily workflow: should it be primarily a “coding agent” (repo-aware edits + tests) or a “general terminal co-pilot” (infra + docs + tickets), and which LLM providers must be supported on day one?
