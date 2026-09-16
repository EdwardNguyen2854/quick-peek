# Implementation Notes

## Backend startup

`backend/run_backend.bat` and `backend/run_backend.sh`:
1. create `.venv` if missing
2. install requirements with the venv interpreter
3. stop on installation failure
4. run uvicorn with the same venv interpreter

This prevents fallback to a global Python installation.

## Frontend

`App.tsx` renders only `QuickPeekPage`.

`api.ts` uses relative URLs. Vite proxies `/api` to backend port 8000 in development.

## Backend

`main.py` includes only:
- `peek.router`
- `folders.router`

SQLite stores the file index only.

## Build

The Vite build outputs to `backend/app/static`. The PyInstaller spec bundles that directory as `app/static`.

## STEP viewer

`StepViewer.tsx` loads the raw STEP preview URL and uses `occt-wasm` to import and tessellate the model in the browser. Vite excludes `occt-wasm` from dependency pre-bundling and targets ESNext so the WebAssembly runtime is emitted correctly.

## STEP preview grid

STEP result cards render automatically as interactive Three.js viewports. `StepCardViewer` shares the cached tessellated mesh with the full `StepViewer` and uses `IntersectionObserver` to keep WebGL contexts only for cards in or near the viewport. Cards support direct rotate, wheel zoom, and pan; off-screen cards release their renderer while retaining a lightweight snapshot and cached mesh.

## UI layout

The frontend uses a single professional workspace: sticky product header, compact format selector, two-column search form, responsive results grid, and a focused full-screen preview modal. Keep new controls visually restrained and avoid adding secondary navigation or dashboard surfaces.

## Card sizing

The Results toolbar exposes persisted card width and height sliders. Width controls the responsive grid track size; height controls the full card height. STEP viewports use ResizeObserver so their renderer and camera update when card dimensions change.
