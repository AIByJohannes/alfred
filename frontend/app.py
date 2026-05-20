from __future__ import annotations

import asyncio
import base64
import json
from typing import Any

import streamlit as st

from scripts.chat import stream_chat
from scripts.common import get_sessions_root
from scripts.fs_agent import stream_filesystem_agent

st.set_page_config(
    page_title="Alfred Workbench",
    page_icon=":material/smart_toy:",
    layout="wide",
    initial_sidebar_state="expanded",
)

_DEFAULTS: dict[str, Any] = {
    "messages": [],
    "session_id": None,
    "artifacts": [],
    "mode": "chat",
    "cwd": "",
    "fs_backend": "auto",
    "status": "idle",
    "status_detail": "Standing by.",
    "resolved_backend": None,
    "pending_image": None,
    "_running": False,
}
for key, val in _DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = val


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
                    "mode": (
                        "chat" if data.get("mode") == "inference" else data.get("mode", "unknown")
                    ),
                    "timestamp": d.name.split("-")[0],
                }
            )
        except Exception:
            pass
    return sessions


def run_stream(
    prompt: str,
    mode: str,
    session_id: str | None,
    cwd: str,
    backend: str,
    image_base64: str | None,
    placeholder: Any,
) -> tuple:
    async def _run():
        if mode == "chat":
            gen = stream_chat(prompt, session_id=session_id, image_base64=image_base64)
        else:
            gen = stream_filesystem_agent(
                prompt,
                cwd=cwd or None,
                session_id=session_id,
                backend=backend,
            )

        content = ""
        new_artifacts = []
        new_session_id = session_id
        resolved_backend = None

        async for event in gen:
            et = event.get("type", "")
            if et == "meta":
                new_session_id = event.get("session_id", new_session_id)
                resolved_backend = event.get("backend", resolved_backend)

            elif et == "delta":
                text = read_text(event)
                if text:
                    content += text
                    placeholder.markdown(content + "\u200b")

            elif et == "artifact":
                new_artifacts.append(event)

            elif et == "done":
                placeholder.markdown(content)
                msg = event.get("result") or event.get("message") or "Run complete."
                return content, new_artifacts, new_session_id, resolved_backend, "done", msg

            elif et == "error":
                placeholder.markdown(content)
                msg = event.get("message") or "The run failed."
                return content, new_artifacts, new_session_id, resolved_backend, "error", msg

        placeholder.markdown(content)
        return content, new_artifacts, new_session_id, resolved_backend, "done", "Run complete."

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_run())
    finally:
        loop.close()


def load_session_into_state(sid: str) -> None:
    session_dir = get_sessions_root() / sid
    if not session_dir.exists():
        return

    req_file = session_dir / "request.json"
    events_file = session_dir / "events.ndjson"
    messages_file = session_dir / "messages.ndjson"

    meta = {}
    if req_file.exists():
        meta = json.loads(req_file.read_text())

    events = []
    if events_file.exists():
        for line in events_file.read_text().splitlines():
            if line.strip():
                events.append(json.loads(line))

    messages = None
    if messages_file.exists():
        messages = []
        for line in messages_file.read_text().splitlines():
            if line.strip():
                messages.append(json.loads(line))

    new_msgs = []
    new_artifacts = []

    if messages:
        for msg in messages:
            image_b64 = None
            if msg.get("image_ref"):
                img_path = session_dir / msg["image_ref"]
                if img_path.exists():
                    image_b64 = base64.b64encode(img_path.read_bytes()).decode("utf-8")
            new_msgs.append(
                {
                    "role": msg["role"],
                    "content": msg["content"],
                    "status": msg.get("status"),
                    "image_base64": image_b64,
                }
            )
    else:
        user_prompt = meta.get("prompt", "Loaded session")
        assistant_content = ""
        for ev in events:
            if ev.get("type") == "delta":
                assistant_content += str(
                    ev.get("content")
                    or ev.get("delta")
                    or ev.get("message")
                    or ev.get("result")
                    or ""
                )
            if ev.get("type") == "artifact":
                new_artifacts.append(ev)

        image_b64 = None
        upload_path = session_dir / "upload.png"
        if upload_path.exists():
            image_b64 = base64.b64encode(upload_path.read_bytes()).decode("utf-8")

        new_msgs.append({"role": "user", "content": user_prompt, "image_base64": image_b64})
        new_msgs.append({"role": "assistant", "content": assistant_content, "status": "done"})

    st.session_state.messages = new_msgs
    st.session_state.artifacts = new_artifacts
    st.session_state.session_id = sid
    st.session_state.status = "idle"
    st.session_state.status_detail = "Session loaded."
    st.session_state.resolved_backend = None


