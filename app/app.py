import asyncio
import base64
import json
from pathlib import Path
from typing import Any

import gradio as gr

from scripts.common import get_sessions_root
from scripts.fs_agent import stream_filesystem_agent


def _short(s: str, n: int = 40) -> str:
    return (s[:n] + "...") if len(s) > n else s


def read_text(data: Any) -> str:
    if isinstance(data, str):
        return data
    if isinstance(data, dict):
        return str(
            data.get("text")
            or data.get("delta")
            or data.get("message")
            or data.get("content")
            or data.get("result")
            or ""
        )
    return str(data) if data else ""


def decode_voice_audio_data(payload: dict) -> tuple[bytes, str]:
    mime = payload.get("mimeType", "audio/webm")
    ext = mime.split("/")[-1].split(";")[0]
    data_b64 = payload.get("data", "")
    audio_bytes = base64.b64decode(data_b64)
    filename = f"voice.{ext}"
    return audio_bytes, filename


def get_sessions() -> list[dict]:
    root = get_sessions_root()
    if not root.exists():
        return []
    sessions = []
    for d in sorted(root.iterdir(), key=lambda d: d.name, reverse=True):
        if not d.is_dir():
            continue
        req = d / "request.json"
        if not req.exists():
            continue
        try:
            data = json.loads(req.read_text())
            sessions.append(
                {
                    "id": d.name,
                    "prompt": data.get("prompt", ""),
                    "timestamp": d.name.split("-")[0],
                }
            )
        except Exception:
            pass
    return sessions


def _render_status(st: str, dt: str) -> str:
    if st == "idle":
        icon = '<i class="fas fa-info-circle"></i> '
        cls = "status-idle"
    elif st == "running":
        icon = '<i class="fas fa-spinner fa-spin"></i> '
        cls = "status-running"
    elif st == "done":
        icon = '<i class="fas fa-check-circle"></i> '
        cls = "status-done"
    else:
        icon = '<i class="fas fa-exclamation-triangle"></i> '
        cls = "status-error"
    return f'<div class="status-banner {cls}">{icon}<span id="status-indicator">{dt}</span></div>'


def _render_artifacts(arts: list[dict]) -> str:
    if not arts:
        return ""
    h = (
        '<h4 style="font-weight:600;margin-bottom:0.75rem;'
        'font-size:0.95rem;color:#abb2bf">Artifacts</h4>'
    )
    parts = [f"<div>{h}"]
    for art in arts:
        label = art.get("label", "artifact")
        path = art.get("path") or art.get("url") or "pending"
        name = Path(path).name if path != "pending" else "pending"
        parts.append(
            '<div class="artifact-card">'
            f'<span style="font-weight:500">📦 {label}</span>'
            f'<span style="font-size:0.75rem;color:#7f848e;word-break:break-all;'
            f'margin-top:2px">{name}</span></div>'
        )
    parts.append("</div>")
    return "".join(parts)


def _render_pending(name: str | None) -> str:
    if not name:
        return ""
    return (
        '<span style="color:#98c379;font-size:0.85rem;padding:0.25rem 0.5rem;'
        'background:rgba(152,195,121,0.1);border-radius:4px;'
        'border:1px solid rgba(152,195,121,0.3)">'
        f"📷 {name}</span>"
    )


def _build_history_choices(sid: str | None) -> tuple[list[tuple[str, str]], str | None]:
    sessions = get_sessions()
    choices: list[tuple[str, str]] = []
    for s in sessions:
        lbl = s["prompt"][:40] or "Empty session"
        if len(s["prompt"]) > 40:
            lbl += "..."
        lbl += f"\n{s['timestamp']}"
        choices.append((lbl, s["id"]))
    value = sid if any(c[1] == sid for c in choices) else None
    return choices, value


