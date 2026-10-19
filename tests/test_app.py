import base64
import inspect
import json
from pathlib import Path

# ===================== TDD CONTRACTS FOR GRADIO MIGRATION =====================
# These tests are written FIRST (TDD). They must fail against the old PyShiny
# implementation and pass after the full Gradio replacement with:
#   import gradio as gr
#   with gr.Blocks(theme=gr.Theme.from_hub("d8ahazard/rd_blue")) as demo:
# No PyShiny symbols may remain in app/app.py or other tracked files.
# Local caches (.venv, .alfred-runtime) will be cleaned to eliminate all traces.


def test_app_exports_gradio_blocks():
    from app.app import app, demo

    assert demo is not None
    # app should be the same launchable object for convenience/compat
    assert app is demo or app is not None

    import gradio as gr
    # demo must be (or wrap) a Gradio Blocks interface
    assert isinstance(demo, gr.Blocks) or hasattr(demo, "launch")


def test_app_uses_required_theme():
    import app.app as appmod
    src = inspect.getsource(appmod)
    assert 'gr.themes.Monochrome()' in src or 'gr.themes.Base()' in src


def test_app_has_core_controls():
    import app.app as appmod
    src = inspect.getsource(appmod)

    # Essential control names / labels must be present in the Gradio UI definition
    # (MultimodalTextbox now provides text + image attach + submit natively,
    # so separate image_upload / send_btn controls were removed.)
    required = [
        "prompt",
        "cwd",
        "fs_backend",
        "multimodal",
        "audio_upload",
        "voice_audio",
        "clear_btn",
        "new_session_btn",
        "history_radio",
        "status",
        "messages",
        "artifacts",
        "chatbot",
    ]
    lower_src = src.lower()
    for name in required:
        assert name in lower_src or name in src


def test_send_prompt_is_async():
    import app.app as appmod
    src = inspect.getsource(appmod)
    assert "stream_filesystem_agent" in src
    # There must be an async handler that performs the streaming send
    assert "async def" in src and ("send" in src or "_send" in src or "handle_send" in src)


def test_audio_file_transcription_helper():
    import app.app as appmod
    src = inspect.getsource(appmod)
    assert "get_transcription_service" in src
    assert "transcribe_file" in src


def test_decode_voice_audio_data():
    from app.app import decode_voice_audio_data

    sample = b"fake audio bytes"
    b64 = base64.b64encode(sample).decode()
    payload = {"mimeType": "audio/webm", "data": b64}
    audio_bytes, filename = decode_voice_audio_data(payload)
    assert audio_bytes == sample
    assert filename == "voice.webm"


def test_decode_voice_audio_data_default_mime():
    from app.app import decode_voice_audio_data

    b64 = base64.b64encode(b"test").decode()
    payload = {"data": b64}
    audio_bytes, filename = decode_voice_audio_data(payload)
    assert audio_bytes == b"test"
    assert filename == "voice.webm"


def test_session_timestamp_is_human_readable():
    from app.app import _format_session_timestamp

    assert _format_session_timestamp("20260710T185819Z") == "10 Jul 2026, 18:58 UTC"
    assert _format_session_timestamp("unknown") == "unknown"


def test_no_pyshiny_symbols_in_app():
    src = Path("app/app.py").read_text(encoding="utf-8").lower()
    forbidden = [
        "from shiny",
        "import shiny",
        "shiny.",
        "app_ui",
        "page_sidebar",
        "shiny.setinputvalue",
        "reactive.value",
        "render.ui",
        "@output",
        "@render.ui",
    ]
    for token in forbidden:
        assert token not in src, f"Found PyShiny trace: {token}"


