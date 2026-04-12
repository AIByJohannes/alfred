from __future__ import annotations

import argparse
import asyncio
import base64
import binascii
import io
import json
import os
import shlex
import sys
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from llm import LLMEngine
from models import (
    FS_AGENT_BACKEND_ALFRED,
    FS_AGENT_BACKEND_AUTO,
    FS_AGENT_BACKEND_SMOL,
    FsAgentBackend,
)

DEFAULT_RUNTIME_ROOT = ".alfred-runtime"
DEFAULT_AGENT_MODE = "fs-agent"


def get_repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def get_runtime_root() -> Path:
    configured = os.getenv("ALFRED_RUNTIME_ROOT", DEFAULT_RUNTIME_ROOT)
    root = Path(configured)
    if not root.is_absolute():
        root = get_repo_root() / root
    root.mkdir(parents=True, exist_ok=True)
    return root


def get_sessions_root() -> Path:
    root = get_runtime_root() / "sessions"
    root.mkdir(parents=True, exist_ok=True)
    return root


def timestamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def ensure_session(session_id: str | None = None) -> tuple[str, Path]:
    session_id = session_id or f"{timestamp()}-{uuid4().hex[:8]}"
    session_dir = get_sessions_root() / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    (session_dir / "artifacts").mkdir(parents=True, exist_ok=True)
    return session_id, session_dir


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def append_jsonl(path: Path, payload: Any) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload) + "\n")


def get_messages_path(session_dir: Path) -> Path:
    return session_dir / "messages.ndjson"


def append_message(
    session_dir: Path,
    role: str,
    content: str,
    status: str | None = None,
    image_ref: str | None = None,
) -> None:
    msg: dict[str, Any] = {
        "role": role,
        "content": content,
    }
    if status:
        msg["status"] = status
    if image_ref:
        msg["image_ref"] = image_ref
    append_jsonl(get_messages_path(session_dir), msg)


def event(event_type: str, **payload: Any) -> dict[str, Any]:
    return {"type": event_type, **payload}


def format_sse_event(payload: dict[str, Any]) -> str:
    event_type = str(payload.get("type", "message"))
    body = json.dumps(payload, ensure_ascii=True)
    return f"event: {event_type}\ndata: {body}\n\n"


def print_event(payload: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(payload) + "\n")
    sys.stdout.flush()


def resolve_alfred_binary() -> Path | None:
    candidates: list[Path] = []
    if configured := os.getenv("ALFRED_CLI_BIN"):
        candidates.append(Path(configured))

    cli_root = (get_repo_root().parent / "alfred-cli").resolve()
    candidates.extend(
        [
            cli_root / "target" / "release" / "alfred",
            cli_root / "target" / "debug" / "alfred",
        ]
    )

    for candidate in candidates:
        if candidate.exists() and os.access(candidate, os.X_OK):
            return candidate

    path_binary = shutil_which("alfred")
    return Path(path_binary) if path_binary else None


def shutil_which(binary: str) -> str | None:
    for path in os.getenv("PATH", "").split(os.pathsep):
        candidate = Path(path) / binary
        if candidate.exists() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def build_alfred_run_command(prompt: str, cwd: str | None = None) -> list[str]:
    binary = resolve_alfred_binary()
    if binary is None:
        raise FileNotFoundError(
            "No scriptable `alfred` binary found. Set ALFRED_CLI_BIN or build ../alfred-cli."
        )

    command = [
        str(binary),
        "run",
        "--jsonl",
        "--mode",
        os.getenv("ALFRED_AGENT_MODE", DEFAULT_AGENT_MODE),
        "--prompt",
        prompt,
    ]
    if cwd:
        command.extend(["--cwd", cwd])
    return command


def select_fs_agent_backend(requested: FsAgentBackend) -> tuple[str, Path | None]:
    binary = resolve_alfred_binary()
    if requested in (FS_AGENT_BACKEND_AUTO, FS_AGENT_BACKEND_ALFRED):
        if binary:
            return FS_AGENT_BACKEND_ALFRED, binary
        if requested == FS_AGENT_BACKEND_ALFRED:
            # maintain the same error text to keep the CLI contract consistent
            raise FileNotFoundError(
                "No scriptable `alfred` binary found. Set ALFRED_CLI_BIN or build ../alfred-cli."
            )
    return FS_AGENT_BACKEND_SMOL, None


