from __future__ import annotations

import shlex
from collections.abc import AsyncIterator

from models import FS_AGENT_BACKEND_ALFRED, FS_AGENT_BACKEND_AUTO, FsAgentBackend
from scripts.common import (
    build_alfred_run_command,
    build_arg_parser,
    ensure_session,
    print_event,
    relay_subprocess,
    select_fs_agent_backend,
    stream_llm_prompt,
)


async def stream_filesystem_agent(
    prompt: str,
    *,
    cwd: str | None = None,
    session_id: str | None = None,
    backend: FsAgentBackend = FS_AGENT_BACKEND_AUTO,
) -> AsyncIterator[dict[str, object]]:
    selected_backend, _ = select_fs_agent_backend(backend)
    meta_extra = {"mode": "fs-agent", "backend": selected_backend, "cwd": cwd}

    if selected_backend == FS_AGENT_BACKEND_ALFRED:
        session_id, session_dir = ensure_session(session_id)
        command = build_alfred_run_command(prompt, cwd=cwd)
        request_payload = {
            "type": "fs-agent",
            "prompt": prompt,
            "cwd": cwd,
            "session_id": session_id,
            "backend": selected_backend,
            "command": shlex.join(command),
        }

        async for payload in relay_subprocess(
            command,
            session_dir=session_dir,
            request_payload=request_payload,
            cwd=cwd,
            meta_extra=meta_extra,
        ):
            payload.setdefault("session_id", session_id)
            yield payload
        return

    request_payload = {
        "type": "fs-agent",
        "prompt": prompt,
        "cwd": cwd,
        "backend": selected_backend,
    }

    async for payload in stream_llm_prompt(
        prompt,
        session_id=session_id,
        request_payload=request_payload,
        mode="fs-agent",
        meta_extra=meta_extra,
    ):
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
