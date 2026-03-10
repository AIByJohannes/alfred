import pytest

from scripts.common import (
    build_alfred_run_command,
    ensure_session,
    format_sse_event,
    parse_cli_event,
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