def _load_session_into_state(
    sid: str,
) -> tuple[list[dict], list[dict], str, str, str, str | None, str | None, str | None, object]:
    session_dir = get_sessions_root() / sid
    if not session_dir.exists():
        return [], [], sid, "idle", "Session loaded.", None, None, None, gr.update()

    req_file = session_dir / "request.json"
    events_file = session_dir / "events.ndjson"
    messages_file = session_dir / "messages.ndjson"

    meta = {}
    if req_file.exists():
        try:
            meta = json.loads(req_file.read_text())
        except Exception:
            pass

    events = []
    if events_file.exists():
        try:
            for line in events_file.read_text().splitlines():
                if line.strip():
                    events.append(json.loads(line))
        except Exception:
            pass

    messages_list = None
    if messages_file.exists():
        try:
            messages_list = []
            for line in messages_file.read_text().splitlines():
                if line.strip():
                    messages_list.append(json.loads(line))
        except Exception:
            pass

    new_msgs: list[dict] = []
    new_artifacts: list[dict] = []

    if messages_list:
        for msg in messages_list:
            image_b64 = None
            if msg.get("image_ref"):
                img_path = session_dir / msg["image_ref"]
                if img_path.exists():
                    try:
                        image_b64 = base64.b64encode(img_path.read_bytes()).decode("utf-8")
                    except Exception:
                        pass
            content = msg["content"]
            if image_b64:
                prefix = f"![image](data:image/png;base64,{image_b64})\n\n"
                content = (prefix + content) if content else prefix
            new_msgs.append(
                {
                    "role": msg["role"],
                    "content": content,
                    "status": msg.get("status"),
                }
            )
    else:
        user_prompt = meta.get("prompt", "Loaded session")
        assistant_content = ""
        for ev in events:
            if ev.get("type") == "delta":
                assistant_content += read_text(ev)
            if ev.get("type") == "artifact":
                new_artifacts.append(ev)

        image_b64 = None
        upload_path = session_dir / "upload.png"
        if upload_path.exists():
            try:
                image_b64 = base64.b64encode(upload_path.read_bytes()).decode("utf-8")
            except Exception:
                pass

        if image_b64:
            user_prompt = f"![image](data:image/png;base64,{image_b64})\n\n{user_prompt}"
        new_msgs.append({"role": "user", "content": user_prompt})
        new_msgs.append({"role": "assistant", "content": assistant_content, "status": "done"})

    choices, _ = _build_history_choices(sid)
    return (
        new_msgs,
        new_artifacts,
        sid,
        "idle",
        "Session loaded.",
        None,
        None,
        None,
        gr.update(choices=choices, value=sid),
    )


async def _transcribe_and_fill(audio_path: str, current_prompt: str) -> tuple[str, str, str]:
    if not audio_path:
        return current_prompt, "idle", "Standing by."
    p = Path(audio_path)
    if not p.exists():
        return current_prompt, "idle", "Standing by."
    audio_bytes = p.read_bytes()
    filename = p.name or "speech.webm"

    try:
        from transcription.service import get_transcription_service
        service = get_transcription_service()
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None,
            lambda: service.transcribe_file(audio_data=audio_bytes, filename=filename),
        )
        text = (result.text or "").strip()
        if text:
            return text, "idle", "Transcription ready."
        return current_prompt, "idle", "Audio transcription empty."
    except Exception as e:
        return current_prompt, "error", f"Transcription error: {e}"


