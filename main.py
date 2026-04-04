from __future__ import annotations

import json
from collections.abc import AsyncIterator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from models import (
    FS_AGENT_BACKEND_ALFRED,
    FS_AGENT_BACKEND_SMOL,
    FilesystemAgentRequest,
    HealthResponse,
    StreamRequest,
    SessionMeta,
    SessionDetail,
)
from prompts import SYSTEM_PROMPT
from scripts.common import (
    format_sse_event,
    get_runtime_root,
    get_sessions_root,
    resolve_alfred_binary,
)
from scripts.fs_agent import stream_filesystem_agent
from scripts.infer import stream_inference

app = FastAPI(
    title="Alfred Local Workbench API",
    description="Thin local bridge between the Vite workbench and Python/Rust runners.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _sse_stream(events: AsyncIterator[dict[str, object]]) -> StreamingResponse:
    async def iterator() -> AsyncIterator[bytes]:
        async for event in events:
            yield format_sse_event(event).encode("utf-8")

    return StreamingResponse(
        iterator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    binary = resolve_alfred_binary()
    return HealthResponse(
        runtime_root=str(get_runtime_root()),
        prompt_source="prompts/SOUL.md",
        alfred_cli_available=binary is not None,
        alfred_cli_path=str(binary) if binary else None,
        smolagents_available=True,
        fs_agent_default_backend=FS_AGENT_BACKEND_ALFRED if binary else FS_AGENT_BACKEND_SMOL,
    )


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "message": "Alfred local workbench is running",
        "prompt_source": "prompts/SOUL.md",
        "system_prompt_preview": SYSTEM_PROMPT.splitlines()[0],
    }


@app.post("/api/infer/stream")
async def infer_stream(request: StreamRequest) -> StreamingResponse:
    return _sse_stream(stream_inference(request.prompt, session_id=request.session_id))


@app.post("/api/fs-agent/stream")
async def filesystem_agent_stream(
    request: FilesystemAgentRequest,
) -> StreamingResponse:
    return _sse_stream(
        stream_filesystem_agent(
            request.prompt,
            cwd=request.cwd,
            session_id=request.session_id,
            backend=request.backend,
        )
    )


@app.get("/api/sessions", response_model=list[SessionMeta])
async def list_sessions() -> list[SessionMeta]:
    sessions_root = get_sessions_root()
    sessions = []
    if not sessions_root.exists():
        return sessions
    
    for session_dir in sorted(sessions_root.iterdir(), key=lambda d: d.name, reverse=True):
        if not session_dir.is_dir():
            continue
        req_file = session_dir / "request.json"
        if req_file.exists():
            try:
                with open(req_file) as f:
                    req_data = json.load(f)
                sessions.append(SessionMeta(
                    id=session_dir.name,
                    prompt=req_data.get("prompt", ""),
                    mode=req_data.get("mode", "unknown"),
                    timestamp=session_dir.name.split("-")[0]
                ))
            except Exception:
                pass
    return sessions


@app.get("/api/sessions/{session_id}", response_model=SessionDetail)
async def get_session(session_id: str) -> SessionDetail:
    sessions_root = get_sessions_root()
    session_dir = sessions_root / session_id
    if not session_dir.exists():
        raise HTTPException(status_code=404, detail="Session not found")
        
    req_file = session_dir / "request.json"
    events_file = session_dir / "events.ndjson"
    
    meta_dict = {}
    if req_file.exists():
        with open(req_file) as f:
            meta_dict = json.load(f)
            
    events = []
    if events_file.exists():
        with open(events_file) as f:
            for line in f:
                if line.strip():
                    events.append(json.loads(line))
                    
    meta = SessionMeta(
        id=session_dir.name,
        prompt=meta_dict.get("prompt", ""),
        mode=meta_dict.get("mode", "unknown"),
        timestamp=session_dir.name.split("-")[0]
    )
    return SessionDetail(meta=meta, events=events)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
