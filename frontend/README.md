# Alfred Workbench

Single-page React + Vite frontend for the local Alfred FastAPI bridge.

## Development

```bash
npm install
npm run dev
```

The Vite dev server proxies `/api` and `/health` to FastAPI at `http://127.0.0.1:8000`.
No environment variables are needed for local development.

Override the API base URL (rare, only for non-standard setups):

```bash
VITE_API_BASE_URL=http://localhost:8000 npm run dev
```

## Build

```bash
npm run build
```

The built assets are in `dist/`. In production, FastAPI serves these from the same origin as the API.

## Configuration

- `VITE_API_BASE_URL`: Optional override for the API base. If unset, relative paths are used.