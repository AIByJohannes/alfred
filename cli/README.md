# A.L.F.R.E.D. CLI

![Rust](https://img.shields.io/badge/-Rust-000000?style=flat&logo=rust&logoColor=white)

**A.L.F.R.E.D.** (**A**gentic **L**ocal **F**ramework for **R**epository **E**nhancement and **D**evelopment) is a cross-platform, open-source terminal agent designed to assist with software engineering tasks directly from your shell.

## Overview

Alfred CLI provides a modern, interactive terminal user interface (TUI) built with Rust ([ratatui](https://github.com/ratatui/ratatui) + crossterm). It features a pluggable agent core that connects to various LLM providers to perform tasks such as:

*   **Interactive Chat:** coding assistance, debugging, and general inquiries.
*   **File Editing:** Reading, writing, and patching files within your local repository.
*   **Tool Execution:** Running shell commands, git operations, and custom tools safely.
*   **RAG (Retrieval-Augmented Generation):** Indexing and searching your codebase and documentation for context-aware answers.

## Architecture

The project is structured as a Rust workspace with the following crates:

*   **`alfred-cli`**: The TUI entry point, command router, and UI components.
*   **`alfred-core`**: The agent runtime, handling conversation state, planning, and orchestration.
*   **`alfred-tools`**: A collection of tools for filesystem access, shell execution, and git operations.
*   **`alfred-rag`**: The retrieval layer for indexing and searching code and documents.
*   **`alfred-node-bridge`**: Optional native bridge for npm-based distribution or Node integrations.

## Getting Started

### Prerequisites

*   Rust toolchain (stable)
*   [just](https://github.com/casey/just) command runner

### Installation

```bash
git clone https://github.com/AIByJohannes/alfred-cli.git
cd alfred-cli
just install
```

This will build and install the `alfred` binary to your Cargo bin directory (usually `~/.cargo/bin`). Make sure this directory is in your `PATH`.

To run locally:

```bash
cargo run -p alfred-cli
```

### Running Tests

```bash
cargo test
```
