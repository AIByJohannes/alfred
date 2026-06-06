from __future__ import annotations

import asyncio
import base64
import html
import json
from pathlib import Path
from typing import Any

from shiny import App, reactive, render, ui

from scripts.chat import stream_chat
from scripts.common import get_sessions_root
from scripts.fs_agent import stream_filesystem_agent

# ======================== HELPERS ========================

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


# ======================== UI DEFINITION ========================

app_ui = ui.page_sidebar(
    # Left Sidebar Section
    ui.sidebar(
        ui.h2("A.L.F.R.E.D."),

        ui.input_action_button(
            "new_chat",
            "New Chat",
            class_="btn-primary-custom w-100",
            icon=ui.HTML('<i class="fas fa-comment"></i> '),
            style="margin-bottom: 0.5rem;"
        ),
        ui.input_action_button(
            "new_agent_chat",
            "New Agent Chat",
            class_="btn-agent-custom w-100",
            icon=ui.HTML('<i class="fas fa-robot"></i> ')
        ),

        ui.output_ui("agent_settings_ui"),

        ui.output_ui("artifacts_ui"),

        ui.div(
            ui.h4(
                "History",
                style="font-weight: 600; margin-bottom: 0.75rem; font-size: 0.95rem; color: #abb2bf; margin-top: 0 !important;"
            ),
            style="margin-top: 1rem;"
        ),
        ui.output_ui("history_ui"),

        width=300,
        class_="sidebar"
    ),

    # Main Content Section
    ui.div(
        # Top status indicator banner
        ui.output_ui("status_banner_ui"),

        # Message scroll container
        ui.div(
            ui.output_ui("messages_ui"),
            id="chat-container",
            class_="chat-container"
        ),

        # Input Footer & Toolbar
        ui.div(
            # Toolbar
            ui.div(
                ui.div(
                    ui.input_file(
                        "image_upload",
                        None,
                        button_label="📷 Image",
                        accept=[".png", ".jpg", ".jpeg"],
                        multiple=False
                    ),
                    class_="toolbar-file-upload"
                ),
                ui.div(
                    ui.input_file(
                        "audio_upload",
                        None,
                        button_label="🎤 Voice",
                        accept=[".wav", ".mp3", ".webm", ".m4a", ".ogg"],
                        multiple=False
                    ),
                    class_="toolbar-file-upload"
                ),
                ui.output_ui("pending_upload_ui"),
                ui.div(style="flex-grow: 1;"),
                ui.input_action_button(
                    "clear_chat",
                    "Clear",
                    class_="btn-secondary-custom",
                    icon=ui.HTML('<i class="fas fa-trash"></i> ')
                ),
                class_="toolbar-row"
            ),

            # Message input text bar
            ui.div(
                ui.input_text(
                    "prompt",
                    None,
                    placeholder="Message Alfred...",
                    width="100%",
                    autocomplete="off"
                ),
                ui.input_action_button("send", "Send", class_="btn-primary-custom"),
                class_="input-group-custom"
            ),
            class_="chat-footer"
        ),
        class_="main-layout"
    ),

    # Head & Stylesheet Injections
    ui.head_content(
        ui.HTML('<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">'),
        ui.tags.style(Path(__file__).parent.joinpath("style.css").read_text()),
        ui.tags.script("""
            // Dynamic scroll-to-bottom behavior for the chat history container
            const observer = new MutationObserver(() => {
                const el = document.getElementById("chat-container");
                if (el) {
                    el.scrollTop = el.scrollHeight;
                }
            });
            document.addEventListener("DOMContentLoaded", () => {
                const el = document.getElementById("chat-container");
                if (el) {
                    observer.observe(el, { childList: true, subtree: true });
                    el.scrollTop = el.scrollHeight;
                }

                // Allow submitting by pressing Enter key on the prompt input field
                document.addEventListener("keydown", (e) => {
                    if (e.key === "Enter" && e.target && e.target.id === "prompt") {
                        e.preventDefault();
                        const btn = document.getElementById("send");
                        if (btn) {
                            btn.click();
                        }
                    }
                });
            });
        """)
    ),

    window_title="Alfred Workbench",
    fillable=True,
)


# ======================== SERVER LOGIC ========================

