from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from scripts.common import build_arg_parser, print_event, stream_llm_prompt


async def stream_chat(
    prompt: str,
    *,
    session_id: str | None = None,
    image_base64: str | None = None,
) -> AsyncIterator[dict[str, object]]:
    request_payload = {"type": "chat", "image": bool(image_base64)}
    async for payload in stream_llm_prompt(
        prompt,
        session_id=session_id,
        request_payload=request_payload,
        mode="chat",
        image_base64=image_base64,
    ):
        yield payload


async def _main() -> None:
    parser = build_arg_parser("python -m scripts.chat", "Run Python-side chat.")
    args = parser.parse_args()

    async for payload in stream_chat(args.prompt, session_id=args.session_id):
        print_event(payload)


if __name__ == "__main__":
    asyncio.run(_main())
