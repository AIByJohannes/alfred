from __future__ import annotations

import shlex
from collections.abc import AsyncGenerator

from models import (
    FS_AGENT_BACKEND_AUTO,
    FsAgentBackend,
)
from scripts.common import (
    build_alfred_acp_command,
    build_arg_parser,
    ensure_session,
    event,
    print_event,
    relay_acp_subprocess,
    select_fs_agent_backend,
)


async def stream_filesystem_agent(
    prompt: str,
    *,
    cwd: str | None = None,
    session_id: str | None = None,
    backend: FsAgentBackend = FS_AGENT_BACKEND_AUTO,
    images: list[dict[str, str]] | None = None,
) -> AsyncGenerator[dict[str, object], None]:
    selected_backend, binary = select_fs_agent_backend(backend)
    session_id, session_dir = ensure_session(session_id)
    if binary is None:
        message = (
            "No ACP-capable `alfred` binary found. Set ALFRED_CLI_BIN or build "
            "the Rust CLI with `just cli-build`."
        )
        yield event("meta", session_id=session_id, backend=selected_backend, transport="acp")
        yield event("error", session_id=session_id, message=message)
        return

    command = build_alfred_acp_command(cwd=cwd, binary_override=binary)
    request_payload: dict[str, object] = {
        "type": "fs-agent",
        "prompt": prompt,
        "cwd": cwd,
        "session_id": session_id,
        "backend": selected_backend,
        "transport": "acp",
        "command": shlex.join(command),
    }
    if images:
        request_payload["images"] = images
    async for payload in relay_acp_subprocess(
        command,
        session_dir=session_dir,
        request_payload=request_payload,
        cwd=cwd,
    ):
        payload.setdefault("session_id", session_id)
        yield payload


async def _main() -> None:
    parser = build_arg_parser(
        "python -m scripts.fs_agent",
        "Run the filesystem-capable Alfred CLI wrapper.",
        include_cwd=True,
    )
    args = parser.parse_args()

    async for payload in stream_filesystem_agent(
        args.prompt,
        cwd=args.cwd,
        session_id=args.session_id,
    ):
        print_event(payload)


if __name__ == "__main__":
    import asyncio

    asyncio.run(_main())