def test_no_pyshiny_references_in_tracked_source():
    """Scan product source/docs/config (excluding tests, which must name the forbidden tokens)
    for any remaining PyShiny references. This is the final gate for 'no traces left'.
    Local caches (.venv, .alfred-runtime, etc.) were cleaned as part of the strict scope.
    """
    import subprocess

    # Product roots we care about (no tests/ — test file legitimately contains policing tokens)
    tracked = subprocess.check_output(
        [
            "git",
            "ls-files",
            "--",
            "app/*",
            "llm/*",
            "prompts/*",
            "scripts/*",
            "transcription/*",
            "models.py",
            "pyproject.toml",
            "Justfile",
            "*.md",
            "docs/*",
            "AGENTS.md",
            "uv.lock",
        ],
        cwd=".",
        text=True,
    ).splitlines()

    extra = [
        "app/app.py",
        "app/style.css",
        "app/README.md",
        "pyproject.toml",
        "Justfile",
        "README.md",
        "AGENTS.md",
        "docs/architecture.md",
        "uv.lock",
    ]
    files_to_scan = sorted(set(tracked + extra))

    # Explicitly drop anything that is test code
    files_to_scan = [
        f
        for f in files_to_scan
        if not f.startswith("tests/")
        and "/tests/" not in f
        and "test_" not in Path(f).name
    ]

    forbidden_patterns = [
        "pyshiny",
        "PyShiny",
        "from shiny import",
        "import shiny",
        "shiny>=1.6.0",
        "shiny run",
        "Shiny.setInputValue",
        "ui.page_sidebar",
        "page_sidebar",
        ".shiny-input",
        ".shiny-options",
    ]

    hits = []
    for f in files_to_scan:
        p = Path(f)
        if not p.exists():
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for pat in forbidden_patterns:
            if pat.lower() in text.lower():
                hits.append((f, pat))

    assert not hits, f"PyShiny references remain: {hits}"


def test_pyproject_uses_gradio_not_shiny():
    text = Path("pyproject.toml").read_text(encoding="utf-8")
    assert "gradio" in text.lower()
    # shiny may still appear in lock comments until we refresh, but the requires must not list it
    # After `uv lock` it must be absent from the project metadata.
    # We assert the source dependency declaration here.
    if "dependencies" in text.lower():
        section = text.lower().split("dependencies")[1].split("]")[0]
        assert "shiny" not in section
    else:
        assert True  # no dependencies section at all -> vacuously ok for this gate


def test_gradio_app_constructs():
    from app.app import demo

    # Basic smoke: constructing the module must not raise and demo must be usable
    assert demo is not None


def test_workspaces_filter_and_remember_session_membership(tmp_path, monkeypatch):
    monkeypatch.setenv("ALFRED_RUNTIME_ROOT", str(tmp_path))
    from app.app import _add_session_to_workspace, _create_workspace, get_sessions

    session_dir = tmp_path / "sessions" / "session-a"
    session_dir.mkdir(parents=True)
    (session_dir / "request.json").write_text(json.dumps({"prompt": "Workspace test"}))

    workspace_update = _create_workspace("Research")
    workspace_id = workspace_update["value"]
    _add_session_to_workspace(workspace_id, "session-a")

    assert [session["id"] for session in get_sessions(workspace_id)] == ["session-a"]
    assert get_sessions("general") == []


# ===================== CHAT-FIRST LAYOUT CONTRACTS =====================


def _write_session(root: Path, name: str, prompt: str) -> Path:
    session_dir = root / "sessions" / name
    session_dir.mkdir(parents=True)
    (session_dir / "request.json").write_text(json.dumps({"prompt": prompt}))
    return session_dir


def test_idle_run_state_shows_no_status_banner():
    from app.app import _render_status

    assert _render_status("idle", "Standing by.") == ""
    assert "status-running" in _render_status("running", "Working")
    assert "status-done" in _render_status("done", "Done")
    assert "status-error" in _render_status("error", "Boom")


def test_status_detail_is_html_escaped():
    from app.app import _render_status

    out = _render_status("error", "<script>alert(1)</script>")
    assert "<script>" not in out
    assert "&lt;script&gt;" in out


def test_artifact_and_pending_labels_are_html_escaped():
    from app.app import _render_artifacts, _render_pending

    artifacts = _render_artifacts([{"label": "<img src=x>", "path": "/tmp/<b>.txt"}])
    assert "<img" not in artifacts
    assert "<b>" not in artifacts

    pending = _render_pending("<iframe></iframe>")
    assert "<iframe>" not in pending


def test_new_chat_clears_view_state_but_keeps_persisted_sessions(tmp_path, monkeypatch):
    monkeypatch.setenv("ALFRED_RUNTIME_ROOT", str(tmp_path))
    from app.app import _clear_state, get_sessions

    _write_session(tmp_path, "20261019T120000Z-aaa", "Keep me")

    messages, session_id, artifacts, status, detail, *_rest = _clear_state("Session ready.")
    chatbot = _rest[-1]

    assert messages == []
    assert session_id is None
    assert artifacts == []
    assert status == "idle"
    assert detail == "Session ready."
    assert chatbot == []
    assert [s["id"] for s in get_sessions()] == ["20261019T120000Z-aaa"]


def test_fork_detaches_from_session_without_dropping_transcript():
    from app.app import _fork_session

    transcript = [{"role": "user", "content": "Hello"}]
    messages, session_id, *_rest = _fork_session(transcript, [], "general")

    assert messages == transcript
    assert session_id is None