async def relay_subprocess(
    command: list[str],
    *,
    session_dir: Path,
    request_payload: dict[str, Any],
    cwd: str | None = None,
    meta_extra: dict[str, Any] | None = None,
) -> AsyncIterator[dict[str, Any]]:
    request_path = session_dir / "request.json"
    events_path = session_dir / "events.ndjson"
    result_path = session_dir / "result.json"
    write_json(request_path, request_payload)

    prompt = request_payload.get("prompt", "")
    if prompt:
        append_message(session_dir, "user", prompt)

    meta_payload = event(
        "meta",
        session_id=session_dir.name,
        command=shlex.join(command),
        cwd=cwd or str(get_repo_root()),
        **(meta_extra or {}),
    )
    yield meta_payload

    process = await asyncio.create_subprocess_exec(
        *command,
        cwd=cwd or str(get_repo_root()),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    assert process.stdout is not None
    assert process.stderr is not None

    stderr_lines: list[str] = []

    async def collect_stderr() -> None:
        async for raw_line in process.stderr:
            line = raw_line.decode("utf-8").strip()
            if line:
                stderr_lines.append(line)

    stderr_task = asyncio.create_task(collect_stderr())

    async for raw_line in process.stdout:
        line = raw_line.decode("utf-8").strip()
        if not line:
            continue

        payload = parse_cli_event(line)
        append_jsonl(events_path, payload)

        if payload["type"] == "artifact" and payload.get("path"):
            artifact_path = session_dir / "artifacts" / "manifest.json"
            existing = []
            if artifact_path.exists():
                existing = json.loads(artifact_path.read_text(encoding="utf-8"))
            existing.append(payload)
            write_json(artifact_path, existing)

        if payload["type"] == "done":
            write_json(result_path, payload)

        yield payload

    return_code = await process.wait()
    await stderr_task
    stderr = "\n".join(stderr_lines).strip()

    if return_code != 0:
        error_payload = event(
            "error",
            session_id=session_dir.name,
            message=stderr or f"`alfred run` exited with status {return_code}",
            exit_code=return_code,
        )
        append_jsonl(events_path, error_payload)
        yield error_payload
        if prompt:
            append_message(
                session_dir, "assistant", stderr or f"Exit code {return_code}", status="error"
            )
        return

    if stderr:
        note_payload = event("error", session_id=session_dir.name, message=stderr)
        append_jsonl(events_path, note_payload)
        yield note_payload
        if prompt:
            append_message(session_dir, "assistant", stderr, status="error")

    if not result_path.exists():
        payload = event("done", session_id=session_dir.name, result="completed")
        write_json(result_path, payload)
        append_jsonl(events_path, payload)
        yield payload
        if prompt:
            append_message(session_dir, "assistant", "Task completed", status="done")


def parse_cli_event(line: str) -> dict[str, Any]:
    try:
        payload = json.loads(line)
    except json.JSONDecodeError:
        return event("delta", content=line)

    if "type" not in payload:
        payload["type"] = "delta"
    return payload


def build_arg_parser(
    name: str, description: str, include_cwd: bool = False
) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=name, description=description)
    parser.add_argument("prompt", help="Task or prompt text")
    parser.add_argument("--session-id", dest="session_id")
    if include_cwd:
        parser.add_argument("--cwd", dest="cwd")
    return parser


async def stream_llm_prompt(
    prompt: str,
    *,
    session_id: str | None = None,
    request_payload: dict[str, Any] | None = None,
    mode: str = "chat",
    meta_extra: dict[str, Any] | None = None,
    image_base64: str | None = None,
) -> AsyncIterator[dict[str, Any]]:
    from PIL import Image

    session_id, session_dir = ensure_session(session_id)
    events_path = session_dir / "events.ndjson"
    payload = dict(request_payload or {})
    payload.setdefault("type", mode)
    payload["prompt"] = prompt
    payload["session_id"] = session_id
    if image_base64:
        payload["image"] = True
    write_json(session_dir / "request.json", payload)

    meta_payload = event("meta", session_id=session_id, mode=mode, **(meta_extra or {}))
    append_jsonl(events_path, meta_payload)
    yield meta_payload

    image_path: Path | None = None
    image_ref: str | None = None
    if image_base64:
        try:
            image_data = base64.b64decode(image_base64, validate=True)
            image = Image.open(io.BytesIO(image_data))
            image.load()
            image_ref = f"upload-{uuid4().hex[:8]}.png"
            image_path = session_dir / image_ref
            image.save(image_path)
        except (ValueError, binascii.Error, OSError):
            error_payload = event(
                "error",
                session_id=session_id,
                message="Invalid image attachment.",
            )
            append_jsonl(events_path, error_payload)
            yield error_payload
            append_message(session_dir, "assistant", "", status="error", image_ref=None)
            return

    append_message(session_dir, "user", prompt, image_ref=image_ref)

    engine = LLMEngine()
    result = await asyncio.to_thread(engine.run, prompt, image_path=image_path)

    delta = event("delta", session_id=session_id, content=result)
    append_jsonl(events_path, delta)
    yield delta

    done = event("done", session_id=session_id, result=result)
    append_jsonl(events_path, done)
    write_json(session_dir / "result.json", done)
    yield done

    append_message(session_dir, "assistant", result, status="done")
