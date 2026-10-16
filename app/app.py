import asyncio
import base64
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import gradio as gr

from scripts.common import get_runtime_root, get_sessions_root
from scripts.fs_agent import stream_filesystem_agent


def _short(s: str, n: int = 40) -> str:
    return (s[:n] + "...") if len(s) > n else s


def _format_session_timestamp(value: str) -> str:
    try:
        timestamp = datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC)
    except ValueError:
        return value
    return timestamp.strftime("%d %b %Y, %H:%M UTC")


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


DEFAULT_WORKSPACE_ID = "general"


def _workspace_path() -> Path:
    return get_runtime_root() / "workspaces.json"


def _read_workspaces() -> dict[str, dict[str, Any]]:
    try:
        payload = json.loads(_workspace_path().read_text(encoding="utf-8"))
        if isinstance(payload, dict) and payload:
            return payload
    except (OSError, json.JSONDecodeError):
        pass
    return {DEFAULT_WORKSPACE_ID: {"name": "General", "sessions": []}}


def _write_workspaces(workspaces: dict[str, dict[str, Any]]) -> None:
    _workspace_path().write_text(json.dumps(workspaces, indent=2), encoding="utf-8")


def _workspace_choices() -> list[tuple[str, str]]:
    return [(data["name"], workspace_id) for workspace_id, data in _read_workspaces().items()]


def _create_workspace(name: str) -> object:
    cleaned = name.strip()
    workspaces = _read_workspaces()
    if not cleaned:
        return gr.update(choices=_workspace_choices(), value=DEFAULT_WORKSPACE_ID)
    workspace_id = f"workspace-{uuid4().hex[:8]}"
    workspaces[workspace_id] = {"name": cleaned[:80], "sessions": []}
    _write_workspaces(workspaces)
    return gr.update(choices=_workspace_choices(), value=workspace_id)


def _add_session_to_workspace(workspace_id: str, session_id: str) -> None:
    workspaces = _read_workspaces()
    target_id = workspace_id if workspace_id in workspaces else DEFAULT_WORKSPACE_ID
    for data in workspaces.values():
        data["sessions"] = [sid for sid in data.get("sessions", []) if sid != session_id]
    workspaces[target_id].setdefault("sessions", []).append(session_id)
    _write_workspaces(workspaces)


def get_sessions(workspace_id: str | None = None) -> list[dict]:
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
    if workspace_id is None:
        return sessions
    workspaces = _read_workspaces()
    known_sessions = {sid for item in workspaces.values() for sid in item.get("sessions", [])}
    allowed = set(workspaces.get(workspace_id, {}).get("sessions", []))
    if workspace_id == DEFAULT_WORKSPACE_ID:
        allowed.update(session["id"] for session in sessions if session["id"] not in known_sessions)
    return [session for session in sessions if session["id"] in allowed]


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


def _build_history_choices(
    sid: str | None, workspace_id: str | None = DEFAULT_WORKSPACE_ID
) -> tuple[list[tuple[str, str]], str | None]:
    sessions = get_sessions(workspace_id)
    choices: list[tuple[str, str]] = []
    for s in sessions:
        lbl = s["prompt"][:40] or "Empty session"
        if len(s["prompt"]) > 40:
            lbl += "..."
        lbl += f"\n{_format_session_timestamp(s['timestamp'])}"
        choices.append((lbl, s["id"]))
    value = sid if any(c[1] == sid for c in choices) else None
    return choices, value


def _load_session_into_state(
    sid: str,
    workspace_id: str = DEFAULT_WORKSPACE_ID,
) -> tuple[
    list[dict],
    list[dict],
    str,
    str,
    str,
    str | None,
    str | None,
    str | None,
    object,
    list[dict],
]:
    session_dir = get_sessions_root() / sid
    if not session_dir.exists():
        return [], [], sid, "idle", "Session loaded.", None, None, None, gr.update(), []

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
            if str(content).strip():
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
        if assistant_content.strip():
            new_msgs.append(
                {"role": "assistant", "content": assistant_content, "status": "done"}
            )

    choices, _ = _build_history_choices(sid, workspace_id)
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
        new_msgs,
    )


