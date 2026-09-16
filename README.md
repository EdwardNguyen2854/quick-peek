# Quick Peek

A local engineering file lookup and preview tool.

Quick Peek v0.8 focuses on **reliable search**: it normalizes part numbers, ranks strong matches deterministically, understands explicit revisions and common folder states, and keeps fuzzy results clearly separated as suggestions.

## Core workflow

1. choose **All** or a specific file format
2. optionally choose a working folder
3. paste one or many part numbers / codes
4. search the current SQLite index
5. review recommended matches, alternatives, suggestions, and missing codes
6. preview, open, or download the source file

There is no login, user/account management, admin panel, dashboard, roadmap, releases page, or permission system.

## Reliable search

Normal Search does **not** rescan the filesystem. Configured roots are indexed at startup, and the search panel provides explicit index status and Refresh controls.

Strong candidates are ranked in this order:

```
match exactness
→ folder priority
→ revision
→ modified time
→ stable filename tie-breaker
```

Match classes include:

- exact part number
- exact after case/separator normalization
- exact filename token
- part-number prefix / variant
- normalized substring

If there is no strong deterministic match, Quick Peek can show up to three conservative **Did you mean?** suggestions. Fuzzy suggestions are never automatically selected or marked as Found.

Common folder names influence ranking without hiding files:

- released / production / approved
- current / engineering / design
- supplier / vendor
- WIP / draft
- archive / obsolete / old

Multiple strong matches remain inspectable from the result card. Batch result filters are available for **All, Found, Multiple, Suggested, Missing**.

## Paste handling

Quick Peek accepts:

- one code per line
- comma- or semicolon-separated codes
- rows pasted from Excel/Sheets; when tabs are present, the first column is used
- codes with supported file extensions
- separator/case variations such as `ABC-123` vs `abc_123`
- numeric spreadsheet values such as `12345.0`

Input order is preserved after normalization and duplicate removal.

## Supported formats

- All supported formats
- STEP / STP
- PDF
- DXF
- Word
- Excel
- PowerPoint
- Markdown
- Text
- HTML

## Search index

The SQLite index stores filename/path metadata plus normalized forms, probable part code, explicit revision metadata, file type, folder class/priority, and timestamps.

The app automatically ignores common junk such as temporary Office files, editor swap files, cache directories, version-control directories, and common partial-download/backup suffixes.

Existing pre-v0.8 SQLite databases migrate in place. Existing file rows are retained and enriched on the next refresh.

API endpoints:

```
GET  /api/index/status
POST /api/index/refresh
POST /api/peek/search
```

Selecting a folder through the folder picker refreshes that folder explicitly. If you type a folder path manually, use **Refresh** before searching newly changed files.

## Quick start

### Windows

```bat
scripts\run_dev_windows.bat
```

Then open:

```
http://127.0.0.1:5173
```

The frontend runs on port `5173` and proxies `/api` to the backend on port `8000`.

Normal development binds to localhost. `scripts\run_lan_windows.bat` explicitly enables LAN access; because authentication has been removed, use LAN mode only on a trusted network.

### macOS / Linux

```bash
scripts/run_dev_mac_linux.sh
```

## Python

Backend startup uses `backend/.venv` for installation and uvicorn. If dependency installation fails, startup stops instead of falling back to a global Python installation.

If an old environment is broken, delete `backend/.venv` and run the launcher again.

## Configuration

Copy `backend/.env.example` to `backend/.env` if needed.

| Variable | Default | Purpose |
|---|---|---|
| `QUICKPEEK_FILE_ROOTS` | `./data/files` | Folders indexed at startup |
| `QUICKPEEK_DB_PATH` | `./data/quickpeek.sqlite3` | Local SQLite search index |
| `QUICKPEEK_LIBREOFFICE_CMD` | auto/empty | Optional Office conversion command |
| `QUICKPEEK_MAX_CONVERT_SIZE_MB` | `100` | Maximum document conversion size |

## STEP preview

```
STEP B-rep → OpenCascade WebAssembly tessellation → Three.js mesh
```

Visible STEP result cards are interactive: rotate, zoom, and pan directly in the grid. Tessellated mesh data is cached, and off-screen cards release their WebGL contexts. Card width and height are adjustable and saved locally.

No FreeCAD install or converter command is required. STEP previews are intended for quick visual inspection; use a CAD system for authoritative B-rep/topology or precision validation.

## Tests and CI

GitHub Actions runs:

- Python backend compilation
- search/ranking/migration/index integration tests
- TypeScript compilation
- Vite production build

Local backend tests:

```bash
cd backend
python -m unittest discover -s tests -v
```

Frontend build:

```bash
cd frontend
npm ci
npm run build
```

## Windows executable

```bat
scripts\build_windows.bat
```

The built frontend is bundled into the PyInstaller package.
