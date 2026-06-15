from __future__ import annotations

import shlex
from collections.abc import AsyncIterator

from models import (
    FS_AGENT_BACKEND_ALFRED,
    FS_AGENT_BACKEND_AUTO,
    FS_AGENT_BACKEND_SMOL,
    FsAgentBackend,
)
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
    selected_backend, binary = select_fs_agent_backend(backend)
    meta_extra = {"backend": selected_backend}

    # Native (alfred-cli) attempt: only when selection returned a usable binary.
    # The single agent path must never hard-fail due to a missing native binary.
    # Validate/build the command *before* allocating a session dir, so a missing
    # binary does not leave partial sessions and does not surface the
    # "No scriptable `alfred` binary found" error to agent users.
    # cwd is optional in both native and fallback paths.
    if selected_backend == FS_AGENT_BACKEND_ALFRED and binary is not None:
        try:
            command = build_alfred_run_command(prompt, cwd=cwd, binary_override=binary)
            # Only allocate the native session after we know we can run the command.
            session_id, session_dir = ensure_session(session_id)
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
        except Exception as e:
            # Any problem with the native path (binary vanished after selection,
            # not executable, launch failure inside relay, etc.) -> fall back.
            # Never let "No scriptable alfred binary" or similar bubble out of
            # the high-level agent API. Record the actual runtime backend + reason.
            selected_backend = FS_AGENT_BACKEND_SMOL
            meta_extra = {"backend": selected_backend, "fallback_reason": str(e)[:300]}

    # Python-side agent (smolagents) path.
    # Used for:
    # - no native binary present (AUTO or explicit alfred-cli degrade here)
    # - explicit smolagents backend requested
    # - native attempt failed for any reason above
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
