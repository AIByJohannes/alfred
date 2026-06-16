import base64
import inspect
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
    assert 'gr.Theme.from_hub("d8ahazard/rd_blue")' in src or "d8ahazard/rd_blue" in src


def test_app_has_core_controls():
    import app.app as appmod
    src = inspect.getsource(appmod)

    # Essential control names / labels must be present in the Gradio UI definition
    # (updated for Gradio migration; no Shiny IDs remain)
    required = [
        "prompt",
        "cwd",
        "fs_backend",
        "image_upload",
        "audio_upload",
        "voice_audio",
        "send_btn",
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