# ======================== SIDEBAR ========================
with st.sidebar:
    st.title("A.L.F.R.E.D.")
    st.caption("Algorithmic Life-form\nFeigning Real Emotional Depth")

    if st.button(":material/add_circle: New Chat", use_container_width=True, type="primary"):
        for key in ("messages", "session_id", "artifacts"):
            st.session_state[key] = [] if key != "session_id" else None
        st.session_state.status = "idle"
        st.session_state.status_detail = "Standing by."
        st.session_state.resolved_backend = None
        st.session_state.pending_image = None
        st.rerun()

    st.divider()

    st.subheader("Execution Mode")
    mode = st.radio(
        "mode",
        options=["chat", "fs-agent"],
        format_func={"chat": "Chat", "fs-agent": "Agent"}.get,
        index=0 if st.session_state.mode == "chat" else 1,
        label_visibility="collapsed",
        key="mode_radio",
    )
    st.session_state.mode = mode

    if st.session_state.resolved_backend:
        st.caption(f"Backend: {st.session_state.resolved_backend}")

    if mode == "fs-agent":
        st.subheader("Agent Settings")
        st.session_state.cwd = st.text_input(
            "Working Directory",
            value=st.session_state.cwd,
            placeholder="/path/to/repo",
        )
        st.session_state.fs_backend = st.selectbox(
            "Backend Fallback",
            options=["auto", "alfred-cli", "smolagents"],
            index=["auto", "alfred-cli", "smolagents"].index(st.session_state.fs_backend),
        )

    st.divider()

    if st.session_state.artifacts:
        st.subheader("Artifacts")
        for art in st.session_state.artifacts:
            label = art.get("label", "artifact")
            path = art.get("path") or art.get("url") or "pending"
            st.text(f":material/download: {label}: {path}")

    st.subheader("History")
    sessions = get_sessions()
    if not sessions:
        st.caption("No sessions yet.")
    for s in sessions:
        label = (s["prompt"][:50] or "Empty") + f"\n{s['mode']}  {s['timestamp']}"
        active = s["id"] == st.session_state.session_id
        if st.button(
            label,
            key=f"sess_{s['id']}",
            use_container_width=True,
            disabled=st.session_state._running,
            type="secondary" if not active else "primary",
        ):
            load_session_into_state(s["id"])
            st.rerun()

# ======================== MAIN ========================
status_styles = {
    "running": {"icon": ":material/progress_activity:", "bg": "#fff3cd", "fg": "#856404"},
    "done": {"icon": ":material/check_circle:", "bg": "#d4edda", "fg": "#155724"},
    "error": {"icon": ":material/error:", "bg": "#f8d7da", "fg": "#721c24"},
    "idle": {"icon": "", "bg": "transparent", "fg": "inherit"},
}

if st.session_state.status != "idle" and not st.session_state._running:
    s = status_styles.get(st.session_state.status, status_styles["idle"])
    st.markdown(
        f"<div style='padding:0.5rem 1rem;background:{s['bg']};color:{s['fg']};"
        f"border-radius:0.25rem;margin-bottom:0.5rem;font-size:0.85rem'>"
        f"{s['icon']} {st.session_state.status_detail}</div>",
        unsafe_allow_html=True,
    )

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg.get("image_base64"):
            st.image(f"data:image/png;base64,{msg['image_base64']}", width=240)
        st.markdown(msg.get("content", ""))
        if msg.get("status") == "running":
            st.markdown("...")

# === Toolbar + Input ===
toolbar, input_area = st.columns([4, 6])
with toolbar:
    tb_cols = st.columns([1, 1, 1])
    with tb_cols[0]:
        camera = st.camera_input(
            "📷",
            label_visibility="collapsed",
            disabled=st.session_state._running or st.session_state.mode != "chat",
            key="camera_widget",
        )
        if camera and st.session_state.mode == "chat":
            st.session_state.pending_image = base64.b64encode(camera.getvalue()).decode("utf-8")

    with tb_cols[1]:
        audio = st.audio_input(
            "🎤",
            label_visibility="collapsed",
            disabled=st.session_state._running or st.session_state.mode != "chat",
            key="audio_widget",
        )
        if audio and st.session_state.mode == "chat":
            try:
                from transcription.service import get_transcription_service

                service = get_transcription_service()
                result = service.transcribe_file(
                    audio_data=audio.getvalue(),
                    filename=audio.name or "speech.webm",
                )
                st.toast(f"Transcribed: {result.text[:60]}...", icon="🎤")
                st.session_state._pending_transcript = result.text
                st.rerun()
            except Exception as e:
                st.error(f"Transcription failed: {e}")

    with tb_cols[2]:
        if st.button(":material/delete: Clear", disabled=st.session_state._running):
            st.session_state.messages = []
            st.session_state.artifacts = []
            st.session_state.session_id = None
            st.session_state.status = "idle"
            st.session_state.status_detail = "Workbench cleared."
            st.session_state.resolved_backend = None
            st.session_state.pending_image = None
            st.rerun()

prompt = st.chat_input("Message Alfred...", disabled=st.session_state._running)

# === Handle pending transcript (auto-fills input area) ===
if st.session_state.get("_pending_transcript") and not prompt:
    transcript = st.session_state._pending_transcript
    del st.session_state._pending_transcript
    if transcript.strip():
        st.info(f"Transcribed: {transcript}", icon="🎤")

# === Handle prompt submission ===
if prompt:
    st.session_state._running = True
    image_b64 = st.session_state.pending_image

    user_msg: dict[str, Any] = {"role": "user", "content": prompt}
    if image_b64:
        user_msg["image_base64"] = image_b64
        st.session_state.pending_image = None
    st.session_state.messages.append(user_msg)

    with st.chat_message("user"):
        if image_b64:
            st.image(f"data:image/png;base64,{image_b64}", width=240)
        st.markdown(prompt)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        placeholder.markdown("\u200b")

    result = run_stream(
        prompt=prompt,
        mode=st.session_state.mode,
        session_id=st.session_state.session_id,
        cwd=st.session_state.cwd,
        backend=st.session_state.fs_backend,
        image_base64=image_b64,
        placeholder=placeholder,
    )
    content, new_artifacts, new_session_id, resolved_backend, final_status, final_detail = result

    st.session_state.messages.append(
        {"role": "assistant", "content": content, "status": final_status}
    )
    if new_session_id:
        st.session_state.session_id = new_session_id
    if new_artifacts:
        st.session_state.artifacts.extend(new_artifacts)
    st.session_state.resolved_backend = resolved_backend
    st.session_state.status = final_status
    st.session_state.status_detail = final_detail
    st.session_state._running = False

    st.rerun()
