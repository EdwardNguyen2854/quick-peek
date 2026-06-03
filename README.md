# Quick Peek

<div>

[![Internal](https://img.shields.io/badge/License-Internal-yellow)](https://github.com/EdwardNguyen2854/quick-peek)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![Node 20+](https://img.shields.io/badge/Node-20%2B-green)](https://nodejs.org/)

</div>

Internal web app for fast batch preview of **STEP/STP**, **PDF**, **DXF**, and **OBJ** files. Designed for CAD teams — paste a list of codes, preview files instantly without opening CAD software.

## Features

- **Multi-format preview grid** — STEP, PDF, DXF, OBJ (one format at a time)
- **Batch code search** — paste many codes at once; glob-style filename matching
- **Adjustable grid** — column count (1–5) and preview height slider
- **Server-side folder browsing** with named presets per user
- **Full-screen preview modal** with pan/zoom for images and PDFs
- **3D rotate/pan/zoom** for OBJ (STEP via GLB converter)
- **User auth** with role-based permissions per format
- **Admin panel** — user management, file reindexing, usage dashboard
- **Info & Roadmap pages** — project docs and planned features
- **Time-savings estimator** (configurable seconds-per-file)
- **Windows .exe build** — PyInstaller single-folder package for distribution

## Quick Start

**Windows:**
```bat
scripts\run_dev_windows.bat
```

**Mac/Linux:**
```bash
scripts/run_dev_mac_linux.sh
```

Open [http://127.0.0.1:5173](http://127.0.0.1:5173). Default login: `admin` / `admin123`.

## Build Windows Executable

On Windows with Node.js and Python installed:

```bat
scripts\build_windows.bat
```

Output: `dist\QuickPeek\QuickPeek.exe` — copy the entire folder to the target machine.

## Architecture

```
backend/           FastAPI + SQLite (port 8000)
  app/
    main.py       FastAPI app + static file serving (frozen exe mode)
    config.py     All configuration via environment variables
    db.py         SQLite init + queries
    file_index.py File indexing and search
    preview.py    Preview generation logic
    dxf_preview.py DXF → SVG vector rendering
    routers/      auth, admin, peek, dashboard, folders
frontend/         React + Vite + TypeScript (port 5173)
  src/
    pages/        QuickPeekPage, AdminPage, DashboardPage, InfoPage, RoadmapPage
    components/   PreviewCard, ViewerModal, FolderPickerModal
    styles/       global.css (all styles)
tools/             Optional STEP→GLB converter (FreeCAD helper)
scripts/           Dev startup scripts + build script
data/              SQLite DB + indexed files (gitignored)
```

## Configuration

All settings via environment variables (or a `.env` file in `backend/`):

| Variable | Default | Description |
|---|---|---|
| `QUICKPEEK_FILE_ROOTS` | `./data/files` | Root folders to index (semicolon-separated) |
| `QUICKPEEK_SECRET_KEY` | `dev-secret-...` | JWT signing key — **change in production** |
| `QUICKPEEK_ADMIN_USERNAME` | `admin` | Initial admin username |
| `QUICKPEEK_ADMIN_PASSWORD` | `admin123` | Initial admin password — **change in production** |
| `QUICKPEEK_STEP_CONVERTER_CMD` | _(none)_ | Command to convert STEP→GLB, e.g. `"C:\tools\freecadcmd.exe" "{input}" "{output}"` |
| `QUICKPEEK_DB_PATH` | `./data/quickpeek.sqlite3` | SQLite database path (relative to `backend/`) |

After changing `QUICKPEEK_FILE_ROOTS`, go to **Admin → Reindex files**.

## Supported File Types

| Format | Extensions | Preview |
|---|---|---|
| STEP | `.stp`, `.step` | Placeholder (GLB conversion configurable) |
| PDF | `.pdf` | Embedded iframe (PDF.js) |
| DXF | `.dxf` | SVG vector render |
| OBJ | `.obj` | Three.js 3D viewer |

## STEP Preview (3D)

Three.js handles OBJ/GLB natively. STEP is CAD B-rep data requiring a converter:

```
STEP → QUICKPEEK_STEP_CONVERTER_CMD → GLB → Three.js
```

Enable by setting `QUICKPEEK_STEP_CONVERTER_CMD`. Without it, STEP shows a placeholder SVG. A FreeCAD helper is in `tools/freecad_step_to_glb.py`.

## License

**Internal** — For internal use only. Not licensed for external distribution.