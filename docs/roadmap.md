# Alfred Local Workbench Roadmap

## Current Direction

The repo has been cut over from a backend microservice project into a local-first Python + Rust workbench.

## Completed

1. (DONE) Finish the non-interactive `alfred run` contract in `../alfred-cli`
   - Added `alfred run --jsonl --mode fs-agent --prompt <prompt> --cwd <cwd>`
   - Outputs JSONL events (`meta`, `delta`, `tool_request`, `tool_result`, `done`, `error`)
   - Falls back to smolagents when CLI binary is unavailable

## Near-Term Work

1. Stream structured filesystem-agent events into the Vite workbench
2. Expand artifact inspection and session recovery in `.alfred-runtime/`
3. Harden research helpers and optional storage backends

## External Dependency

The CLI contract is now implemented. Next steps focus on the Python bridge and frontend integration.
