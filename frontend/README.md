# Alfred Workbench

Single-page React + Vite frontend for the local Alfred FastAPI bridge.

## Development

```bash
npm install
npm run dev
```

The app expects the FastAPI server on `http://localhost:8000` by default. Override with:

```bash
VITE_API_BASE_URL=http://localhost:8000 npm run dev
```

## Build

```bash
npm run build
```

