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
- The current interface uses `gr.themes.Monochrome()` plus `app/style.css`.
- Run with live reload: `gradio app/app.py --watch-dirs app`.

## UX redesign

See [`docs/gradio-web-interface-design.md`](../docs/gradio-web-interface-design.md) for the proposed chat-first redesign, state model, component strategy, migration plan, and acceptance criteria.
