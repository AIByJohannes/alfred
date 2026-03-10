# Alfred Local Workbench Roadmap

## Current Direction

The repo has been cut over from a backend microservice project into a local-first Python + Rust workbench.

## Near-Term Work

1. Finish the non-interactive `alfred run` contract in `../alfred-cli`
2. Stream structured filesystem-agent events into the Vite workbench
3. Expand artifact inspection and session recovery in `.alfred-runtime/`
4. Harden research helpers and optional storage backends

## External Dependency

The main blocker for true end-to-end filesystem execution is the Rust CLI contract:

- `alfred run --jsonl`
- prompt and cwd input
- structured stdout events suitable for Python relay

Until that exists, the Python wrapper and FastAPI bridge remain ready but partially mocked by contract.
