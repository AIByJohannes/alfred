# Alfred Gradio Web Interface UX Redesign

**Status:** Proposed  
**Owner:** Alfred project  
**Last updated:** 2026-07-10

## 1. Decision summary

Rebuild the Gradio workbench around a stable, chat-first application shell rather than continuing to patch the current layout with increasingly specific CSS.

The redesigned interface will:

- use one collapsible navigation sidebar for sessions;
- move working-directory and backend controls into a secondary settings surface;
- replace the separate text, image, audio-upload, and microphone controls with one multimodal composer;
- expose clear run states and a working stop action;
- show artifacts as usable links or files instead of static labels;
- provide a true mobile drawer rather than a full-width sidebar column;
- reduce coupling to undocumented Gradio DOM structure;
- split UI, state, event, and presentation logic into focused modules;
- pin and test one Gradio minor version before implementation.

This remains a local-first Gradio application. A custom JavaScript frontend is not required for this redesign.

## 2. Context

The current workbench successfully provides streamed agent output, session history, image input, voice transcription, backend selection, working-directory selection, and artifact reporting. The UX is nevertheless fragile and difficult to evolve.

The current implementation is concentrated in:

- `app/app.py`: UI construction, state, rendering helpers, filesystem reads, event handlers, and streaming orchestration;
- `app/style.css`: layout and visual behavior implemented through extensive overrides of Gradio-generated markup.

Recent changes improved the visual design, but the interface is now dependent on internal selectors such as `.message-row`, `[data-testid="bot"]`, `.wrap`, `.form`, and nested `:has(...)` rules. This makes normal Gradio upgrades capable of breaking layout or interaction without a Python error.

## 3. Current-state UX diagnosis

### 3.1 Run status exists in state but is not visible

`status`, `status_detail`, and `_render_status()` exist, but no visible status component is connected to them. Users therefore receive weak feedback about whether Alfred is idle, transcribing, running, done, or failed.

### 3.2 The composer is fragmented

Text entry, image upload, audio-file upload, microphone recording, pending-image display, and send are separate components spread across two rows. This creates several problems:

- the user must understand the distinction between audio upload and microphone recording;
- attachment state is displayed away from the control that created it;
- there is no clear remove/replace action for a pending image;
- microphone UI is styled as a fixed-width floating popover;
- the layout becomes crowded and wraps poorly on narrow screens.

### 3.3 Mobile navigation is not a drawer

At small widths the sidebar becomes 100% wide, but it remains part of the same row layout. It does not behave like a modal drawer with an overlay, automatic closing after navigation, or a persistent way to return to chat.

The voice popover also has a fixed minimum width that can exceed a phone viewport.

### 3.4 Primary and destructive actions are unclear

`New Chat` and `Clear` currently reset nearly the same state. The distinction is unclear, and neither action communicates whether saved session history is affected.

The target design should have:

- one obvious **New chat** action;
- a separate, less prominent **Delete conversation** action only if actual persisted deletion is implemented;
- confirmation before persisted deletion.

### 3.5 Technical settings dominate navigation

Working directory and backend fallback are permanently visible above session history. They are important power-user controls, but not primary navigation. Their placement makes the application feel like a debug panel rather than a focused assistant.

### 3.6 Session history is visually and semantically weak

History is represented as a styled `Radio` component with hidden radio controls. It provides selection, but not the expected conversation-management behavior:

- timestamps are derived from session IDs rather than formatted for humans;
- long titles have weak truncation and no tooltip;
- no empty, loading, or malformed-session state is shown;
- no rename, delete, or search behavior exists;
- choices are rebuilt repeatedly during streaming.

### 3.7 Artifacts are not actionable

Artifact cards show a label and basename but do not reliably let the user open, download, copy, or reveal the artifact. Paths are rendered through manually constructed HTML.

### 3.8 Streaming updates cause unnecessary UI work

The send generator rebuilds history choices on metadata, every text delta, artifact events, completion, and errors. This can cause avoidable rerenders or flicker and makes the callback contract difficult to reason about.

### 3.9 Accessibility is incidental

Several controls use emoji or symbols as their only visible label. Hidden native controls and aggressive CSS overrides can interfere with focus indicators, keyboard navigation, and screen-reader naming.

