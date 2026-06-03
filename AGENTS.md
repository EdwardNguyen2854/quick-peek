# Quick Peek — Agent Notes

## Repo Structure

```
backend/      FastAPI + SQLite (port 8000)
frontend/     React/Vite (port 5173)
tools/        FreeCAD STEP→GLB conversion helper
scripts/      Platform-specific dev startup scripts
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

Both scripts install deps and start backend + frontend concurrently.

Manual start:
```bash
# Backend
cd backend && python3 -m venv .venv && source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Frontend
cd frontend && npm install && npm run dev
```

## Key Quirks

- **Platform split in scripts**: Windows uses `.bat` + `py` launcher; Mac/Linux uses `.sh` + `python3`. Backend startup binds to `0.0.0.0` on Windows, `127.0.0.1` on Mac/Linux.
- **Admin auto-created**: On first boot `ensure_admin_user()` creates the admin user from `QUICKPEEK_ADMIN_USERNAME/PASSWORD` env vars. Default is `admin`/`admin123`. Change before first run.
- **Relative DB path**: `QUICKPEEK_DB_PATH=./data/quickpeek.sqlite3` is relative to the `backend/` working directory.
- **Offline network drives**: `reindex_files()` is wrapped in try/except so a missing network root won't crash startup.
- **STEP preview**: Shows placeholder by default. Real 3D requires `QUICKPEEK_STEP_CONVERTER_CMD` env var pointing to a converter that outputs GLB.
- **CORS wide open**: `allow_origins=["*"]` — appropriate for internal tool only.
- **No type checking / lint in CI**: `frontend/package.json` has no test/lint/typecheck scripts. `backend/requirements.txt` has no test deps. Tests would need to be added.