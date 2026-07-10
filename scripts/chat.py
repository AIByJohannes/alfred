from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from scripts.common import build_arg_parser, print_event
from scripts.fs_agent import stream_filesystem_agent


async def stream_chat(
    prompt: str,
    *,
    session_id: str | None = None,
    image_base64: str | None = None,
) -> AsyncIterator[dict[str, object]]:
    if image_base64:
        prompt = f"{prompt}\n\n[An image attachment is present in the workbench UI.]"
    async for payload in stream_filesystem_agent(prompt, session_id=session_id):
        yield payload


async def _main() -> None:
    parser = build_arg_parser("python -m scripts.chat", "Run Python-side chat.")
    args = parser.parse_args()

    async for payload in stream_chat(args.prompt, session_id=args.session_id):
        print_event(payload)


if __name__ == "__main__":
    asyncio.run(_main())
