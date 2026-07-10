# Alfred Local Workbench Roadmap

## Current Direction

The repo has been cut over from a backend microservice project into a local-first Python + Rust workbench.

## Completed

1. (DONE) Finish the native agent transport in `cli/`
   - Added `alfred acp` as the workbench's stdio protocol.
   - Outputs JSONL events (`meta`, `delta`, `tool_request`, `tool_result`, `done`, `error`).
   - Uses the Rust/Cersei agent runtime exclusively.

2. (DONE) Migrate Rust CLI execution to the Cersei crate SDK
   - Replaced legacy unary OpenRouter routing in TUI chat mode, JSONL mode, and ACP mode.
   - Added persistent transcript and graph memory through `cersei-memory`.
   - Preserves Python runtime session IDs via `alfred run --session-id`.

## Near-Term Work

1. Stream structured filesystem-agent events into the Vite workbench
2. Expand artifact inspection and session recovery in `.alfred-runtime/`
3. Harden research helpers and optional storage backends

## External Dependency

The CLI contract is now implemented. Next steps focus on the Python bridge and frontend integration.