def _parse_prompt_payload(payload: Any) -> tuple[str, list]:
    """Accept a plain string (legacy Textbox) or a MultimodalTextbox dict."""
    if payload is None:
        return "", []
    if isinstance(payload, str):
        return payload, []
    if isinstance(payload, dict):
        text = payload.get("text") or ""
        files = payload.get("files") or payload.get("data") or []
        if not isinstance(files, list):
            files = [files]
        return (text if isinstance(text, str) else str(text)), files
    return str(payload), []


def _file_to_b64(entry: Any) -> tuple[str | None, str | None]:
    try:
        if isinstance(entry, dict):
            raw = entry.get("path") or entry.get("url")
            name = entry.get("orig_name") or entry.get("name") or "upload"
        else:
            raw = entry
            name = "upload"
        if raw is None:
            return None, None
        candidate = Path(str(raw))
        if not candidate.exists():
            return None, None
        return base64.b64encode(candidate.read_bytes()).decode("utf-8"), candidate.name or str(name)
    except Exception:
        return None, None


def _current_text(payload: Any) -> str:
    text, _ = _parse_prompt_payload(payload)
    return text


async def _transcribe_and_fill(audio_path: str, current_prompt: Any) -> tuple[str, str, str]:
    fallback = _current_text(current_prompt)
    if not audio_path:
        return fallback, "idle", "Standing by."
    p = Path(audio_path)
    if not p.exists():
        return fallback, "idle", "Standing by."
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
        return fallback, "idle", "Audio transcription empty."
    except Exception as e:
        return fallback, "error", f"Transcription error: {e}"