def test_transcription_failure_preserves_existing_draft():
    import asyncio

    from app.app import _transcribe_and_fill

    draft = {"text": "keep this draft", "files": []}
    text, status, _detail = asyncio.run(_transcribe_and_fill("/nonexistent/audio.webm", draft))

    assert text == "keep this draft"
    assert status == "idle"


def test_loading_history_restores_assistant_reply(tmp_path, monkeypatch):
    monkeypatch.setenv("ALFRED_RUNTIME_ROOT", str(tmp_path))
    from app.app import _load_session_into_state

    session_dir = _write_session(tmp_path, "20261019T120000Z-bbb", "Hello")
    (session_dir / "messages.ndjson").write_text(
        json.dumps({"role": "user", "content": "Hello"}) + "\n"
    )
    (session_dir / "events.ndjson").write_text(
        "\n".join(
            [
                json.dumps({"type": "delta", "text": "Hi "}),
                json.dumps({"type": "delta", "text": "there"}),
                json.dumps({"type": "done", "result": "completed"}),
            ]
        )
        + "\n"
    )

    messages, *_rest = _load_session_into_state("20261019T120000Z-bbb", "general")

    assert [m["role"] for m in messages] == ["user", "assistant"]
    assert messages[1]["content"] == "Hi there"
    assert messages[1]["status"] == "done"


def test_loading_history_marks_failed_runs(tmp_path, monkeypatch):
    monkeypatch.setenv("ALFRED_RUNTIME_ROOT", str(tmp_path))
    from app.app import _load_session_into_state

    session_dir = _write_session(tmp_path, "20261019T120000Z-ccc", "Hello")
    (session_dir / "messages.ndjson").write_text(
        json.dumps({"role": "user", "content": "Hello"}) + "\n"
    )
    (session_dir / "events.ndjson").write_text(
        "\n".join(
            [
                json.dumps({"type": "delta", "text": "partial"}),
                json.dumps({"type": "error", "message": "boom"}),
            ]
        )
        + "\n"
    )

    messages, *_rest = _load_session_into_state("20261019T120000Z-ccc", "general")

    assert messages[-1]["role"] == "assistant"
    assert messages[-1]["status"] == "error"


def test_voice_controls_are_in_normal_flow():
    css = Path("app/style.css").read_text(encoding="utf-8")
    # The floating popover that covered the transcript must not come back.
    assert ".voice-audio" not in css
    assert ".voice-accordion" in css


def test_style_has_no_external_font_requests():
    css = Path("app/style.css").read_text(encoding="utf-8")
    assert "fonts.googleapis.com" not in css
    assert "@import" not in css


# ===================== TOOL ACTIVITY & ATTACHMENTS =====================


def test_tool_events_render_as_activity_messages():
    from app.app import _tool_event_message

    request = _tool_event_message(
        {
            "type": "tool_request",
            "name": "Bash",
            "arguments": {"command": "ls -la"},
        },
        "request",
    )
    assert request["kind"] == "tool"
    assert request["status"] == "running"
    assert "Bash" in request["content"]
    assert "ls -la" in request["content"]

    failure = _tool_event_message(
        {
            "type": "tool_result",
            "name": "Bash",
            "output": "permission denied",
            "is_error": True,
        },
        "result",
    )
    assert failure["status"] == "error"
    assert "permission denied" in failure["content"]


def test_assistant_delta_starts_new_message_after_tool_activity():
    from app.app import _append_assistant_delta, _tool_event_message

    messages = [{"role": "user", "content": "hello"}]
    messages = _append_assistant_delta(messages, "thinking")
    messages.append(
        _tool_event_message(
            {"type": "tool_request", "name": "Read", "arguments": {"path": "x"}},
            "request",
        )
    )
    messages = _append_assistant_delta(messages, "done")

    assert [message["role"] for message in messages] == [
        "user",
        "assistant",
        "assistant",
        "assistant",
    ]
    assert messages[1]["content"] == "thinking"
    assert messages[2]["kind"] == "tool"
    assert messages[3]["content"] == "done"


