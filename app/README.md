# Alfred Workbench

Gradio workbench for the local Alfred app.

## Development

```bash
just run
# or manually: uv run --active python app/app.py
```

The Gradio app imports and calls Python wrappers directly; no API proxy is needed for the UI.

## Configuration

- Gradio runs on port 8501 by default.
- Uses `gr.themes.Monochrome()` plus `app/style.css`.
- Alfred is dark-first: the app sets the documented `?__theme=dark` parameter on
  first load. Removing that parameter (`head` in `app/app.py`) falls back to the
  system light/dark preference.
- Run with live reload: `gradio app/app.py --watch-dirs app`.

## Layout model

The workbench is a single-viewport, chat-first shell:

- One collapsible `gr.Sidebar` holds New Chat, workspace selection, session
  history, and a collapsed **Settings** accordion (working directory, backend,
  new workspace, reset transcript).
- The main column owns the remaining height. Only the transcript scrolls; the
  composer is always visible, including on short windows.
- Voice input (microphone recording and audio upload) lives in a collapsed
  accordion in normal layout flow. It must never float over the transcript.
- Attachments and submission use the native `gr.MultimodalTextbox`.
- Run state appears in a compact status line above the composer and stays hidden
  while idle.

## Styling rules

- Style Alfred-owned `elem_id` / `elem_classes` and use Gradio theme variables
  where possible.
- Do not target internal message markup (`.message-row`, `.user`, `.bot`,
  `[data-testid=...]`, deep `.wrap` / `.form` chains).
- No external fonts, CDNs, or analytics requests.
- Keep `app/style.css` free of fixed-width floating controls.

## Tests

`just test` covers session/workspace behaviour, HTML escaping, status states,
draft-preserving transcription, and the layout invariants (voice controls in
flow, no external fonts). Browser-level checks are manual: verify empty,
restored, streaming, and error states at roughly 1440×900, 1280×720, 1024×600,
and a narrow viewport.

## Historical design notes

[`docs/gradio-web-interface-design.md`](../docs/gradio-web-interface-design.md)
records the larger original UX proposal. The implemented change is deliberately
smaller: native Gradio components, a shallow stylesheet, and no module split.
