import base64


def test_app_ui_imports():
    from app.app import app_ui, server

    assert app_ui is not None
    assert callable(server)


def test_app_constructs():
    from app.app import app, server

    assert callable(app)
    assert callable(server)


# ── Voice record button ──────────────────────────────────────────────


def test_voice_record_button_in_ui():
    from app.app import app_ui

    html = str(app_ui)
    assert 'id="voice_record"' in html


def test_voice_media_recorder_script_content():
    from app.app import VOICE_RECORDER_SCRIPT

    assert "MediaRecorder" in VOICE_RECORDER_SCRIPT
    assert "voice_audio" in VOICE_RECORDER_SCRIPT
    assert "setInputValue" in VOICE_RECORDER_SCRIPT


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


def test_send_prompt_coroutine_in_server():
    import inspect

    from app.app import server

    source = inspect.getsource(server)
    assert "async def _send_prompt" in source
