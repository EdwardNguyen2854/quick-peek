# Architecture

Quick Peek is a local two-layer engineering lookup tool:

- **Frontend:** React/Vite single-screen UI for indexed search, folder selection, batch result review, preview, and download.
- **Backend:** FastAPI + SQLite for filesystem indexing, deterministic search/ranking, folder browsing, raw files, and preview generation.

## Search data flow

```
Configured roots / explicit folder refresh
        ↓
Filesystem scan
        ↓
Filename normalization + metadata parsing
        ↓
SQLite files index
        ↓
POST /api/peek/search
        ↓
Candidate retrieval → deterministic ranking
        ↓
Recommended match + alternatives / suggestions
        ↓
Preview grid
```

Normal search never walks the filesystem. Configured roots are indexed at startup. Users can explicitly refresh the configured roots or the selected working folder.

## Ranking order

Strong candidates are ranked by:

1. match exactness
2. folder priority
3. revision
4. modified time
5. filename tie-breakers

Fuzzy candidates are suggestions only and are returned only when no strong candidate exists.

## Indexed metadata

The SQLite `files` table stores file metadata plus normalized filename/stem, compact identifier forms, parsed code, explicit revision metadata, tokens, file format, folder classification/priority, and index root.

`index_state` stores refresh health and timestamps.

## Routes

- `GET /api/health`
- `GET /api/folders/browse`
- `POST /api/peek/search`
- `GET /api/index/status`
- `POST /api/index/refresh`
- `GET /api/files/{id}/preview`
- `GET /api/files/{id}/raw`

There is no authentication, account model, permissions layer, dashboard, admin API, or analytics API.

## STEP

STEP is sent raw to the browser, tessellated locally with OpenCascade WebAssembly, and rendered directly with Three.js. Result cards are directly interactive and manage WebGL contexts based on viewport visibility.
