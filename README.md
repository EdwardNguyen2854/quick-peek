# Quick Peek

<div>

[![Internal](https://img.shields.io/badge/License-Internal-yellow)](https://github.com/EdwardNguyen2854/quick-peek)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![Node 20+](https://img.shields.io/badge/Node-20%2B-green)](https://nodejs.org/)

</div>

Internal web app for fast batch preview of **STEP/STP**, **PDF**, **DXF**, and **OBJ** files. Designed for CAD workflows — paste a list of codes, preview files instantly without opening CAD software.

## Features

- Multi-format preview grid: STEP, PDF, DXF, OBJ (one format at a time)
- Paste many codes at once with glob-style search patterns
- Server-side folder browsing with named presets per user
- Full-screen preview modal with pan/zoom
- 3D rotate/pan/zoom for OBJ (and STEP via GLB converter)
- User auth with role-based permissions
- Admin panel: user management, file reindexing, usage dashboard
- Time-savings estimator (configurable seconds-per-file)

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

## Architecture

```
backend/      FastAPI + SQLite (port 8000)
frontend/     React/Vite (port 5173)
tools/        Optional STEP→GLB converter helper
scripts/      Dev startup scripts
```

## Configuration

Copy `backend/.env.example` → `backend/.env` and adjust:

| Variable | Default | Description |
|---|---|---|
| `QUICKPEEK_FILE_ROOTS` | `./data/files` | Root folders to index (comma/semicolon separated) |
| `QUICKPEEK_SECRET_KEY` | `change-this...` | JWT signing key — **change in production** |
| `QUICKPEEK_ADMIN_USERNAME` | `admin` | Initial admin username |
| `QUICKPEEK_ADMIN_PASSWORD` | `admin123` | Initial admin password — **change in production** |
| `QUICKPEEK_STEP_CONVERTER_CMD` | _(none)_ | Command to convert STEP→GLB, e.g. `"C:\tools\step-to-glb.exe" "{input}" "{output}"` |

After changing `QUICKPEEK_FILE_ROOTS`, go to **Admin → Reindex files**.

## STEP Preview

Three.js handles OBJ/GLB natively. STEP is CAD B-rep data requiring a converter:

```
STEP → QUICKPEEK_STEP_CONVERTER_CMD → GLB → Three.js
```

Enable by setting `QUICKPEEK_STEP_CONVERTER_CMD`. Without it, STEP shows a placeholder. A FreeCAD helper skeleton is in `tools/freecad_step_to_glb.py`.

## License

**Internal** — For internal use only. Not licensed for external distribution.