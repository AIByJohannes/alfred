from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from scripts.common import (
    build_alfred_run_command,
    build_arg_parser,
    ensure_session,
    print_event,
    relay_subprocess,
)


async def stream_filesystem_agent(
    prompt: str,
    *,
    cwd: str | None = None,
    session_id: str | None = None,
) -> AsyncIterator[dict[str, object]]:
    session_id, session_dir = ensure_session(session_id)
    command = build_alfred_run_command(prompt, cwd=cwd)
    request_payload = {
        "type": "fs-agent",
        "prompt": prompt,
        "cwd": cwd,
        "session_id": session_id,
        "command": command,
    }

    async for payload in relay_subprocess(
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
    asyncio.run(_main())
