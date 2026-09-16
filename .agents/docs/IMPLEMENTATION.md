# Implementation Notes

## Backend startup

`backend/run_backend.bat` and `backend/run_backend.sh` use `backend/.venv`, stop on install failure, and run uvicorn with the same interpreter.

## Search modules

- `db.py`: schema migration, SQLite connection helpers, index state
- `file_index.py`: filesystem scan, metadata upsert, candidate retrieval, index status/refresh
- `search_engine.py`: normalization, revision/folder parsing, match classification, deterministic ranking, fuzzy suggestions
- `routers/peek.py`: search/index API and preview/raw file routes

Search ranking belongs on the backend. The frontend must display backend explanations rather than reproducing ranking rules.

## Index lifecycle

Configured roots are indexed on startup. Refreshing an unchanged file reuses its existing parsed metadata when size and mtime are unchanged. Normal search never calls the filesystem indexer.

The UI exposes index health and a manual Refresh action. Selecting a folder through the folder picker refreshes that folder explicitly.

## Match model

Strong match classes:

- exact
- exact normalized
- exact token
- variant/prefix
- normalized partial

If no strong match exists, edit-distance suggestions are considered conservatively. Suggestions remain a separate result status.

## Frontend

`QuickPeekPage.tsx` provides:
- All or format-specific search
- robust paste normalization
- index status/refresh
- batch result filters
- persisted card dimensions

`PreviewCard.tsx` displays the backend match reason, revision/folder context, fuzzy suggestions, and inspectable alternative matches.

## STEP viewer

`StepViewer.tsx` imports STEP using `occt-wasm`. Interactive result cards share cached tessellation data, use `IntersectionObserver` to limit WebGL contexts, and use `ResizeObserver` for card resizing.

## Build and CI

Vite builds into `backend/app/static`. GitHub Actions runs backend compilation/unit/integration tests and the frontend TypeScript/Vite build on pull requests and pushes to `main`.