async def _handle_send_stream(
    prompt_text: str,
    current_msgs: list[dict],
    img_b64: str | None,
    cwd_val: str,
    backend_val: str,
    current_artifacts: list[dict],
    current_sid: str | None,
    current_res: str | None,
):
    if not prompt_text or not str(prompt_text).strip():
        choices, val = _build_history_choices(current_sid)
        yield (
            current_msgs,
            current_artifacts,
            "idle",
            "Standing by.",
            current_sid,
            current_res,
            None,
            None,
            gr.update(),
            gr.update(choices=choices, value=val),
        )
        return

    user_content = prompt_text
    if img_b64:
        user_content = f"![image](data:image/png;base64,{img_b64})\n\n{prompt_text}"

    new_msgs = current_msgs + [{"role": "user", "content": user_content}]
    choices, val = _build_history_choices(current_sid)
    yield (
        new_msgs,
        current_artifacts,
        "running",
        "Alfred is processing your query...",
        current_sid,
        current_res,
        None,
        None,
        gr.update(value=""),
        gr.update(choices=choices, value=val),
    )

    new_msgs = new_msgs + [{"role": "assistant", "content": "", "status": "running"}]
    choices, val = _build_history_choices(current_sid)
    yield (
        new_msgs,
        current_artifacts,
        "running",
        "Alfred is processing your query...",
        current_sid,
        current_res,
        None,
        None,
        gr.update(value=""),
        gr.update(choices=choices, value=val),
    )

    gen = stream_filesystem_agent(
        prompt_text,
        cwd=cwd_val or None,
        session_id=current_sid,
        backend=backend_val,
    )

    content = ""
    new_arts = list(current_artifacts)
    new_sid = current_sid
    res_b = current_res

    try:
        async for event in gen:
            et = event.get("type", "")
            if et == "meta":
                new_sid = event.get("session_id", new_sid)
                res_b = event.get("backend", res_b)
                choices, val = _build_history_choices(new_sid)
                yield (
                    new_msgs,
                    new_arts,
                    "running",
                    "Alfred is processing your query...",
                    new_sid,
                    res_b,
                    None,
                    None,
                    gr.update(),
                    gr.update(choices=choices, value=val),
                )
            elif et == "delta":
                text = read_text(event)
                if text:
                    content += text
                    if new_msgs:
                        new_msgs[-1]["content"] = content
                    choices, val = _build_history_choices(new_sid)
                    yield (
                        new_msgs,
                        new_arts,
                        "running",
                        "Alfred is processing your query...",
                        new_sid,
                        res_b,
                        None,
                        None,
                        gr.update(),
                        gr.update(choices=choices, value=val),
                    )
            elif et == "artifact":
                new_arts = new_arts + [event]
                choices, val = _build_history_choices(new_sid)
                yield (
                    new_msgs,
                    new_arts,
                    "running",
                    "Alfred is processing your query...",
                    new_sid,
                    res_b,
                    None,
                    None,
                    gr.update(),
                    gr.update(choices=choices, value=val),
                )
            elif et == "done":
                msg = event.get("result") or event.get("message") or "Run complete."
                if new_msgs:
                    new_msgs[-1]["status"] = "done"
                choices, val = _build_history_choices(new_sid)
                yield (
                    new_msgs,
                    new_arts,
                    "done",
                    msg,
                    new_sid,
                    res_b,
                    None,
                    None,
                    gr.update(),
                    gr.update(choices=choices, value=val),
                )
                return
            elif et == "error":
                msg = event.get("message") or "The run failed."
                if new_msgs:
                    new_msgs[-1]["status"] = "error"
                choices, val = _build_history_choices(new_sid)
                yield (
                    new_msgs,
                    new_arts,
                    "error",
                    msg,
                    new_sid,
                    res_b,
                    None,
                    None,
                    gr.update(),
                    gr.update(choices=choices, value=val),
                )
                return
        if new_msgs:
            new_msgs[-1]["status"] = "done"
        choices, val = _build_history_choices(new_sid)
        yield (
            new_msgs,
            new_arts,
            "done",
            "Run complete.",
            new_sid,
            res_b,
            None,
            None,
            gr.update(),
            gr.update(choices=choices, value=val),
        )
    except Exception as e:
        if new_msgs:
            new_msgs[-1]["status"] = "error"
        choices, val = _build_history_choices(new_sid)
        yield (
            new_msgs,
            new_arts,
            "error",
            f"Error: {e}",
            new_sid,
            res_b,
            None,
            None,
            gr.update(),
            gr.update(choices=choices, value=val),
        )


