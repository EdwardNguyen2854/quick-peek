# Quick Peek

A small local web app for fast batch file lookup and preview.

The app now focuses on the core workflow only:

- choose a file format
- optionally choose a working folder
- paste one or more part numbers / codes
- search matching files
- preview them in a grid
- open a larger preview or download the source file
- rotate / pan / zoom STEP previews tessellated directly in the browser

There is no login, user/account management, admin panel, dashboard, roadmap, releases page, or permission system.

## Supported formats

- STEP / STP
- PDF
- DXF
- Word
- Excel
- PowerPoint
- Markdown
- Text
- HTML

## Quick start

### Windows

```bat
scripts\run_dev_windows.bat
```

Then open:

```
http://127.0.0.1:5173
```

The frontend runs on port `5173` and proxies `/api` requests to the backend on port `8000`.

The normal dev launcher binds to localhost. `scripts\\run_lan_windows.bat` opts into LAN access explicitly; because authentication has been removed, use LAN mode only on a trusted network.

### macOS / Linux

```bash
scripts/run_dev_mac_linux.sh
```

## Python 3.14

The backend dependencies require Pydantic 2.13+ and FastAPI 0.119.1+, which support Python 3.14.

The startup scripts always install and run packages through `backend/.venv`. If dependency installation fails, the backend stops instead of continuing with a global Python environment.

If you have an old broken environment, you can delete `backend/.venv` and run the start script again.

## Configuration

Copy `backend/.env.example` to `backend/.env` if needed.

| Variable | Default | Purpose |
|---|---|---|
| `QUICKPEEK_FILE_ROOTS` | `./data/files` | Folders indexed at startup |
| `QUICKPEEK_DB_PATH` | `./data/quickpeek.sqlite3` | Local SQLite file index |
| `QUICKPEEK_LIBREOFFICE_CMD` | auto/empty | Optional Office conversion command |
| `QUICKPEEK_MAX_CONVERT_SIZE_MB` | `100` | Maximum document conversion size |

## STEP preview

Quick Peek does not render the native STEP B-rep directly. The preview pipeline is:

```
STEP B-rep → OpenCascade WebAssembly tessellation → Three.js mesh
```

STEP tessellation runs locally in the browser; no FreeCAD install or `QUICKPEEK_STEP_CONVERTER_CMD` is required. This is intended for quick visual inspection and engineering checks. Use a CAD system when exact B-rep topology or precision geometry validation is required.

## Windows executable

Build with:

```bat
scripts\build_windows.bat
```

The built frontend is bundled into the PyInstaller package.
