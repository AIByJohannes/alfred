# Alfred Workbench

PyShiny frontend for the local Alfred FastAPI bridge.

## Development

```bash
uv run shiny run frontend/app.py --port 8501
```

The PyShiny app imports and calls Python wrappers directly (no API proxy needed for the UI).

## Configuration

- PyShiny runs on port 8501 by default.
- FastAPI (if running separately) serves on port 8000.