### 3.10 Local-first behavior depends on an external font request

`style.css` imports Google Fonts. The interface should remain complete and visually stable without internet access and should not make an unnecessary third-party request.

## 4. Goals

### 4.1 Product goals

1. Make sending a request the visually dominant action.
2. Make system state understandable without inspecting logs.
3. Make session navigation fast on desktop and usable on mobile.
4. Preserve all current capabilities while reducing visible complexity.
5. Make the UI resilient to supported Gradio upgrades.
6. Keep the application local-first and operable without external frontend assets.

### 4.2 Engineering goals

1. Separate filesystem/session logic from Gradio component construction.
2. Replace high-arity callback tuples with small typed view-state transformations where practical.
3. Refresh history only when session metadata changes.
4. Avoid manual HTML for user-controlled strings unless values are escaped.
5. Add behavior-focused tests instead of source-text-only UI tests.
6. Establish a visual smoke-test workflow for desktop and mobile widths.

## 5. Non-goals

This redesign does not include:

- replacing Gradio with React, Next.js, or another frontend framework;
- multi-user authentication or remote hosting hardening;
- redesigning the Alfred CLI or agent protocol;
- changing the session storage format unless needed for titles or timestamps;
- adding multiple simultaneous conversations in separate tabs;
- building a full file browser;
- adding model-provider configuration to the main chat screen.

## 6. Design principles

### Chat first

The transcript and composer receive most of the viewport. Navigation and settings must not compete with the current task.

### Progressive disclosure

Common actions stay visible. Technical controls move behind a clear settings action and retain sensible defaults.

### One state, one explanation

Idle, submitting, running, stopping, complete, and error states each have a visible and consistent representation.

### Stable components before CSS tricks

Prefer documented Gradio layout and input components. Custom CSS should style Alfred-owned `elem_id` and `elem_classes`, not reverse-engineer deep generated markup.

### Mobile is a distinct layout mode

The mobile sidebar is an overlay drawer. The composer is a single surface. Touch targets remain at least 44 by 44 CSS pixels.

### Local by default

Use a system font stack and local assets. Do not depend on Google Fonts or another external CDN.

## 7. Information architecture

### 7.1 Primary surfaces

1. **Session sidebar**
   - Alfred identity
   - New chat
   - Session history
   - Settings button

2. **Chat workspace**
   - compact header
   - transcript
   - run/error status
   - multimodal composer

3. **Settings panel**
   - working directory
   - backend selection
   - resolved backend and runtime diagnostics

4. **Artifact surface**
   - inline artifact message when created
   - optional artifact drawer/list for the current session

### 7.2 Desktop wireframe

```text
┌──────────────────────┬──────────────────────────────────────────────────┐
│ A.L.F.R.E.D.         │ Alfred                              [Artifacts]  │
│ [+ New chat]         ├──────────────────────────────────────────────────┤
│                      │                                                  │
│ Today                │ User message                                     │
│  Current session     │                                                  │
│  Another session     │ Alfred streamed response                         │
│                      │  └─ generated artifact.pdf [Open] [Download]     │
│ Previous             │                                                  │
│  Older session       │                                                  │
│                      │                                                  │
│                      ├──────────────────────────────────────────────────┤
│ [Settings]           │ [attachment chips]                               │
│                      │ [ Ask Alfred…                         ][Send/Stop] │
└──────────────────────┴──────────────────────────────────────────────────┘
```

### 7.3 Mobile wireframe

```text
┌──────────────────────────────────────┐
│ [☰] Alfred                 [Artifacts]│
├──────────────────────────────────────┤
│                                      │
│ User message                         │
│                                      │
│ Alfred response                      │
│                                      │
├──────────────────────────────────────┤
│ [attachment chip]                    │
│ [ Ask Alfred…               ][Send]  │
└──────────────────────────────────────┘
```

Opening the menu displays session navigation as an overlay drawer. Selecting a session closes the drawer and returns focus to the transcript.

## 8. Detailed interaction design

### 8.1 Application shell

Use a documented collapsible sidebar component when supported by the pinned Gradio version. Otherwise retain a `Column`, but implement a deliberate desktop sidebar and mobile overlay rather than relying on row wrapping.

Desktop behavior:

- default open at widths of 1024 px and above;
- collapsible through a labelled menu button;
- width approximately 280 px;
- transcript width grows with the viewport, with a readable content maximum around 900–1000 px.

Mobile behavior:

- default closed below 768 px;
- overlays the chat instead of resizing it;
- includes a scrim and closes on Escape, scrim click, or session selection;
- traps focus while open if implemented with custom JavaScript.

### 8.2 Header

The header contains:

- a menu button with accessible label `Open navigation` or `Close navigation`;
- current session title, or `New chat`;
- a working-directory chip only when a directory is set;
- an artifacts button with count when artifacts exist.

Do not show a decorative page title such as `Alfred Workspace` when the current session title is more useful.

### 8.3 Empty state

The empty transcript should show:

- Alfred’s name;
- one short identity line in Alfred’s established voice;
- a direct prompt to start typing;
- optionally two or three concise example tasks.

It should not repeat configuration instructions that belong in settings.

### 8.4 Transcript

Messages use the native `gr.Chatbot(type="messages")` data model.

Behavior:

- user messages align right;
- assistant messages align left;
- code blocks remain readable and horizontally scrollable;
- copy actions remain available but are not forced permanently visible;
- the transcript autoscrolls only while the user is already near the bottom;
- scrolling upward pauses forced autoscroll;
- errors appear as assistant-system messages with recovery actions, not only as global banners.

The design should avoid selectors tied to undocumented message-row internals. If exact bubble styling requires deep internal selectors, reduce customization rather than expanding selector coverage.

### 8.5 Multimodal composer

Preferred component: `gr.MultimodalTextbox` with upload and microphone sources, provided the pinned Gradio version supports the required behavior.

Initial supported inputs:

- text;
- one image;
- microphone recording;
- uploaded audio for transcription.

The composer must:

- show selected attachments as removable chips or previews inside the composer surface;
- keep the text draft after attachment selection;
- disable submit when there is neither text nor an attachment;
- submit on Enter and insert a newline on Shift+Enter;
- become read-only while the request is being accepted;
- show a stop button while streaming;
- restore focus after completion, cancellation, or recoverable failure.

If `MultimodalTextbox` cannot distinguish image input from audio-to-transcribe cleanly in the pinned version, keep a single attachment menu adjacent to the textbox rather than separate permanent toolbar controls.

### 8.6 Run-state model

Use these explicit states:

| State | Visible behavior | Allowed actions |
|---|---|---|
| `idle` | Composer enabled; no status noise | Send, attach, navigate |
| `submitting` | User message appears immediately; subtle pending indicator | Stop if request started |
| `running` | Assistant message streams; send becomes Stop | Stop, copy prior messages |
| `stopping` | Stop disabled; label says `Stopping…` | Navigate only after safe cancellation |
| `done` | Final assistant message; composer re-enabled | Send next message |
| `error` | Error message with Retry and Copy details | Retry, edit draft, navigate |

A compact status line may show transcription or backend setup work, but normal token streaming should be represented primarily in the current assistant message.

### 8.7 Stop behavior

Stopping must cancel both layers:

1. the Gradio generator/event;
2. the underlying Alfred subprocess or agent task.

Cancelling only frontend iteration while leaving the process running is not acceptable.

The implementation should retain the event handle returned by `.submit()` or `.click()` and wire it to Gradio cancellation. The Python bridge must propagate cancellation to `stream_filesystem_agent` and terminate the subprocess cleanly.

### 8.8 Session history

The sidebar history should be a simple conversation list, grouped by human-readable time:

- Today
- Yesterday
- Previous 7 days
- Older

Each row shows:

- title derived from the first user prompt;
- formatted local date/time as secondary text;
- selected state;
- optional overflow menu in a later phase.

Behavior:

- opening a session loads the transcript and current artifacts;
- mobile navigation closes after selection;
- malformed session files appear as unavailable rather than disappearing silently;
- history refreshes on initial load, new session creation, title change, deletion, or completed first turn—not on every streamed token.

Phase-one history management may remain read-only. Rename and delete can be phase two, but the UI must not imply those capabilities before persistence is implemented.

### 8.9 New chat

`New chat` creates a clean in-memory draft state without deleting persisted sessions.

