from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from llm import LLMEngine
from scripts.common import append_jsonl, build_arg_parser, ensure_session, event, print_event, write_json


async def stream_inference(prompt: str, *, session_id: str | None = None) -> AsyncIterator[dict[str, object]]:
    session_id, session_dir = ensure_session(session_id)
    events_path = session_dir / "events.ndjson"
    write_json(
        session_dir / "request.json",
        {"type": "infer", "prompt": prompt, "session_id": session_id},
    )

    meta = event("meta", session_id=session_id, mode="inference")
    append_jsonl(events_path, meta)
    yield meta

    engine = LLMEngine()
    result = await asyncio.to_thread(engine.run, prompt)

    delta = event("delta", session_id=session_id, content=result)
    append_jsonl(events_path, delta)
    yield delta

    done = event("done", session_id=session_id, result=result)
    append_jsonl(events_path, done)
    write_json(session_dir / "result.json", done)
    yield done


async def _main() -> None:
    parser = build_arg_parser("python -m scripts.infer", "Run Python-side inference.")
    args = parser.parse_args()

    async for payload in stream_inference(args.prompt, session_id=args.session_id):
        print_event(payload)


if __name__ == "__main__":
    asyncio.run(_main())
