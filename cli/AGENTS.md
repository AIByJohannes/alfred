# A.L.F.R.E.D. CLI Context

## Project Overview

**A.L.F.R.E.D.** (**A**gentic **L**ocal **F**ramework for **R**epository **E**nhancement and **D**evelopment) is a cross-platform, open-source terminal agent designed to assist with software engineering tasks directly from the shell. It features a modern TUI built with Rust (`ratatui`) and connects to LLM providers to perform interactive chat, file editing, tool execution, and RAG-based context retrieval.

## Architecture

The project is organized as a Rust workspace with the following crates:

*   **`alfred-cli`**: The user interface entry point. Handles the TUI (using `ratatui` + `crossterm`), command routing, and rendering.
*   **`alfred-core`**: The agent runtime. Manages conversation state, planning, the tool registry, and orchestration of LLM interactions.
*   **`alfred-tools`**: Provides capabilities for the agent to interact with the system, including filesystem operations, shell execution, and git commands.
*   **`alfred-rag`**: The retrieval-augmented generation layer. Handles indexing, chunking, and searching of the codebase and documentation.
*   **`alfred-node-bridge`**: An optional bridge for Node.js integrations.

## Building and Running

### Prerequisites
*   Stable Rust toolchain
*   [just](https://github.com/casey/just) command runner

### Key Commands

*   **Build Workspace:**
    ```bash
    cargo build --workspace
    # or via justfile
    just build
    ```

*   **Run CLI (Local Development):**
    ```bash
    cargo run -p alfred-cli
    ```

*   **Install (to Cargo bin):**
    ```bash
    just install
    # Equivalent to: cargo install --path crates/alfred-cli --locked
    ```

*   **Run Tests:**
    ```bash
    cargo test --workspace
    # or via justfile
    just test
    ```

*   **Clean:**
    ```bash
    just clean
    ```

## Development Conventions

*   **Language:** Rust (2021 edition).
*   **Async Runtime:** `tokio` is used for asynchronous operations.
*   **Error Handling:** Uses `anyhow` and `thiserror`.
*   **Logging:** Uses `tracing` and `tracing-subscriber`.
*   **Workspace:** All logic is separated into distinct crates under `crates/` to enforce separation of concerns between UI, Core Logic, Tools, and RAG.

## Key Features

*   **Interactive Chat:** TUI-based chat interface.
*   **File Editing:** Capabilities to read, write, and patch files.
*   **Tool Execution:** Safe execution of shell commands and git operations.
*   **RAG:** Indexing and retrieval of code and documentation context.
