# Alfred Workbench

Gradio workbench for the local Alfred app.

## Development

```bash
just run
# or manually: uv run --active python app/app.py
```

The Gradio app imports and calls Python wrappers directly (no API proxy needed for the UI).

## Configuration

- Gradio runs on port 8501 by default.
- Theme: `d8ahazard/rd_blue` from the Gradio theme hub.
- Run with live reload: `gradio app/app.py --watch-dirs app`.
