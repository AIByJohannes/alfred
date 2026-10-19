import json
import os
import sys
from pathlib import Path

import pytest

from models import FS_AGENT_BACKEND_ALFRED
from scripts.common import (
    append_message,
    build_alfred_acp_command,
    build_alfred_run_command,
    ensure_session,
    format_sse_event,
    get_messages_path,
    parse_cli_event,
    relay_acp_subprocess,
    select_fs_agent_backend,
)


def test_ensure_session_creates_runtime_tree(tmp_path, monkeypatch):
    monkeypatch.setenv("ALFRED_RUNTIME_ROOT", str(tmp_path))

    session_id, session_dir = ensure_session()

    assert session_id
    assert session_dir == tmp_path / "sessions" / session_id
    assert (session_dir / "artifacts").is_dir()


def test_format_sse_event_uses_event_name():
    payload = {"type": "delta", "content": "hello"}

    formatted = format_sse_event(payload)

    assert formatted.startswith("event: delta")
    assert '"content": "hello"' in formatted


def test_parse_cli_event_falls_back_to_delta():
    payload = parse_cli_event("plain text line")

    assert payload == {"type": "delta", "content": "plain text line"}


def test_build_alfred_run_command_prefers_env_override(tmp_path, monkeypatch):
    binary = tmp_path / "alfred"
    binary.write_text("#!/bin/sh\n", encoding="utf-8")
    binary.chmod(0o755)
    monkeypatch.setenv("ALFRED_CLI_BIN", str(binary))

    command = build_alfred_run_command("ship it", cwd="/tmp/repo")

    assert command[:3] == [str(binary), "run", "--jsonl"]
    assert command[3:5] == ["--prompt", "ship it"]
    assert command[-2:] == ["--cwd", "/tmp/repo"]


def test_build_alfred_run_command_errors_when_missing(monkeypatch):
    monkeypatch.setattr("scripts.common.resolve_alfred_binary", lambda: None)

    with pytest.raises(FileNotFoundError):
        build_alfred_run_command("ship it")


def test_build_alfred_run_command_omits_cwd_when_none(tmp_path, monkeypatch):
    binary = tmp_path / "alfred"
    binary.write_text("#!/bin/sh\n", encoding="utf-8")
    binary.chmod(0o755)
    monkeypatch.setenv("ALFRED_CLI_BIN", str(binary))

    command = build_alfred_run_command("do it")

    assert command[:3] == [str(binary), "run", "--jsonl"]
    assert command[3:5] == ["--prompt", "do it"]
    assert "--cwd" not in command


def test_build_alfred_acp_command_uses_binary_and_cwd(tmp_path, monkeypatch):
    binary = tmp_path / "alfred"
    binary.write_text("#!/bin/sh\n", encoding="utf-8")
    binary.chmod(0o755)
    monkeypatch.setenv("ALFRED_CLI_BIN", str(binary))

    command = build_alfred_acp_command(cwd="/tmp/repo")

    assert command == [str(binary), "acp", "--cwd", "/tmp/repo"]


def test_build_alfred_acp_command_omits_cwd_when_none(tmp_path, monkeypatch):
    binary = tmp_path / "alfred"
    binary.write_text("#!/bin/sh\n", encoding="utf-8")
    binary.chmod(0o755)
    monkeypatch.setenv("ALFRED_CLI_BIN", str(binary))

    assert build_alfred_acp_command() == [str(binary), "acp"]


def test_build_alfred_run_command_includes_session_id(tmp_path, monkeypatch):
    binary = tmp_path / "alfred"
    binary.write_text("#!/bin/sh\n", encoding="utf-8")
    binary.chmod(0o755)
    monkeypatch.setenv("ALFRED_CLI_BIN", str(binary))

    command = build_alfred_run_command(
        "ship it",
        cwd="/tmp/repo",
        session_id="test-session-123",
    )

    assert command[:3] == [str(binary), "run", "--jsonl"]
    assert "--session-id" in command
    session_idx = command.index("--session-id")
    assert command[session_idx + 1] == "test-session-123"


