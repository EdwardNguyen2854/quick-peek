# Architecture

Quick Peek has two small layers:

- **Frontend:** React/Vite single-screen UI for format selection, folder selection, code search, preview grid, full viewer, and download.
- **Backend:** FastAPI service for folder browsing, file indexing/search, raw file download, and preview generation.

## Data flow

```
User selects folder / codes
        ↓
POST /api/peek/search
        ↓
Index selected folder or refresh configured roots
        ↓
SQLite files table
        ↓
Preview metadata + URLs
        ↓
Browser preview
```

## Routes

- `GET /api/health`
- `GET /api/folders/browse`
- `POST /api/peek/search`
- `GET /api/files/{id}/preview`
- `GET /api/files/{id}/raw`

There is no authentication, account model, permissions layer, dashboard, admin API, or analytics API.

## STEP

STEP is sent raw to the browser, tessellated locally with OpenCascade WebAssembly, and rendered directly with Three.js.