def server(input, output, session):
    # Reactive states for tracking interactive conversations
    messages = reactive.Value([])
    session_id = reactive.Value(None)
    artifacts = reactive.Value([])
    status = reactive.Value("idle")
    status_detail = reactive.Value("Standing by.")
    resolved_backend = reactive.Value(None)
    pending_image = reactive.Value(None)
    pending_image_name = reactive.Value(None)
    running = reactive.Value(False)
    chat_mode = reactive.Value("chat")

    # Dynamically render Agent configuration card when in agent mode
    @output
    @render.ui
    def agent_settings_ui():
        if chat_mode() == "fs-agent":
            return ui.div(
                ui.input_text(
                    "cwd",
                    "Working Directory",
                    placeholder="/path/to/repo",
                    value=""
                ),
                ui.input_select(
                    "fs_backend",
                    "Backend Fallback",
                    choices={
                        "auto": "auto",
                        "alfred-cli": "alfred-cli",
                        "smolagents": "smolagents"
                    },
                    selected="auto"
                ),
                style="margin-top: 1.25rem;"
            )
        return None

    # Dynamically render list of artifacts generated in the active session
    @output
    @render.ui
    def artifacts_ui():
        arts = artifacts()
        if not arts:
            return None

        art_uis = []
        for art in arts:
            label = art.get("label", "artifact")
            path = art.get("path") or art.get("url") or "pending"
            art_uis.append(
                ui.div(
                    ui.span(f"📦 {label}", style="font-weight: 500;"),
                    ui.span(
                        Path(path).name if path != "pending" else "pending",
                        style="font-size: 0.75rem; color: #7f848e; word-break: break-all; "
                              "margin-top: 2px;"
                    ),
                    class_="artifact-card"
                )
            )
        return ui.div(
            ui.h4(
                "Artifacts",
                style="font-weight: 600; margin-bottom: 0.75rem; "
                      "font-size: 0.95rem; color: #abb2bf;"
            ),
            *art_uis,
            style="margin-top: 1.25rem;"
        )

    # Dynamic historical session listing with load interaction
    @output
    @render.ui
    def history_ui():
        sessions = get_sessions()
        if not sessions:
            return ui.p(
                "No sessions yet.",
                style="font-size: 0.85rem; color: #7f848e; font-style: italic;"
            )

        history_elements = []
        for s in sessions:
            lbl = s["prompt"][:40] or "Empty session"
            if len(s["prompt"]) > 40:
                lbl += "..."
            lbl += f"\n{s['mode']} • {s['timestamp']}"

            is_active = s["id"] == session_id()
            active_class = "active" if is_active else ""

            safe_id = json.dumps(s["id"])
            safe_lbl = html.escape(lbl)
            btn_html = ui.HTML(
                f'<button onclick="Shiny.setInputValue('
                f'\'selected_session\', {safe_id}, {{priority: \'event\'}})" '
                f'class="btn-history-item {active_class}">{safe_lbl}</button>'
            )
            history_elements.append(btn_html)

        return ui.div(*history_elements)

    # Dynamic session loader when clicking history items
    @reactive.effect
    @reactive.event(input.selected_session)
    def _load_selected_session():
        sid = input.selected_session()
        if sid:
            load_session_into_state_local(sid)

    def load_session_into_state_local(sid: str) -> None:
        session_dir = get_sessions_root() / sid
        if not session_dir.exists():
            return

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

        new_msgs = []
        new_artifacts = []

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

            new_msgs.append({"role": "user", "content": user_prompt, "image_base64": image_b64})
            new_msgs.append({"role": "assistant", "content": assistant_content, "status": "done"})

        loaded_mode = meta.get("mode", "chat")
        if loaded_mode == "inference":
            loaded_mode = "chat"
        chat_mode.set(loaded_mode)

        messages.set(new_msgs)
        artifacts.set(new_artifacts)
        session_id.set(sid)
        status.set("idle")
        mode_name = "Agent" if loaded_mode == "fs-agent" else "Chat"
        status_detail.set(f"{mode_name} session loaded.")
        resolved_backend.set(None)

    # Click handler for creating clean slate conversations (Chat mode)
    @reactive.effect
    @reactive.event(input.new_chat)
    def _handle_new_chat():
        chat_mode.set("chat")
        clear_state_for_new_session("Chat session ready.")

    # Click handler for creating clean slate conversations (Agent mode)
    @reactive.effect
    @reactive.event(input.new_agent_chat)
    def _handle_new_agent_chat():
        chat_mode.set("fs-agent")
        clear_state_for_new_session("Agent session ready.")

    def clear_state_for_new_session(msg: str):
        messages.set([])
        session_id.set(None)
        artifacts.set([])
        status.set("idle")
        status_detail.set(msg)
        resolved_backend.set(None)
        pending_image.set(None)
        pending_image_name.set(None)
        ui.update_text("prompt", value="")

    # Click handler for clearing conversation panel
    @reactive.effect
    @reactive.event(input.clear_chat)
    def _handle_clear_chat():
        messages.set([])
        session_id.set(None)
        artifacts.set([])
        status.set("idle")
        status_detail.set("Workbench cleared.")
        resolved_backend.set(None)
        pending_image.set(None)
        pending_image_name.set(None)
        ui.update_text("prompt", value="")

    # Upload handler for visual media (images)
    @reactive.effect
    @reactive.event(input.image_upload)
    def _handle_image_upload():
        uploaded = input.image_upload()
        if uploaded:
            path = uploaded[0]["datapath"]
            name = uploaded[0]["name"]
            try:
                with open(path, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode("utf-8")
                pending_image.set(b64)
                pending_image_name.set(name)
                ui.notification_show(f"Image ready: {name}", type="message")
            except Exception as e:
                ui.notification_show(f"Failed to read image: {e}", type="error")

    # Upload handler for audio voice files
    @reactive.effect
    @reactive.event(input.audio_upload)
    async def _handle_audio_upload():
        uploaded = input.audio_upload()
        if uploaded:
            path = uploaded[0]["datapath"]
            name = uploaded[0]["name"]
            status.set("running")
            status_detail.set("Transcribing audio...")

            try:
                from transcription.service import get_transcription_service
                service = get_transcription_service()

                with open(path, "rb") as f:
                    audio_bytes = f.read()

                loop = asyncio.get_running_loop()
                result = await loop.run_in_executor(
                    None,
                    lambda: service.transcribe_file(
                        audio_data=audio_bytes,
                        filename=name or "speech.webm"
                    )
                )

                text = result.text
                if text.strip():
                    ui.update_text("prompt", value=text)
                    ui.notification_show("Audio transcribed!", type="message")
                    status.set("idle")
                    status_detail.set("Transcription ready.")
                else:
                    ui.notification_show("Audio transcriber returned empty text.", type="warning")
                    status.set("idle")
                    status_detail.set("Audio transcription empty.")
            except Exception as e:
                ui.notification_show(f"Transcription failed: {e}", type="error")
                status.set("error")
                status_detail.set(f"Transcription error: {e}")

    # Display indicator for pending image upload in toolbar
    @output
    @render.ui
    def pending_upload_ui():
        if pending_image():
            return ui.span(
                f"📷 {pending_image_name() or 'Image ready'}",
                style="color: #98c379; font-size: 0.85rem; padding: 0.25rem 0.5rem; "
                      "background-color: rgba(152, 195, 121, 0.1); border-radius: 4px; "
                      "border: 1px solid rgba(152, 195, 121, 0.3);"
            )
        return None

    # Render dynamic operational status banner
    @output
    @render.ui
    def status_banner_ui():
        st_val = status()
        dt_val = status_detail()

        if st_val == "idle":
            icon = ui.HTML('<i class="fas fa-info-circle"></i> ')
            cls = "status-idle"
        elif st_val == "running":
            icon = ui.HTML('<i class="fas fa-spinner fa-spin"></i> ')
            cls = "status-running"
        elif st_val == "done":
            icon = ui.HTML('<i class="fas fa-check-circle"></i> ')
            cls = "status-done"
        else:  # error
            icon = ui.HTML('<i class="fas fa-exclamation-triangle"></i> ')
            cls = "status-error"

        return ui.div(
            icon,
            ui.span(dt_val, id="status-indicator"),
            class_=f"status-banner {cls}"
        )

    # Render chat bubbles reactively
    @output
    @render.ui
    def messages_ui():
        msgs = messages()
        if not msgs:
            # Standard custom welcome screen for blank chats
            return ui.div(
                ui.div(
                    ui.div("A", class_="message-avatar"),
                    ui.div(
                        ui.markdown(
                            "**Alfred Standing By.**\n\n"
                            "Greetings. I am Alfred, your Algorithmic Life-form Feigning "
                            "Real Emotional Depth.\n\n"
                            "I can assist you in Chat mode or run terminal instructions in "
                            "Agent mode. Click **New Chat** or **New Agent Chat** on the left to start."
                        ),
                        class_="message-bubble"
                    ),
                    class_="message-row assistant"
                ),
                style="display: flex; flex-direction: column; gap: 1rem;"
            )

        msg_rows = []
        for msg in msgs:
            role = msg["role"]
            content = msg.get("content", "")
            img_b64 = msg.get("image_base64")

            elements = []
            if img_b64:
                elements.append(
                    ui.img(
                        src=f"data:image/png;base64,{img_b64}",
                        class_="uploaded-image"
                    )
                )
            if content:
                elements.append(ui.markdown(content))

            if not content and not img_b64:
                elements.append(
                    ui.span(
                        "Thinking...",
                        class_="text-muted",
                        style="font-style: italic;"
                    )
                )

            bubble = ui.div(*elements, class_="message-bubble")

            if role == "user":
                avatar = ui.div("U", class_="message-avatar")
                row = ui.div(bubble, avatar, class_="message-row user")
            else:
                avatar = ui.div("A", class_="message-avatar")
                row = ui.div(avatar, bubble, class_="message-row assistant")

            msg_rows.append(row)

        return ui.div(*msg_rows, style="display: flex; flex-direction: column; gap: 1rem;")

    # Click handler for submitting chats & launching background execution tasks
    @reactive.effect
    @reactive.event(input.send)
    async def _handle_send():
        # Prevent parallel runs
        if running():
            return

        prompt_text = input.prompt()
        if not prompt_text or not prompt_text.strip():
            return

        # Clear text input field instantly
        ui.update_text("prompt", value="")

        # Lock states
        running.set(True)
        status.set("running")
        status_detail.set("Alfred is processing your query...")

        # Obtain uploaded image context
        img_b64 = pending_image()
        pending_image.set(None)
        pending_image_name.set(None)

        # Add user query message
        current_msgs = list(messages())
        user_msg = {"role": "user", "content": prompt_text}
        if img_b64:
            user_msg["image_base64"] = img_b64
        messages.set(current_msgs + [user_msg])

        # Append assistant streaming block placeholder
        current_msgs = messages()
        assistant_msg = {"role": "assistant", "content": "", "status": "running"}
        messages.set(current_msgs + [assistant_msg])

        # Helper callback to stream text updates into the reactive message block
        def update_assistant_content(text_delta: str):
            msgs = list(messages())
            if msgs:
                msgs[-1]["content"] += text_delta
                messages.set(msgs)

        run_mode = chat_mode()
        run_session_id = session_id()

        # Read agent configurations safely
        run_cwd = ""
        run_backend = "auto"
        if run_mode == "fs-agent":
            try:
                run_cwd = input.cwd()
            except Exception:
                pass
            try:
                run_backend = input.fs_backend()
            except Exception:
                pass

        # Select target generator
        if run_mode == "chat":
            gen = stream_chat(prompt_text, session_id=run_session_id, image_base64=img_b64)
        else:
            gen = stream_filesystem_agent(
                prompt_text,
                cwd=run_cwd or None,
                session_id=run_session_id,
                backend=run_backend,
            )

        content = ""
        new_artifacts = []
        new_session_id = run_session_id
        res_backend = resolved_backend()

        try:
            async for event in gen:
                et = event.get("type", "")
                if et == "meta":
                    new_session_id = event.get("session_id", new_session_id)
                    res_backend = event.get("backend", res_backend)
                    if new_session_id:
                        session_id.set(new_session_id)
                    if res_backend:
                        resolved_backend.set(res_backend)

                elif et == "delta":
                    text = read_text(event)
                    if text:
                        content += text
                        update_assistant_content(text)

                elif et == "artifact":
                    new_artifacts.append(event)
                    artifacts.set(artifacts() + [event])

                elif et == "done":
                    msg = event.get("result") or event.get("message") or "Run complete."
                    status.set("done")
                    status_detail.set(msg)
                    break

                elif et == "error":
                    msg = event.get("message") or "The run failed."
                    status.set("error")
                    status_detail.set(msg)
                    break
            else:
                status.set("done")
                status_detail.set("Run complete.")

        except Exception as e:
            status.set("error")
            status_detail.set(f"Error: {e}")

        finally:
            msgs = list(messages())
            if msgs:
                msgs[-1]["status"] = status()
            messages.set(msgs)
            running.set(False)


# ======================== APPLICATION MOUNT ========================

app = App(app_ui, server)
