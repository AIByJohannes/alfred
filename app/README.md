# Alfred Workbench

PyShiny workbench for the local Alfred app.

## Development

```bash
just run
# or manually: uv run shiny run app/app.py --port 8501
```

The PyShiny app imports and calls Python wrappers directly (no API proxy needed for the UI).

## Configuration

- PyShiny runs on port 8501 by default.

## Compatibility

The workbench targets **Shiny ≥1.6**. If `page_sidebar` fails with an `HTMLDependency`
type error, verify that `ui.head_content(...)` is passed as a child argument (not the
`header=` keyword), which was removed in Shiny 1.6.