If the current conversation contains an unsent draft or attachment, preserve the draft in browser state or ask for confirmation before discarding it.

Remove the current `Clear` action from the primary toolbar. If a transcript-only reset remains useful for development, place it in an explicitly labelled developer menu.

### 8.10 Settings

Settings are secondary and should open in a right-side panel, modal, accordion, or dedicated sidebar section.

Fields:

- **Working directory**
  - text input initially;
  - normalized path preview;
  - validation state: valid, missing, inaccessible;
  - persisted locally for the next browser session when appropriate.

- **Backend**
  - user-facing values: `Automatic`, `Alfred CLI`, `Smolagents fallback`;
  - default `Automatic`;
  - concise descriptions;
  - resolved backend shown as diagnostics after a run.

- **Diagnostics**
  - session ID;
  - resolved backend;
  - runtime root;
  - copy button for troubleshooting information.

Do not label the main field `Backend Fallback`; it is selecting execution policy, not only a fallback.

### 8.11 Voice transcription

Voice is an input method, not a separate workspace.

Behavior:

- microphone recording begins from the composer;
- recording state is visually obvious;
- completion transcribes into the current draft without erasing existing text;
- append transcribed text at the cursor or after existing text with appropriate spacing;
- transcription errors appear near the composer and leave the draft intact;
- uploaded audio follows the same transcription path.

### 8.12 Image attachments

Phase one may retain one image per message to match the current backend contract.

Behavior:

- preview thumbnail plus filename;
- remove action before send;
- attachment clears only after the request is accepted;
- loading an old session displays the persisted image without embedding unnecessarily large base64 data when a served file path is available.

### 8.13 Artifacts

Artifacts should be represented by a typed view model:

```python
@dataclass
class ArtifactView:
    label: str
    path: str | None
    url: str | None
    kind: str | None
    exists: bool
```

Display behavior:

- insert an inline artifact card at the point it is emitted;
- provide `Open`, `Download`, or `Reveal path` according to artifact type and environment;
- show missing artifacts explicitly;
- provide a current-session artifact list from the header;
- escape labels and paths if HTML rendering remains necessary.

Prefer Gradio file/download components over manually concatenated HTML.

### 8.14 Errors and recovery

User-facing errors must answer three questions:

1. What failed?
2. Was the current draft or session preserved?
3. What can the user do next?

Error categories:

- missing or invalid working directory;
- backend unavailable;
- authentication/provider failure;
- transcription failure;
- malformed stored session;
- unexpected application error.

Unexpected errors should have a short message plus expandable technical details. Never replace the current transcript with an error-only screen.

## 9. State design

Replace loosely related `gr.State` values with a small documented state model.

Suggested logical model:

```python
@dataclass
class ComposerState:
    text: str = ""
    attachments: list[PendingAttachment] = field(default_factory=list)
    transcription_state: str = "idle"

@dataclass
class SessionViewState:
    session_id: str | None = None
    title: str = "New chat"
    messages: list[dict] = field(default_factory=list)
    artifacts: list[ArtifactView] = field(default_factory=list)

@dataclass
class RunViewState:
    phase: Literal[
        "idle", "submitting", "running", "stopping", "done", "error"
    ] = "idle"
    detail: str | None = None
    resolved_backend: str | None = None
```

Gradio components may still require separate outputs, but handlers should transform these logical models through focused presenter functions rather than manually assembling large tuples throughout the streaming loop.

## 10. Proposed code organization

```text
app/
├── app.py            # compose Blocks, wire events, launch
├── components.py     # sidebar, header, transcript, composer, settings
├── events.py         # submit, stop, load session, new chat, transcription
├── presenters.py     # state -> Gradio update/view models
├── sessions.py       # session discovery and loading for UI use
├── models.py         # typed UI state and artifact models
├── style.css         # tokens and shallow Alfred-owned selectors
└── README.md
```

`app.py` should remain the launchable entry point but should no longer contain filesystem parsing, HTML construction, all event logic, and all components in one file.

## 11. Gradio component strategy

Preferred documented components:

