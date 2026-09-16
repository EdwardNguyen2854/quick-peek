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
