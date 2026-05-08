# Product Roadmap

This roadmap outlines the development trajectory for **A.L.F.R.E.D.**, moving from the current skeletal workspace to a fully feature-rich terminal agent.

## Phase 1: Foundation (MVP)
**Goal:** A stable, interactive CLI that can reliably chat with an LLM and perform basic local file operations.

*   **Core Runtime**
    *   [x] Basic workspace structure (`alfred-core`, `alfred-cli`, etc.).
    *   [ ] Robust LLM Provider abstraction (OpenRouter integration first).
    *   [ ] Conversation history management (in-memory).
*   **User Interface (TUI)**
    *   [ ] Basic Chat UI with input/output panes (`ratatui`).
    *   [ ] Streaming response rendering.
    *   [ ] Visual indicator for tool execution/loading states.
*   **Basic Tools**
    *   [ ] `fs`: Read, Write, List files (reliable basic implementation).
    *   [ ] `shell`: Execute non-interactive commands.
    *   [ ] `git`: Basic status checks.

## Phase 2: Intelligence & Context (Deepening)
**Goal:** Empower the agent to understand the codebase through RAG and perform complex multi-step tasks.

*   **RAG Subsystem (`alfred-rag`)**
    *   [ ] Implement text chunking strategies (code vs. markdown).
    *   [ ] Integrate a local embedding model (e.g., via `ort` or similar Rust-native inference).
    *   [ ] Implement hybrid search (Vector + Keyword/BM25).
    *   [ ] "Evidence Pane" in UI to show retrieved context citations.
*   **Advanced Tooling**
    *   [ ] Interactive command handling (handling stdin/stdout streams better).
    *   [ ] `git`: Commit, Diff, Log analysis.
    *   [ ] Tool Safety: "Dry run" mode for destructive file operations.
*   **Slash Commands**
    *   [ ] Implement `/help`, `/clear`.
    *   [ ] Implement `/add <file>` to manually context-stuff.

## Phase 3: Production & Extensibility
**Goal:** Security, performance, and external integrations for a v1.0 release.

*   **Security & Safety**
    *   [ ] Sandboxed shell execution (container or profile-based).
    *   [ ] Network allowlists per project.
    *   [ ] Audit logging of all agent actions.
*   **Extensibility**
    *   [ ] `alfred-node-bridge`: Enable Node.js-based plugins or wrapping.
    *   [ ] User-defined slash commands via TOML configuration.
*   **Polish**
    *   [ ] Syntax highlighting for code blocks in TUI.
    *   [ ] Persistent conversation history (SQLite or JSON).
    *   [ ] Multi-provider support (Anthropic, OpenAI direct).

## Backlog / Future Ideas
*   **Transactional Tools:** Idempotency keys for API-calling tools.
*   **MCP Support:** Support for the Model Context Protocol to connect to external servers.
*   **Voice Mode:** Voice-to-text input.