def test_select_fs_agent_backend_auto_prefers_cli(monkeypatch):
    fake_binary = Path("/usr/bin/alfred")
    monkeypatch.setattr("scripts.common.resolve_alfred_binary", lambda: fake_binary)

    backend, resolved = select_fs_agent_backend("auto")

    assert backend == FS_AGENT_BACKEND_ALFRED
    assert resolved == fake_binary


def test_select_fs_agent_backend_auto_reports_missing_cli(monkeypatch):
    monkeypatch.setattr("scripts.common.resolve_alfred_binary", lambda: None)

    backend, resolved = select_fs_agent_backend("auto")

    assert backend == FS_AGENT_BACKEND_ALFRED
    assert resolved is None


def test_select_fs_agent_backend_explicit_alfred_reports_missing_cli(monkeypatch):
    monkeypatch.setattr("scripts.common.resolve_alfred_binary", lambda: None)

    backend, resolved = select_fs_agent_backend(FS_AGENT_BACKEND_ALFRED)

    assert backend == FS_AGENT_BACKEND_ALFRED
    assert resolved is None


@pytest.mark.asyncio
async def test_relay_acp_subprocess_streams_and_persists_protocol_events(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("ALFRED_RUNTIME_ROOT", str(tmp_path))
    session_id, session_dir = ensure_session("acp-test")
    fake_server = tmp_path / "fake_acp_server.py"
    fake_server.write_text(
        """
import json
import sys

active_session = None

for raw_line in sys.stdin:
    message = json.loads(raw_line)
    if message["type"] == "session.start":
        active_session = message["session_id"]
        print(json.dumps({
            "type": "meta",
            "session_id": active_session,
            "cwd": message["cwd"],
            "backend": "fake",
            "transport": "acp",
            "version": "1",
        }), flush=True)
    elif message["type"] == "prompt.send":
        print(json.dumps({
            "type": "delta",
            "content": f"echo: {message['prompt']}",
        }), flush=True)
        print(json.dumps({"type": "done", "result": "completed"}), flush=True)
    elif message["type"] == "session.close":
        break
""".lstrip(),
        encoding="utf-8",
    )

    request_payload = {
        "type": "fs-agent",
        "prompt": "test prompt",
        "cwd": str(tmp_path),
        "session_id": session_id,
        "backend": "alfred-cli",
        "transport": "acp",
    }

    events = []
    async for payload in relay_acp_subprocess(
        [sys.executable, str(fake_server)],
        session_dir=session_dir,
        request_payload=request_payload,
        cwd=str(tmp_path),
    ):
        events.append(payload)

    assert [payload["type"] for payload in events] == ["meta", "delta", "done"]
    assert events[0]["session_id"] == session_id
    assert events[1]["content"] == "echo: test prompt"
    assert json.loads((session_dir / "result.json").read_text()) == {
        "type": "done",
        "result": "completed",
        "session_id": session_id,
    }
    assert (session_dir / "request.json").exists()


def test_append_message_persists_to_file(tmp_path, monkeypatch):
    monkeypatch.setenv("ALFRED_RUNTIME_ROOT", str(tmp_path))
    session_id, session_dir = ensure_session()
    messages_path = get_messages_path(session_dir)

    assert not messages_path.exists()

    append_message(session_dir, "user", "Hello Alfred")
    assert messages_path.exists()

    with open(messages_path) as f:
        msgs = [json.loads(line) for line in f if line.strip()]

    assert len(msgs) == 1
    assert msgs[0]["role"] == "user"
    assert msgs[0]["content"] == "Hello Alfred"


@pytest.mark.asyncio
async def test_relay_acp_subprocess_forwards_images(tmp_path, monkeypatch):
    monkeypatch.setenv("ALFRED_RUNTIME_ROOT", str(tmp_path))
    session_id, session_dir = ensure_session("acp-images")
    fake_server = tmp_path / "fake_acp_images.py"
    fake_server.write_text(
        """
import json
import sys

for raw_line in sys.stdin:
    message = json.loads(raw_line)
    if message["type"] == "session.start":
        print(json.dumps({"type": "meta", "session_id": message["session_id"]}), flush=True)
    elif message["type"] == "prompt.send":
        print(json.dumps({
            "type": "delta",
            "content": f"images={len(message.get('images', []))}",
        }), flush=True)
        print(json.dumps({"type": "done", "result": "completed"}), flush=True)
    elif message["type"] == "session.close":
        break
""".lstrip(),
        encoding="utf-8",
    )

    request_payload = {
        "type": "fs-agent",
        "prompt": "describe",
        "session_id": session_id,
        "images": [{"media_type": "image/png", "data": "YWJj"}],
    }

    events = []
    async for payload in relay_acp_subprocess(
        [sys.executable, str(fake_server)],
        session_dir=session_dir,
        request_payload=request_payload,
        cwd=str(tmp_path),
    ):
        events.append(payload)

    assert any(
        payload.get("content") == "images=1" for payload in events if payload["type"] == "delta"
    )


@pytest.mark.asyncio
async def test_relay_acp_ignores_stderr_on_success_and_persists_reply(tmp_path, monkeypatch):
    monkeypatch.setenv("ALFRED_RUNTIME_ROOT", str(tmp_path))
    _, session_dir = ensure_session("acp-stderr")
    fake_server = tmp_path / "fake_acp_stderr.py"
    fake_server.write_text(
        """
import json
import sys

print("diagnostic noise", file=sys.stderr, flush=True)
for raw_line in sys.stdin:
    message = json.loads(raw_line)
    if message["type"] == "session.start":
        print(json.dumps({"type": "meta", "session_id": message["session_id"]}), flush=True)
    elif message["type"] == "prompt.send":
        print(json.dumps({"type": "delta", "content": "hello"}), flush=True)
        print(json.dumps({"type": "done", "result": "completed"}), flush=True)
    elif message["type"] == "session.close":
        break
""".lstrip(),
        encoding="utf-8",
    )

    events = [
        payload
        async for payload in relay_acp_subprocess(
            [sys.executable, str(fake_server)],
            session_dir=session_dir,
            request_payload={
                "type": "fs-agent",
                "prompt": "say hello",
                "session_id": "acp-stderr",
            },
            cwd=str(tmp_path),
        )
    ]

    assert not any(payload["type"] == "error" for payload in events)
    messages = [
        json.loads(line)
        for line in get_messages_path(session_dir).read_text().splitlines()
        if line.strip()
    ]
    assert messages[-1] == {
        "role": "assistant",
        "content": "hello",
        "status": "done",
    }


@pytest.mark.asyncio
async def test_relay_acp_subprocess_cleans_up_on_cancellation(tmp_path, monkeypatch):
    monkeypatch.setenv("ALFRED_RUNTIME_ROOT", str(tmp_path))
    _, session_dir = ensure_session("acp-cancel")
    fake_server = tmp_path / "fake_acp_cancel.py"
    pid_file = tmp_path / "server.pid"
    fake_server.write_text(
        f"""
import json
import os
import sys
import time

with open({str(pid_file)!r}, "w", encoding="utf-8") as handle:
    handle.write(str(os.getpid()))
    handle.flush()

print(json.dumps({{"type": "meta", "session_id": "acp-cancel"}}), flush=True)
time.sleep(30)
""".lstrip(),
        encoding="utf-8",
    )

    stream = relay_acp_subprocess(
        [sys.executable, str(fake_server)],
        session_dir=session_dir,
        request_payload={"type": "fs-agent", "prompt": "wait", "session_id": "acp-cancel"},
        cwd=str(tmp_path),
    )
    first = await anext(stream)
    assert first["type"] == "meta"
    await stream.aclose()

    pid = int(pid_file.read_text())
    with pytest.raises(ProcessLookupError):
        os.kill(pid, 0)