- `gr.Blocks` for the application shell;
- `gr.Sidebar` for documented collapsible navigation when available in the pinned version;
- `gr.Chatbot(type="messages")` for the transcript;
- `gr.MultimodalTextbox` for unified text, upload, microphone, submit, and stop behavior when compatible with the backend contract;
- `gr.File` or download-capable components for artifacts;
- `gr.Accordion` or a secondary sidebar/modal pattern for settings;
- `gr.State` only for browser-session view state, not as a substitute for typed application models.

Official references:

- [Gradio Sidebar](https://www.gradio.app/docs/gradio/sidebar)
- [Gradio MultimodalTextbox](https://www.gradio.app/docs/gradio/multimodaltextbox)
- [Creating a chatbot with Gradio](https://www.gradio.app/guides/creating-a-chatbot-fast)

Before implementation, pin a single tested Gradio minor version in `pyproject.toml` and refresh `uv.lock`. The current broad range allows materially different DOM and component behavior.

## 12. CSS strategy

### 12.1 Tokens

Keep a small token set:

```css
:root {
  --alfred-bg: #171717;
  --alfred-surface: #212121;
  --alfred-surface-raised: #2a2a2a;
  --alfred-border: #3a3a3a;
  --alfred-text: #f1f1f1;
  --alfred-text-muted: #a3a3a3;
  --alfred-accent: #61afef;
  --alfred-danger: #e06c75;
  --alfred-success: #98c379;
  --alfred-radius: 12px;
}
```

### 12.2 Selector rules

Allowed:

- Alfred-owned IDs and classes set through `elem_id` and `elem_classes`;
- shallow styling of documented component roots;
- standard responsive media queries.

Avoid:

- selectors that depend on generated nesting depth;
- broad `.wrap`, `.form`, or `.gr-button` overrides outside an Alfred-owned root;
- styling based on undocumented `data-testid` values;
- permanently forcing hidden Gradio controls to display;
- fixed-width popovers that exceed narrow viewports.

### 12.3 Fonts

Remove the Google Fonts import. Use:

```css
font-family: Inter, ui-sans-serif, system-ui, -apple-system,
  BlinkMacSystemFont, "Segoe UI", sans-serif;
```

The interface must remain complete offline.

## 13. Responsive requirements

### Desktop: 1024 px and above

- sidebar open by default;
- transcript centered with readable maximum width;
- composer fixed to bottom of workspace;
- settings may use a right-side panel.

### Tablet: 768–1023 px

- sidebar collapsed by default or reduced width;
- no fixed-width floating controls;
- artifacts open in an overlay/panel.

### Mobile: below 768 px

- navigation is an overlay drawer;
- header remains one line where possible;
- composer uses full width with safe-area padding;
- all primary touch targets are at least 44 px;
- message bubbles may use up to 94% width;
- no horizontal page scrolling at 320 px viewport width;
- virtual keyboard must not cover the composer.

## 14. Accessibility requirements

- Every icon-only button has an accessible name and tooltip.
- Visible focus rings are preserved for keyboard users.
- Sidebar, transcript, composer, and settings are reachable in logical tab order.
- Status changes use an appropriate live region without announcing every token.
- Color is never the only indicator of running, success, or failure.
- Text and interactive controls meet WCAG 2.2 AA contrast targets.
- Motion respects `prefers-reduced-motion`.
- Native controls should not be hidden unless equivalent semantics and keyboard behavior are retained.

## 15. Performance requirements

- Do not rebuild session history on each token delta.
- Throttle or rely on Gradio’s normal stream cadence rather than issuing redundant component updates.
- Avoid re-encoding persisted images to base64 when a safe file-serving mechanism is available.
- Load full session contents only for the selected session.
- Keep history discovery metadata-only.
- Avoid duplicate synchronization paths between `messages` state and `chatbot` unless one is demonstrably necessary.

## 16. Security and privacy requirements

- Escape artifact labels, filenames, paths, prompts, and error strings before including them in HTML.
- Prefer component APIs over raw HTML rendering.
- Do not expose arbitrary local files through download links without confirming they belong to the current session or approved working directory.
- Do not send font, analytics, or UI asset requests to third parties.
- Keep internal callback APIs private and API documentation disabled unless intentionally exposed.

## 17. Testing strategy

### 17.1 Unit tests

Test pure functions for:

- session title and timestamp formatting;
- session grouping;
- malformed session handling;
- run-state transitions;
- attachment normalization;
- artifact view-model construction;
- path validation and escaping.

### 17.2 Component/contract tests

Assert behavior and component availability rather than searching source text for variable names.

Examples:

- app constructs successfully with the pinned Gradio version;
- new chat clears active view state but does not delete persisted sessions;
- loading history updates transcript and artifacts;
- invalid working directory blocks execution with a visible error;
- image removal preserves text draft;
- transcript survives transcription failure;
- stop invokes task cancellation;
- session history is not refreshed for each delta.

### 17.3 End-to-end smoke tests

Use Playwright or equivalent browser automation for:

- desktop send and streaming;
- mobile menu open/select/close;
- attachment add/remove/send;
- microphone permission-denied path;
- stop during generation;
- error and retry;
- keyboard-only navigation;
- viewport widths of 320, 768, 1024, and 1440 px.

Capture screenshots for a small set of stable states to detect major layout regressions. Avoid brittle pixel-perfect assertions for token-streaming content.

## 18. Migration plan

### Phase 0 — Stabilize dependencies

- identify the exact Gradio version currently resolved in `uv.lock`;
- choose and pin one supported minor version;
- confirm support for `Sidebar`, `MultimodalTextbox`, submit/stop controls, and required event cancellation;
- update stale Gradio theme documentation in `app/README.md`.

### Phase 1 — Extract state and session logic

- create typed UI models;
- move session discovery/loading out of `app.py`;
- add formatting and malformed-session tests;
- preserve existing visual UI during extraction.

### Phase 2 — Replace the application shell

- implement documented sidebar behavior;
- add mobile drawer behavior;
- replace header title with session context;
- remove permanent technical settings from navigation.

### Phase 3 — Replace the composer

- introduce the unified multimodal composer;
- support removable attachment preview;
- unify uploaded-audio and microphone transcription behavior;
- remove the floating audio component and toolbar row.

### Phase 4 — Implement run lifecycle

- add visible run-state transitions;
- add stop propagation to the underlying process;
- add recoverable error messages and retry;
- refresh history only at defined lifecycle points.

### Phase 5 — Make artifacts actionable

- introduce artifact view models;
- add open/download/reveal behavior;
- remove raw artifact HTML where possible.

### Phase 6 — CSS and accessibility cleanup

- remove external fonts;
- replace deep selectors with Alfred-owned roots;
- test focus order, contrast, live regions, reduced motion, and phone widths.

### Phase 7 — Remove obsolete code

Remove:

- `_render_status()` if replaced by components, or connect it deliberately;
- duplicate `Clear` behavior;
- separate permanent audio toolbar controls;
- redundant chatbot synchronization callbacks;
- stale selectors and comments tied to old Gradio DOM;
- source-text tests that no longer represent user behavior.

## 19. Acceptance criteria

The redesign is complete when all of the following are true:

1. A new user can send a text request without opening settings.
2. Image and voice input are discoverable from the composer.
3. An attachment can be previewed and removed before sending.
4. Running, stopping, completed, and error states are visible.
5. Stop terminates the underlying Alfred task, not only the UI stream.
6. New chat does not delete persisted sessions.
7. Session history does not rerender on each token.
8. Selecting a session on mobile closes the navigation drawer.
9. The app has no horizontal scrolling at a 320 px viewport.
10. Artifacts can be opened or downloaded when available.
11. The interface works without loading external fonts or assets.
12. Icon-only controls have accessible names and keyboard focus states.
13. User-controlled strings are not inserted into unescaped HTML.
14. The UI works against one pinned, tested Gradio minor version.
15. `just check` passes, including new behavior-focused tests.

## 20. Open implementation decisions

The following should be resolved during Phase 0, not left implicit during UI implementation:

1. Which exact Gradio minor version is the supported baseline?
2. Does that version’s `MultimodalTextbox` provide the required attachment preview and stop behavior?
3. Can Gradio cancellation reliably propagate through the current async generator into the subprocess bridge?
4. Should working-directory selection persist globally, per browser, or per session?
5. Should artifacts open through Gradio file serving, the operating system, or both?
6. Is persisted session deletion in scope for the first redesign release?

The default answer for uncertain features should be the simplest behavior that preserves local-first operation and avoids custom frontend code.