# Quick Peek — Agent Notes

## Repo Structure

```
backend/           FastAPI + SQLite (port 8000)
  app/
    main.py        FastAPI app + static serving for frozen exe
    config.py      All settings via environment variables
    db.py          SQLite schema init
    file_index.py  File indexing + search
    preview.py     Preview generation per format
    dxf_preview.py DXF → SVG vector renderer
    routers/       auth, admin, peek, dashboard, folders
frontend/          React + Vite + TypeScript (port 5173)
  src/pages/       QuickPeekPage, AdminPage, DashboardPage, InfoPage, RoadmapPage
  src/components/   PreviewCard, ViewerModal, FolderPickerModal
  src/styles/      global.css (all styles, no CSS modules)
scripts/           Platform dev scripts + build_windows.bat
tools/             FreeCAD STEP→GLB helper
```

## Dev Commands

**Windows:**
```bat
scripts\run_dev_windows.bat
```

**Mac/Linux:**
```bash
scripts/run_dev_mac_linux.sh
```

Both install deps and start backend + frontend concurrently.

**Manual:**
```bash
# Backend (Mac/Linux)
cd backend && python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend
cd frontend && npm install && npm run dev
```

## Build Windows Executable

On Windows with Node.js + Python installed:

```bat
scripts\build_windows.bat
```

Steps: `npm install` → `vite build` (outputs to `../backend/app/static`) → `PyInstaller quick_peek.spec`.
Output: `dist/QuickPeek/QuickPeek.exe` — copy the entire folder to target machine.

## Key Quirks

- **Backend binds to `0.0.0.0`** — accessible from all network interfaces. Not `127.0.0.1`.
- **Frontend build outputs to `backend/app/static`** — required for the PyInstaller exe to embed the React app. Do not change this path.
- **Python 3.9 union syntax breakage**: `HTTPAuthorizationCredentials | None` fails at runtime on Python 3.9 — use `Optional[HTTPAuthorizationCredentials]` with `from typing import Optional`. This has been fixed in `auth.py`; new route parameters must follow the same pattern.
- **Frozen exe static serving**: `main.py` uses `_resource_path()` → `sys._MEIPASS` when bundled. It checks if `app/static/` exists and mounts it at `/` with `html=True` for SPA routing.
- **Admin auto-created** on first boot from `QUICKPEEK_ADMIN_USERNAME/PASSWORD` env vars. Default `admin`/`admin123` — change before first run.
- **Relative DB path**: `QUICKPEEK_DB_PATH=./data/quickpeek.sqlite3` is relative to `backend/` working directory.
- **Offline network drives**: `reindex_files()` is wrapped in try/except — a missing network root won't crash startup.
- **STEP preview**: Placeholder by default. Real 3D requires `QUICKPEEK_STEP_CONVERTER_CMD` env var pointing to a converter that outputs GLB.
- **CORS wide open**: `allow_origins=["*"]` — appropriate for internal tool only.
- **No test/lint/typecheck**: `frontend/package.json` has no test scripts. `backend/requirements.txt` has no test deps. Adding tests would require installing pytest for backend and a test runner for frontend.