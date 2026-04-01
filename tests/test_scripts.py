import pytest
from pathlib import Path

from models import FS_AGENT_BACKEND_ALFRED, FS_AGENT_BACKEND_SMOL
from scripts.common import (
    build_alfred_run_command,
    ensure_session,
    format_sse_event,
    parse_cli_event,
    select_fs_agent_backend,
    stream_llm_prompt,
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

    assert command[:2] == [str(binary), "run"]
    assert command[-2:] == ["--cwd", "/tmp/repo"]


def test_build_alfred_run_command_errors_when_missing(monkeypatch):
    monkeypatch.setattr("scripts.common.resolve_alfred_binary", lambda: None)

    with pytest.raises(FileNotFoundError):
        build_alfred_run_command("ship it")


def test_select_fs_agent_backend_auto_prefers_cli(monkeypatch):
    fake_binary = Path("/usr/bin/alfred")
    monkeypatch.setattr("scripts.common.resolve_alfred_binary", lambda: fake_binary)

    backend, resolved = select_fs_agent_backend("auto")

    assert backend == FS_AGENT_BACKEND_ALFRED
    assert resolved == fake_binary


def test_select_fs_agent_backend_auto_falls_back_when_missing(monkeypatch):
    monkeypatch.setattr("scripts.common.resolve_alfred_binary", lambda: None)

    backend, resolved = select_fs_agent_backend("auto")

    assert backend == FS_AGENT_BACKEND_SMOL
    assert resolved is None


def test_select_fs_agent_backend_requires_cli(monkeypatch):
    monkeypatch.setattr("scripts.common.resolve_alfred_binary", lambda: None)

    with pytest.raises(FileNotFoundError):
        select_fs_agent_backend(FS_AGENT_BACKEND_ALFRED)


@pytest.mark.asyncio
async def test_stream_llm_prompt_records_events(monkeypatch, tmp_path):
    monkeypatch.setenv("ALFRED_RUNTIME_ROOT", str(tmp_path))

    class DummyEngine:
        def run(self, prompt: str) -> str:
            assert prompt == "test prompt"
            return "response"

    monkeypatch.setattr("scripts.common.LLMEngine", DummyEngine)

    events = []
    async for payload in stream_llm_prompt(
        "test prompt",
        request_payload={"type": "fs-agent", "backend": "smolagents"},
        mode="fs-agent",
        meta_extra={"backend": "smolagents"},
    ):
        events.append(payload)

    assert events[0]["type"] == "meta"
    assert events[0]["backend"] == "smolagents"
    assert events[1]["type"] == "delta"
    assert events[1]["content"] == "response"
    assert events[2]["type"] == "done"
    session_id = events[0]["session_id"]
    assert (tmp_path / "sessions" / session_id / "request.json").exists()
