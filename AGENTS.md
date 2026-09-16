# Quick Peek — Agent Notes

## Product scope

Quick Peek is intentionally a small local file-search and preview app.

Core workflow only:
1. choose a format
2. optionally choose a working folder
3. paste codes / part numbers
4. search matching files
5. preview, open, or download

Do not reintroduce login, accounts, roles, permissions, admin pages, dashboards, roadmap pages, releases pages, API keys, LDAP, or usage analytics unless explicitly requested.

## Repo structure

```
backend/           FastAPI + SQLite file index (port 8000)
  app/
    main.py        app startup + optional embedded frontend
    config.py      file roots, DB, preview converter settings
    db.py          files table only
    file_index.py  index + search
    preview.py     preview generation
    dxf_preview.py DXF → SVG
    routers/       peek, folders
frontend/          React + Vite + TypeScript (port 5173)
  src/pages/       QuickPeekPage only
  src/components/  preview + folder picker components
scripts/           dev + Windows build scripts
tools/             FreeCAD STEP → tessellated GLB helper
```

## Development

Windows:
```bat
scripts\run_dev_windows.bat
```

macOS/Linux:
```bash
scripts/run_dev_mac_linux.sh
```

The Vite dev server proxies `/api` to `http://127.0.0.1:8000`.

Backend startup must use `backend/.venv` directly. If dependency installation fails, do not start uvicorn with a global interpreter.

## STEP preview

STEP previews are tessellated geometry:

```
STEP B-rep → tessellation → GLB → Three.js
```

They are for quick visual inspection and engineering checks, not authoritative B-rep/topology or precision validation.