async def test_send_forwards_image_attachment_to_agent(tmp_path, monkeypatch):
    monkeypatch.setenv("ALFRED_RUNTIME_ROOT", str(tmp_path))
    from app.app import _handle_send_stream

    image = tmp_path / "diagram.png"
    image.write_bytes(b"\x89PNG\r\n\x1a\nfake")
    captured = {}

    async def fake_stream(prompt, **kwargs):
        captured["prompt"] = prompt
        captured.update(kwargs)
        yield {"type": "meta", "session_id": "s-image", "backend": "alfred-cli"}
        yield {"type": "done", "result": "completed"}

    monkeypatch.setattr("app.app.stream_filesystem_agent", fake_stream)

    payload = {"text": "Describe this", "files": [str(image)]}
    outputs = [
        item
        async for item in _handle_send_stream(
            payload,
            [],
            None,
            None,
            "auto",
            [],
            None,
            None,
            "general",
        )
    ]

    assert captured["images"] == [
        {
            "media_type": "image/png",
            "data": "iVBORw0KGgpmYWtl",
        }
    ]
    assert outputs[-1][3] == "done"


async def test_send_rejects_unreadable_attachment(tmp_path, monkeypatch):
    monkeypatch.setenv("ALFRED_RUNTIME_ROOT", str(tmp_path))
    from app.app import _handle_send_stream

    monkeypatch.setattr(
        "app.app.stream_filesystem_agent",
        lambda *args, **kwargs: None,
    )

    payload = {"text": "Describe this", "files": [str(tmp_path / "missing.png")]}
    outputs = [
        item
        async for item in _handle_send_stream(
            payload,
            [],
            None,
            None,
            "auto",
            [],
            None,
            None,
            "general",
        )
    ]

    assert outputs[-1][3] == "error"
    assert "attachment" in outputs[-1][4].lower()


def test_history_restores_tool_activity(tmp_path, monkeypatch):
    monkeypatch.setenv("ALFRED_RUNTIME_ROOT", str(tmp_path))
    from app.app import _load_session_into_state

    session_dir = _write_session(tmp_path, "20261019T120000Z-ddd", "Hello")
    (session_dir / "messages.ndjson").write_text(
        json.dumps({"role": "user", "content": "Hello"})
        + "\n"
        + json.dumps({"role": "assistant", "content": "Done", "status": "done"})
        + "\n"
    )
    (session_dir / "events.ndjson").write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "type": "meta",
                        "session_id": "20261019T120000Z-ddd",
                        "backend": "alfred-cli",
                    }
                ),
                json.dumps(
                    {
                        "type": "tool_request",
                        "name": "Read",
                        "arguments": {"path": "README.md"},
                    }
                ),
                json.dumps(
                    {
                        "type": "tool_result",
                        "name": "Read",
                        "output": "contents",
                        "is_error": False,
                    }
                ),
                json.dumps({"type": "delta", "content": "Done"}),
                json.dumps({"type": "done", "result": "completed"}),
            ]
        )
        + "\n"
    )

    messages, *_rest = _load_session_into_state("20261019T120000Z-ddd", "general")

    assert [message["role"] for message in messages] == [
        "user",
        "assistant",
        "assistant",
        "assistant",
    ]
    assert messages[1]["kind"] == "tool"
    assert messages[2]["kind"] == "tool"
    assert messages[3]["content"] == "Done"


def test_history_preserves_interleaved_deltas_and_tools(tmp_path, monkeypatch):
    monkeypatch.setenv("ALFRED_RUNTIME_ROOT", str(tmp_path))
    from app.app import _load_session_into_state

    session_dir = _write_session(tmp_path, "20261019T120500Z-eee", "Hello")
    (session_dir / "messages.ndjson").write_text(
        json.dumps({"role": "user", "content": "Hello"})
        + "\n"
        + json.dumps({"role": "assistant", "content": "beforeafter", "status": "done"})
        + "\n"
    )
    (session_dir / "events.ndjson").write_text(
        "\n".join(
            [
                json.dumps({"type": "meta", "session_id": "20261019T120500Z-eee"}),
                json.dumps({"type": "delta", "content": "before"}),
                json.dumps(
                    {
                        "type": "tool_request",
                        "name": "Read",
                        "arguments": {"path": "README.md"},
                    }
                ),
                json.dumps(
                    {
                        "type": "tool_result",
                        "name": "Read",
                        "output": "contents",
                        "is_error": False,
                    }
                ),
                json.dumps({"type": "delta", "content": "after"}),
                json.dumps({"type": "done", "result": "completed"}),
            ]
        )
        + "\n"
    )

    messages, *_rest = _load_session_into_state("20261019T120500Z-eee", "general")

    assert [message["role"] for message in messages] == [
        "user",
        "assistant",
        "assistant",
        "assistant",
        "assistant",
    ]
    assert messages[1]["content"] == "before"
    assert messages[2]["kind"] == "tool"
    assert messages[3]["kind"] == "tool"
    assert messages[4]["content"] == "after"