def _clear_state(msg: str):
    choices, _ = _build_history_choices(None)
    return (
        [],
        None,
        [],
        "idle",
        msg,
        None,
        None,
        None,
        gr.update(value=""),
        gr.update(choices=choices, value=None),
    )


with gr.Blocks(
    theme=gr.Theme.from_hub("d8ahazard/rd_blue"),
    title="Alfred Workbench",
    css=Path(__file__).parent.joinpath("style.css").read_text(),
) as demo:
    messages = gr.State([])
    session_id = gr.State(None)
    artifacts = gr.State([])
    status = gr.State("idle")
    status_detail = gr.State("Standing by.")
    resolved_backend = gr.State(None)
    pending_image = gr.State(None)
    pending_image_name = gr.State(None)

    with gr.Row():
        with gr.Column(scale=1, min_width=280, elem_classes=["sidebar"]):
            gr.Markdown("## A.L.F.R.E.D.")
            new_session_btn = gr.Button("New Session", elem_classes=["btn-primary-custom", "w-100"])
            cwd = gr.Textbox(
                label="Working Directory (optional)",
                placeholder="/path/to/repo",
                elem_classes=["agent-settings-card"],
            )
            fs_backend = gr.Dropdown(
                choices=["auto", "alfred-cli", "smolagents"],
                value="auto",
                label="Backend Fallback",
                elem_classes=["agent-settings-card"],
            )
            artifacts_html = gr.HTML(elem_classes=["artifacts-panel"])
            gr.Markdown("### History")
            history_radio = gr.Radio(
                label="",
                choices=[],
                interactive=True,
                elem_classes=["history-radio"],
            )

        with gr.Column(scale=4, elem_classes=["main-layout"]):
            status_html = gr.HTML(elem_classes=["status-banner"])
            placeholder = (
                "**Alfred Standing By.**\n\n"
                "Greetings. I am Alfred, your Algorithmic Life-form Feigning "
                "Real Emotional Depth.\n\n"
                "Agent ready. Provide a prompt (cwd optional on left)."
            )
            chatbot = gr.Chatbot(
                placeholder=placeholder,
                type="messages",
                elem_classes=["chat-container"],
                show_copy_button=True,
                avatar_images=(None, None),
            )

            with gr.Row(elem_classes=["toolbar-row"]):
                image_upload = gr.UploadButton(
                    "📷 Image",
                    file_types=["image"],
                    elem_classes=["toolbar-file-upload"],
                )
                audio_upload = gr.UploadButton(
                    "🎤 Voice",
                    file_types=["audio"],
                    elem_classes=["toolbar-file-upload"],
                )
                pending_html = gr.HTML(elem_classes=["pending-upload"])
                gr.HTML("<div style='flex-grow:1'></div>")
                clear_btn = gr.Button("Clear", elem_classes=["btn-secondary-custom"])

            with gr.Row(elem_classes=["chat-footer"]):
                with gr.Row(elem_classes=["input-group-custom"]):
                    prompt = gr.Textbox(
                        placeholder="Message Alfred...",
                        show_label=False,
                        scale=8,
                        elem_classes=["chat-text-input"],
                        autofocus=True,
                    )
                    voice_audio = gr.Audio(
                        sources=["microphone"],
                        type="filepath",
                        label="",
                        show_label=False,
                        elem_classes=["voice-audio"],
                        scale=1,
                    )
                    send_btn = gr.Button("Send", elem_classes=["btn-primary-custom"], scale=1)

    # Derived renders
    status.change(
        _render_status,
        inputs=[status, status_detail],
        outputs=[status_html],
        api_name=False,
        show_api=False,
    )
    artifacts.change(
        _render_artifacts,
        inputs=[artifacts],
        outputs=[artifacts_html],
        api_name=False,
        show_api=False,
    )
    pending_image_name.change(
        _render_pending,
        inputs=[pending_image_name],
        outputs=[pending_html],
        api_name=False,
        show_api=False,
    )

    def _refresh_history(sid):
        choices, val = _build_history_choices(sid)
        return gr.update(choices=choices, value=val)

    # New / Clear
    new_session_btn.click(
        lambda: _clear_state("Session ready."),
        outputs=[
            messages,
            session_id,
            artifacts,
            status,
            status_detail,
            resolved_backend,
            pending_image,
            pending_image_name,
            prompt,
            history_radio,
        ],
        api_name=False,
        show_api=False,
    )
    clear_btn.click(
        lambda: _clear_state("Workbench cleared."),
        outputs=[
            messages,
            session_id,
            artifacts,
            status,
            status_detail,
            resolved_backend,
            pending_image,
            pending_image_name,
            prompt,
            history_radio,
        ],
        api_name=False,
        show_api=False,
    )

    # History load
    history_radio.change(
        _load_session_into_state,
        inputs=[history_radio],
        outputs=[
            messages,
            artifacts,
            session_id,
            status,
            status_detail,
            resolved_backend,
            pending_image,
            pending_image_name,
            history_radio,
        ],
        api_name=False,
        show_api=False,
    )

    # Image upload
    def _handle_image(files):
        if not files:
            return None, None
        p = files[0] if isinstance(files, list | tuple) else files
        try:
            b64 = base64.b64encode(Path(p).read_bytes()).decode("utf-8")
            return b64, Path(p).name
        except Exception:
            return None, None

    image_upload.upload(
        _handle_image,
        inputs=[image_upload],
        outputs=[pending_image, pending_image_name],
        api_name=False,
        show_api=False,
    )

    # Audio file upload -> transcribe to prompt
    audio_upload.upload(
        _transcribe_and_fill,
        inputs=[audio_upload, prompt],
        outputs=[prompt, status, status_detail],
        api_name=False,
        show_api=False,
    )

    # Microphone recording -> transcribe to prompt
    voice_audio.stop_recording(
        _transcribe_and_fill,
        inputs=[voice_audio, prompt],
        outputs=[prompt, status, status_detail],
        api_name=False,
        show_api=False,
    )

    # Send
    send_btn.click(
        _handle_send_stream,
        inputs=[
            prompt,
            messages,
            pending_image,
            cwd,
            fs_backend,
            artifacts,
            session_id,
            resolved_backend,
        ],
        outputs=[
            messages,
            artifacts,
            status,
            status_detail,
            session_id,
            resolved_backend,
            pending_image,
            pending_image_name,
            prompt,
            history_radio,
        ],
        api_name=False,
        show_api=False,
    )
    prompt.submit(
        _handle_send_stream,
        inputs=[
            prompt,
            messages,
            pending_image,
            cwd,
            fs_backend,
            artifacts,
            session_id,
            resolved_backend,
        ],
        outputs=[
            messages,
            artifacts,
            status,
            status_detail,
            session_id,
            resolved_backend,
            pending_image,
            pending_image_name,
            prompt,
            history_radio,
        ],
        api_name=False,
        show_api=False,
    )

    # Keep chatbot in sync with messages state
    messages.change(
        lambda m: m,
        inputs=[messages],
        outputs=[chatbot],
        api_name=False,
        show_api=False,
    )

    # After any major action that may create new sessions, refresh history choices
    for ev in (status, session_id):
        ev.change(
            _refresh_history,
            inputs=[session_id],
            outputs=[history_radio],
            api_name=False,
            show_api=False,
        )

    # Initial history load
    demo.load(
        _refresh_history,
        inputs=[session_id],
        outputs=[history_radio],
        api_name=False,
        show_api=False,
    )


app = demo

if __name__ == "__main__":
    demo.launch(server_port=8501, show_api=False)
