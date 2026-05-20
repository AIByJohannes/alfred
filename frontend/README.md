# Alfred Workbench

Streamlit frontend for the local Alfred FastAPI bridge.

## Development

```bash
uv run streamlit run frontend/app.py --server.port 8501
```

The Streamlit app imports and calls Python wrappers directly (no API proxy needed for the UI).

## Configuration

- Streamlit runs on port 8501 by default.
- FastAPI (if running separately) serves on port 8000.