async def _handle_send_stream(
    prompt_text: Any,
    current_msgs: list[dict],
    img_b64: str | None,
    cwd_val: str,
    backend_val: str,
    current_artifacts: list[dict],
    current_sid: str | None,
    current_res: str | None,
    workspace_id: str,
):
    prompt_str, attached_files = _parse_prompt_payload(prompt_text)
    if attached_files and not img_b64:
        for entry in attached_files:
            converted, _ = _file_to_b64(entry)
            if converted:
                img_b64 = converted
                break
    if not prompt_str or not prompt_str.strip():
        choices, val = _build_history_choices(current_sid, workspace_id)
        yield (
            current_msgs,
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

    user_content = prompt_str
    if img_b64:
        user_content = f"![image](data:image/png;base64,{img_b64})\n\n{prompt_str}"

    new_msgs = current_msgs + [{"role": "user", "content": user_content}]
    choices, val = _build_history_choices(current_sid, workspace_id)
    yield (
        new_msgs,
        new_msgs,
        current_artifacts,
        "running",
        "Alfred is processing your query...",
        current_sid,
        current_res,
        None,
        None,
        gr.update(value={"text": "", "files": []}),
        gr.update(choices=choices, value=val),
    )

    agent_prompt = prompt_str
    if current_sid is None and current_msgs:
        transcript = "\n".join(
            f"{message.get('role', 'user').title()}: {message.get('content', '')}"
            for message in current_msgs
        )
        agent_prompt = (
            "Continue this forked conversation. Treat the transcript as context, then answer "
            "the final user message.\n\n<conversation>\n"
            f"{transcript}\n</conversation>\n\nFinal user message: {prompt_str}"
        )

    gen = stream_filesystem_agent(
        agent_prompt,
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
                if new_sid:
                    _add_session_to_workspace(workspace_id, new_sid)
                choices, val = _build_history_choices(new_sid, workspace_id)
                yield (
                    new_msgs,
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
                    if new_msgs and new_msgs[-1].get("role") == "assistant":
                        new_msgs[-1]["content"] = content
                    else:
                        new_msgs = new_msgs + [
                            {"role": "assistant", "content": content, "status": "running"}
                        ]
                    choices, val = _build_history_choices(new_sid, workspace_id)
                    yield (
                        new_msgs,
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
                choices, val = _build_history_choices(new_sid, workspace_id)
                yield (
                    new_msgs,
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
                if new_msgs and new_msgs[-1].get("role") == "assistant":
                    new_msgs[-1]["status"] = "done"
                choices, val = _build_history_choices(new_sid, workspace_id)
                yield (
                    new_msgs,
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
                if new_msgs and new_msgs[-1].get("role") == "assistant":
                    new_msgs[-1]["status"] = "error"
                choices, val = _build_history_choices(new_sid, workspace_id)
                yield (
                    new_msgs,
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
        if new_msgs and new_msgs[-1].get("role") == "assistant":
            new_msgs[-1]["status"] = "done"
        choices, val = _build_history_choices(new_sid, workspace_id)
        yield (
            new_msgs,
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
        if new_msgs and new_msgs[-1].get("role") == "assistant":
            new_msgs[-1]["status"] = "error"
        choices, val = _build_history_choices(new_sid, workspace_id)
        yield (
            new_msgs,
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


def _clear_state(msg: str, workspace_id: str = DEFAULT_WORKSPACE_ID):
    choices, _ = _build_history_choices(None, workspace_id)
    return (
        [],
        None,
        [],
        "idle",
        msg,
        None,
        None,
        None,
        gr.update(value={"text": "", "files": []}),
        gr.update(choices=choices, value=None),
        [],
    )


def _fork_session(
    current_msgs: list[dict], current_artifacts: list[dict], workspace_id: str
):
    choices, _ = _build_history_choices(None, workspace_id)
    return (
        current_msgs,
        None,
        current_artifacts,
        "idle",
        "Fork ready.",
        None,
        None,
        None,
        gr.update(value={"text": "", "files": []}),
        gr.update(choices=choices, value=None),
        current_msgs,
    )


with gr.Blocks(
    title="Alfred",
    fill_height=True,
) as demo:
    messages = gr.State([])
    session_id = gr.State(None)
    artifacts = gr.State([])
    status = gr.State("idle")
    status_detail = gr.State("Standing by.")
    resolved_backend = gr.State(None)
    pending_image = gr.State(None)
    pending_image_name = gr.State(None)

    with gr.Sidebar(width=280, position="left", open=True, elem_id="sidebar"):
        gr.Markdown("## A.L.F.R.E.D.")
        new_session_btn = gr.Button(
            "New Chat",
            elem_id="new_session_btn",
            elem_classes=["btn-primary-custom", "w-100"],
        )

        cwd = gr.Textbox(
            label="Working Directory (optional)",
            placeholder="/path/to/repo",
            elem_classes=["agent-settings-card"],
        )
        fs_backend = gr.Dropdown(
            choices=["auto", "alfred-cli"],
            value="auto",
            label="Agent Backend",
            elem_classes=["agent-settings-card"],
        )
        workspace_selector = gr.Dropdown(
            choices=_workspace_choices(),
            value=DEFAULT_WORKSPACE_ID,
            label="Workspace",
            elem_classes=["agent-settings-card"],
        )
        with gr.Row(elem_classes=["workspace-create-row"]):
            workspace_name = gr.Textbox(
                placeholder="New workspace",
                show_label=False,
                container=False,
                min_width=0,
                elem_classes=["workspace-name-input"],
            )
            create_workspace_btn = gr.Button(
                "+", size="sm", scale=0, elem_id="create_workspace_btn", min_width=36
            )
        artifacts_html = gr.HTML(elem_classes=["artifacts-panel"])
        gr.Markdown("### History")
        history_radio = gr.Radio(
            label="",
            choices=[],
            interactive=True,
            elem_classes=["history-radio"],
        )

    with gr.Column(scale=1, elem_id="main-chat"):
        with gr.Row(elem_classes=["header-row"]):
            gr.Markdown("# Alfred Workspace", elem_classes=["header-title"])

        with gr.Column(elem_classes=["chat-center-wrapper"]):
            placeholder = (
                "**Alfred Standing By.**\n\n"
                "Greetings. I am Alfred, your Algorithmic Life-form Feigning "
                "Real Emotional Depth.\n\n"
                "Agent ready. Provide a prompt (cwd optional on left)."
            )
            chatbot = gr.Chatbot(
                placeholder=placeholder,
                elem_id="chatbot",
                container=False,
                show_label=False,
                buttons=["copy"],
                allow_tags=False,
                avatar_images=(None, None),
                autoscroll=True,
            )

            with gr.Row(elem_classes=["toolbar-row"]):
                audio_upload = gr.UploadButton(
                    "🎤 Voice Upload",
                    file_types=["audio"],
                    elem_classes=["toolbar-file-upload"],
                )
                voice_audio = gr.Audio(
                    sources=["microphone"],
                    type="filepath",
                    label="",
                    show_label=False,
                    elem_classes=["voice-audio"],
                )
                pending_html = gr.HTML(elem_classes=["pending-upload"])
                gr.HTML("<div style='flex-grow:1'></div>")
                fork_btn = gr.Button("Fork", elem_classes=["btn-secondary-custom"])
                clear_btn = gr.Button("Clear", elem_classes=["btn-secondary-custom"])

            prompt = gr.MultimodalTextbox(
                placeholder="Message Alfred...",
                file_types=["image"],
                sources=["upload"],
                lines=1,
                max_lines=7,
                show_label=False,
                autofocus=True,
                elem_id="input-container",
                submit_btn=True,
            )

    # Derived renders
    artifacts.change(
        _render_artifacts,
        inputs=[artifacts],
        outputs=[artifacts_html],
        api_visibility="private",
    )
    pending_image_name.change(
        _render_pending,
        inputs=[pending_image_name],
        outputs=[pending_html],
        api_visibility="private",
    )

    def _refresh_history(sid, workspace_id):
        choices, val = _build_history_choices(sid, workspace_id)
        return gr.update(choices=choices, value=val)

    def _change_workspace(workspace_id):
        choices, _ = _build_history_choices(None, workspace_id)
        return gr.update(choices=choices, value=None)

    create_workspace_btn.click(
        _create_workspace,
        inputs=[workspace_name],
        outputs=[workspace_selector],
        api_visibility="private",
    ).then(
        lambda: gr.update(value=""),
        outputs=[workspace_name],
        api_visibility="private",
    )
    workspace_selector.change(
        _change_workspace,
        inputs=[workspace_selector],
        outputs=[history_radio],
        api_visibility="private",
    )

    # New / Clear
    new_session_btn.click(
        lambda workspace_id: _clear_state("Session ready.", workspace_id),
        inputs=[workspace_selector],
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
            chatbot,
        ],
        api_visibility="private",
    )
    clear_btn.click(
        lambda workspace_id: _clear_state("Workbench cleared.", workspace_id),
        inputs=[workspace_selector],
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
            chatbot,
        ],
        api_visibility="private",
    )
    fork_btn.click(
        _fork_session,
        inputs=[messages, artifacts, workspace_selector],
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
            chatbot,
        ],
        api_visibility="private",
    )

    # History load
    history_radio.change(
        _load_session_into_state,
        inputs=[history_radio, workspace_selector],
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
            chatbot,
        ],
        api_visibility="private",
    )

    # Audio file upload -> transcribe to prompt
    audio_upload.upload(
        _transcribe_and_fill,
        inputs=[audio_upload, prompt],
        outputs=[prompt, status, status_detail],
        api_visibility="private",
    )

    # Microphone recording -> transcribe to prompt
    voice_audio.stop_recording(
        _transcribe_and_fill,
        inputs=[voice_audio, prompt],
        outputs=[prompt, status, status_detail],
        api_visibility="private",
    )

    # Send (MultimodalTextbox has its own submit/stop button)
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
            workspace_selector,
        ],
        outputs=[
            messages,
            chatbot,
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
        api_visibility="private",
    )

    # Keep chatbot in sync with messages state
    messages.change(
        lambda m: m,
        inputs=[messages],
        outputs=[chatbot],
        api_visibility="private",
    )

    # After any major action that may create new sessions, refresh history choices
    for ev in (status, session_id):
        ev.change(
            _refresh_history,
            inputs=[session_id, workspace_selector],
            outputs=[history_radio],
            api_visibility="private",
        )

    # Initial history load
    demo.load(
        _refresh_history,
        inputs=[session_id, workspace_selector],
        outputs=[history_radio],
        api_visibility="private",
    )


app = demo

if __name__ == "__main__":
    demo.launch(
        server_port=8501,
        theme=gr.themes.Monochrome(),
        css=Path(__file__).parent.joinpath("style.css").read_text(),
        footer_links=[],
    )
