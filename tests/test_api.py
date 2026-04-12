import json
import os
from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from main import app
from scripts.common import ensure_session, append_message, get_messages_path

client = TestClient(app)


@pytest.fixture
def test_session(tmp_path, monkeypatch):
    monkeypatch.setenv("ALFRED_RUNTIME_ROOT", str(tmp_path))
    session_id, session_dir = ensure_session()
    return session_id, session_dir


def test_health_reports_runtime(monkeypatch):
    monkeypatch.delenv("ALFRED_CLI_BIN", raising=False)

    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["runtime_root"].endswith(".alfred-runtime")
    assert body["prompt_source"] == "prompts/SOUL.md"
    assert body["smolagents_available"] is True
    assert body["fs_agent_backend_options"] == ["auto", "alfred-cli", "smolagents"]
    expected_default = "alfred-cli" if body["alfred_cli_available"] else "smolagents"
    assert body["fs_agent_default_backend"] == expected_default


def test_root_endpoint_includes_prompt_metadata():
    response = client.get("/")

    assert response.status_code == 200
    body = response.json()
    assert body["prompt_source"] == "prompts/SOUL.md"
    assert body["message"] == "Alfred local workbench is running"


def test_transcribe_without_file():
    response = client.post("/api/transcribe")

    assert response.status_code == 422


def test_transcribe_with_unsupported_file():
    data = {"file": ("test.txt", b"fake", "text/plain")}
    response = client.post("/api/transcribe", files=data)

    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


def test_transcribe_with_empty_file(tmp_path, monkeypatch):
    monkeypatch.setenv("ALFRED_RUNTIME_ROOT", str(tmp_path))
    data = {"file": ("test.wav", b"", "audio/wav")}
    response = client.post("/api/transcribe", files=data)

    assert response.status_code == 400
    assert "Empty audio file" in response.json()["detail"]


def test_transcription_health_endpoint():
    response = client.get("/api/transcription/health")

    assert response.status_code == 200
    body = response.json()
    assert "available" in body
    assert "backend" in body
    assert "cuda_available" in body


def test_append_message_persists_to_file(test_session):
    session_id, session_dir = test_session
    messages_path = get_messages_path(session_dir)

    assert not messages_path.exists()

    append_message(session_dir, "user", "Hello Alfred")
    assert messages_path.exists()

    with open(messages_path) as f:
        msgs = [json.loads(line) for line in f if line.strip()]

    assert len(msgs) == 1
    assert msgs[0]["role"] == "user"
    assert msgs[0]["content"] == "Hello Alfred"


def test_session_detail_returns_messages(test_session):
    session_id, session_dir = test_session

    append_message(session_dir, "user", "Test prompt")
    append_message(session_dir, "assistant", "Test response", status="done")

    response = client.get(f"/api/sessions/{session_id}")
    assert response.status_code == 200
    body = response.json()

    assert "messages" in body
    assert len(body["messages"]) == 2
    assert body["messages"][0]["role"] == "user"
    assert body["messages"][1]["role"] == "assistant"
    assert body["messages"][1]["content"] == "Test response"


def test_session_detail_returns_events_for_legacy_sessions(test_session):
    session_id, session_dir = test_session

    events_path = session_dir / "events.ndjson"
    events_path.write_text(
        '{"type": "delta", "content": "legacy response"}\n{"type": "done"}\n', encoding="utf-8"
    )

    response = client.get(f"/api/sessions/{session_id}")
    assert response.status_code == 200
    body = response.json()

    assert "messages" in body
    assert body["messages"] is None
    assert len(body["events"]) == 2


def test_session_image_endpoint_returns_image(test_session, monkeypatch):
    session_id, session_dir = test_session
    image_path = session_dir / "test-image.png"
    image_path.write_bytes(b"fake png data")

    response = client.get(f"/api/sessions/{session_id}/image/test-image.png")
    assert response.status_code == 200
    body = response.json()
    assert body["image"] == "ZmFrZSBwbmcgZGF0YQ=="