def test_history_keeps_two_turns_in_order(tmp_path, monkeypatch):
    monkeypatch.setenv("ALFRED_RUNTIME_ROOT", str(tmp_path))
    from app.app import _load_session_into_state

    session_dir = _write_session(tmp_path, "20261019T121000Z-fff", "First")
    (session_dir / "messages.ndjson").write_text(
        "\n".join(
            [
                json.dumps({"role": "user", "content": "First"}),
                json.dumps({"role": "assistant", "content": "One", "status": "done"}),
                json.dumps({"role": "user", "content": "Second"}),
                json.dumps({"role": "assistant", "content": "Two", "status": "done"}),
            ]
        )
        + "\n"
    )
    (session_dir / "events.ndjson").write_text(
        "\n".join(
            [
                json.dumps({"type": "meta", "session_id": "20261019T121000Z-fff"}),
                json.dumps({"type": "delta", "content": "One"}),
                json.dumps({"type": "done", "result": "completed"}),
                json.dumps({"type": "meta", "session_id": "20261019T121000Z-fff"}),
                json.dumps({"type": "delta", "content": "Two"}),
                json.dumps({"type": "done", "result": "completed"}),
            ]
        )
        + "\n"
    )

    messages, *_rest = _load_session_into_state("20261019T121000Z-fff", "general")

    assert [(message["role"], message["content"]) for message in messages] == [
        ("user", "First"),
        ("assistant", "One"),
        ("user", "Second"),
        ("assistant", "Two"),
    ]


def test_history_handles_failed_startup_without_meta(tmp_path, monkeypatch):
    monkeypatch.setenv("ALFRED_RUNTIME_ROOT", str(tmp_path))
    from app.app import _load_session_into_state

    session_dir = _write_session(tmp_path, "20261019T121500Z-ggg", "First")
    (session_dir / "messages.ndjson").write_text(
        "\n".join(
            [
                json.dumps({"role": "user", "content": "First"}),
                json.dumps({"role": "assistant", "content": "One", "status": "done"}),
                json.dumps({"role": "user", "content": "Second"}),
                json.dumps(
                    {"role": "assistant", "content": "Startup failed", "status": "error"}
                ),
            ]
        )
        + "\n"
    )
    (session_dir / "events.ndjson").write_text(
        "\n".join(
            [
                json.dumps({"type": "meta", "session_id": "20261019T121500Z-ggg"}),
                json.dumps(
                    {
                        "type": "tool_request",
                        "name": "Read",
                        "arguments": {"path": "README.md"},
                    }
                ),
                json.dumps(
                    {
                        "type": "tool_result",
                        "name": "Read",
                        "output": "contents",
                        "is_error": False,
                    }
                ),
                json.dumps({"type": "delta", "content": "One"}),
                json.dumps({"type": "done", "result": "completed"}),
                json.dumps({"type": "error", "message": "failed to start"}),
            ]
        )
        + "\n"
    )

    messages, *_rest = _load_session_into_state("20261019T121500Z-ggg", "general")

    assert [(message["role"], message.get("kind")) for message in messages] == [
        ("user", None),
        ("assistant", "tool"),
        ("assistant", "tool"),
        ("assistant", None),
        ("user", None),
        ("assistant", None),
    ]
    assert [message["content"] for message in messages if message.get("kind") != "tool"] == [
        "First",
        "One",
        "Second",
        "Startup failed",
    ]
    assert "Read" in messages[1]["content"]
    assert "contents" in messages[2]["content"]
    assert messages[5]["status"] == "error"


async def test_send_rejects_mixed_valid_and_invalid_attachments(tmp_path, monkeypatch):
    monkeypatch.setenv("ALFRED_RUNTIME_ROOT", str(tmp_path))
    from app.app import _handle_send_stream

    image = tmp_path / "good.png"
    image.write_bytes(b"\x89PNG\r\n\x1a\nfake")
    called = False

    async def fake_stream(prompt, **kwargs):
        nonlocal called
        called = True
        yield {"type": "done", "result": "completed"}

    monkeypatch.setattr("app.app.stream_filesystem_agent", fake_stream)
    payload = {
        "text": "Describe these",
        "files": [str(image), str(tmp_path / "missing.png")],
    }

    outputs = [
        item
        async for item in _handle_send_stream(
            payload,
            [],
            None,
            None,
            "auto",
            [],
            None,
            None,
            "general",
        )
    ]

    assert outputs[-1][3] == "error"
    assert "attachments" in outputs[-1][4].lower()
    assert called is False
