# Architecture — Document Preview Feature

> **Quick Peek v0.3** — Release: Document Preview

---

## Overview

The Quick Peek document preview feature extends the existing file preview pipeline to handle document formats (Office documents, Markdown, plain text, HTML) alongside the already-supported CAD formats (STEP, DXF, OBJ, PDF).

The system follows a **search → preview → serve** pipeline:

```
User Search (codes + format)
    ↓
Backend search_index() — queries SQLite by extension and filename pattern
    ↓
Frontend renders PreviewCard(s) with thumbnail from /api/files/{id}/preview
    ↓
User clicks → ViewerModal opens → full preview served from /api/files/{id}/preview
```

---

## Format Strategies

| Format | Extensions | Strategy |
|--------|-----------|----------|
| **PDF** | `.pdf` | Direct serve — `FileResponse` with `media_type="application/pdf"` |
| **Word** | `.doc`, `.docx` | `python-docx` → HTML → serve as iframe |
| **Excel** | `.xls`, `.xlsx` | `openpyxl` → HTML table → serve as iframe |
| **PowerPoint** | `.ppt`, `.pptx` | `python-pptx` → HTML → serve as iframe |
| **Markdown** | `.md` | `markdown` library → styled HTML → serve in iframe |
| **Plain Text** | `.txt` | Direct serve with `text/plain` content type |
| **HTML** | `.html`, `.htm` | Direct serve with `text/html` content type |

### Strategy Details

**Office → HTML**: Pure Python libraries are used to extract content from Office documents and render as HTML:
- `python-docx` for Word documents (.doc, .docx) — extracts paragraphs, tables, and basic formatting
- `openpyxl` for Excel spreadsheets (.xls, .xlsx) — extracts cell data and renders as HTML tables
- `python-pptx` for PowerPoint presentations (.ppt, .pptx) — extracts slide text and content

This approach requires **no system-level dependencies** (unlike LibreOffice), works offline, and produces HTML output that renders directly in the browser. Conversion is on-demand when a file is first previewed, with results cached in `cache/previews/`.

**Markdown → HTML**: The Python `markdown` library with `fenced_code`, `tables`, and `codehilite` extensions converts `.md` files to styled HTML. The output is cached in the preview directory.

**Direct Serve**: For `txt`, `html`, and already-processed `pdf` files, the original file is served directly with the correct MIME type. No conversion is needed.

---

## Converter Module Design

```
backend/app/converters/
├── __init__.py          # Module marker
├── office_to_html.py    # Pure Python Office-to-HTML converters
└── markdown_to_html.py  # Markdown → styled HTML converter
```

### `office_to_html.py`

**Purpose**: Convert Office documents (doc, docx, xls, xlsx, ppt, pptx) to HTML using pure Python libraries.

**Key functions**:
- `docx_to_html(input_path, output_path)` — Converts Word documents to HTML using `python-docx`
- `xlsx_to_html(input_path, output_path)` — Converts Excel spreadsheets to HTML tables using `openpyxl`
- `pptx_to_html(input_path, output_path)` — Converts PowerPoint presentations to HTML using `python-pptx`
- `office_to_html(input_path, output_path, file_format)` — Dispatches to the appropriate converter based on format

**Flow**:
1. Check file size against `MAX_CONVERT_SIZE_MB` (default: 100 MB)
2. Dispatch to format-specific converter based on file extension
3. Each converter extracts content and writes styled HTML
4. Verify output HTML exists and has non-zero size
5. Return `True`/`False`

**Error handling**: Returns `False` on any exception. No exceptions propagate.

### `markdown_to_html.py`

**Purpose**: Convert Markdown files to styled HTML.

**Key functions**:
- `markdown_to_html(input_path, output_path)` — Converts markdown to HTML with GitHub-flavored styling

**Flow**:
1. Check `MARKDOWN_AVAILABLE` (True if `markdown` library is importable)
2. Read input file as UTF-8
3. Apply `markdown.markdown()` with `fenced_code`, `tables`, `codehilite` extensions
4. Wrap in styled HTML document with GitHub-inspired CSS
5. Write to output path
6. Return `True`/`False`

**Styling**: Injects a complete CSS stylesheet including:
- System font stack
- Code block backgrounds with syntax highlighting colors
- Table borders and padding
- Blockquote styling
- Responsive images

---

## Caching Strategy

### Cache Location
```
backend/cache/previews/
├── {sha256_hash}.svg   # DXF renders
├── {sha256_hash}.glb   # STEP → GLB conversions
├── {sha256_hash}.html  # Office → HTML conversions
└── {sha256_hash}.html  # Markdown → HTML conversions
```

### Cache Key Generation — `file_key()`

```python
def file_key(path: Path) -> str:
    st = path.stat()
    src = f"{path.resolve()}|{st.st_mtime}|{st.st_size}".encode("utf-8", errors="ignore")
    return hashlib.sha256(src).hexdigest()[:24]
```

The key is a 24-character SHA-256 hash of the **resolved absolute path + mtime + size**. This means:
- If the file is moved → new key → cache miss
- If the file is edited → new mtime and/or size → cache miss
- If the file is unchanged → cache hit

### Cache Invalidation

**Automatic**: The `file_key()` incorporates the file's `mtime` and `size`. Any edit to the source file produces a new key, orphaning the old cached file.

**No manual invalidation**: There is no cache purge endpoint. Old cached files accumulate in `cache/previews/` but are harmless.

**Cache hit flow for Office/Markdown**:
1. `ensure_preview()` computes `file_key(path)`
2. Checks if `{key}.pdf` (or `.html`) exists in `PREVIEW_DIR`
3. If exists → return `{"kind": "pdf"/"html", "ready": True, "cache_file": str(out)}`
4. If not → call converter → cache result → return

---

## Permission Model

### Permission List

```python
DEFAULT_USER_PERMISSIONS = [
    "use_quick_peek",
    "view_step", "view_pdf", "view_dxf", "view_obj",
    "view_doc", "view_xls", "view_ppt", "view_md", "view_txt", "view_html"
]
ADMIN_PERMISSIONS = DEFAULT_USER_PERMISSIONS + [
    "view_dashboard", "manage_users", "download_files"
]
```

### Format-to-Permission Mapping

```python
FORMAT_PERMISSION = {
    "step": "view_step",
    "pdf": "view_pdf",
    "dxf": "view_dxf",
    "obj": "view_obj",
    "doc": "view_doc",   # Added for document preview
    "xls": "view_xls",   # Added for document preview
    "ppt": "view_ppt",   # Added for document preview
    "md": "view_md",     # Added for document preview
    "txt": "view_txt",   # Added for document preview
    "html": "view_html", # Added for document preview
}
```

### Enforcement Points

1. **Backend `peek.py` — `search()` endpoint**: Validates user has the format-specific permission before searching. Raises `403` if missing.
2. **Backend `peek.py` — `preview_file()` endpoint**: Requires valid JWT token (via `current_user`). Permission checked at search time; preview just requires auth.
3. **Frontend `QuickPeekPage.tsx`**: Format buttons are disabled for users lacking the corresponding permission.

---

## API Endpoints

### `POST /api/peek/search`

Searches for files matching codes within a format.

**Request**:
```json
{
  "format": "doc" | "xls" | "ppt" | "md" | "txt" | "html",
  "codes": ["1827009605", "573419"],
  "folder_path": "/path/to/folder" | null
}
```

**Response**:
```json
{
  "format": "doc",
  "codes_count": 2,
  "files_found": 3,
  "folder_path": "/path/to/folder",
  "results": [
    {
      "code": "1827009605",
      "status": "found" | "multiple_matches" | "not_found",
      "matches_count": 1,
      "files": [FileItem, ...]
    }
  ]
}
```

### `GET /api/files/{file_id}/preview?format={format}`

Returns the preview content for a file.

**Behavior by format**:
- `pdf`: Returns `FileResponse` with `media_type="application/pdf"` (inline)
- `doc/xls/ppt`: Returns cached PDF from `cache/previews/{key}.pdf`
- `md`: Returns cached HTML from `cache/previews/{key}.html`
- `txt`: Returns raw text file with `text/plain`
- `html`: Returns raw HTML file with `text/html`
- `dxf`: Returns cached SVG from `cache/previews/{key}.svg`
- `step` (no converter): Returns placeholder SVG with configuration message
- `obj`: Returns `FileResponse` with `media_type="model/obj"` (inline)

### `GET /api/files/{file_id}/raw`

Returns the original file as a **download** (`Content-Disposition: attachment`).

### `POST /api/usage/open`

Logs that a user opened a preview. Used for usage statistics.

**Request**:
```json
{
  "file_id": 123,
  "format": "doc"
}
```

---

## Data Flow Diagrams

### Office Document Preview Flow

```
User clicks PreviewCard
    ↓
ViewerModal renders iframe with /api/files/{id}/preview?format=doc
    ↓
peek.py: preview_file() calls ensure_preview(row, "doc")
    ↓
ensure_preview() computes file_key(path) → "a1b2c3..."
    ↓
Check cache/previews/a1b2c3...html exists?
    ├─ Yes → return {kind: "html", ready: True, cache_file: "...html"}
    └─ No  → call office_to_html(path, PREVIEW_DIR / "a1b2c3...html")
                ├─ python-docx/openpyxl/pptx available → convert → cache HTML → return
                └─ Conversion fails → return {kind: "unknown", ready: False, message: "..."}
    ↓
FileResponse(cache_path, media_type="text/html")
    ↓
Browser renders HTML in iframe
```

### Markdown Preview Flow

```
User clicks PreviewCard for .md file
    ↓
ViewerModal renders iframe with /api/files/{id}/preview?format=md
    ↓
ensure_preview() computes file_key() → checks cache/previews/{key}.html
    ├─ Exists → return {kind: "html", ready: True, cache_file: "...html"}
    └─ Not exists → markdown_to_html() → writes styled HTML → cache → return
    ↓
FileResponse(cache_path, media_type="text/html")
    ↓
Browser renders HTML in iframe
```

---

## Dependencies

### Backend (Python)

| Package | Version | Purpose |
|---------|---------|---------|
| `fastapi` | 0.115.6 | Web framework |
| `uvicorn[standard]` | 0.32.1 | ASGI server |
| `python-jose[cryptography]` | 3.3.0 | JWT token handling |
| `pydantic` | 2.10.4 | Request/response validation |
| `python-multipart` | 0.0.20 | Form data parsing |
| `markdown` | (system) | Markdown → HTML conversion |
| `python-docx` | 1.1.2 | Word document → HTML |
| `openpyxl` | 3.1.5 | Excel spreadsheet → HTML |
| `python-pptx` | 1.0.2 | PowerPoint → HTML |

**System dependency**: None (pure Python solution — no LibreOffice or other system packages required)

### Frontend (JavaScript/TypeScript)

| Package | Purpose |
|---------|---------|
| `react` | UI framework |
| `three` | 3D rendering (STEP/OBJ viewers) |
| `lucide-react` | Icons |

### System Requirements

- **Python 3.9+** with pip-installed packages listed above
- No LibreOffice or other system-level dependencies required for Office format conversion

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `QUICKPEEK_MAX_CONVERT_SIZE_MB` | `100` | Max file size (MB) for Office conversion |
| `QUICKPEEK_STEP_CONVERTER_CMD` | (empty) | STEP → GLB converter command template |

### Supported Formats Configuration

```python
SUPPORTED_FORMATS = {
    "step": [".stp", ".step"],
    "pdf":  [".pdf"],
    "dxf":  [".dxf"],
    "obj":  [".obj"],
    "doc":  [".doc", ".docx"],
    "xls":  [".xls", ".xlsx"],
    "ppt":  [".ppt", ".pptx"],
    "md":   [".md"],
    "txt":  [".txt"],
    "html": [".html", ".htm"],
}
```

---

## Directory Structure

```
quick-peek/
├── backend/
│   └── app/
│       ├── config.py              # SUPPORTED_FORMATS, permissions, cache dirs
│       ├── preview.py             # ensure_preview(), file_key()
│       ├── converters/
│       │   ├── __init__.py
│       │   ├── office_to_html.py   # Pure Python Office converters
│       │   └── markdown_to_html.py
│       ├── dxf_preview.py        # DXF → SVG (existing)
│       ├── routers/
│       │   └── peek.py            # /api/peek/search, /api/files/{id}/preview
│       └── ...
├── frontend/
│   └── src/
│       ├── types.ts               # Format type, FileItem, permissions
│       ├── api.ts                 # API client functions
│       ├── pages/QuickPeekPage.tsx  # Format selector, search UI
│       └── components/
│           ├── ViewerModal.tsx     # Preview modal with iframe
│           └── PreviewCard.tsx     # Thumbnail card
└── .agents/docs/
    ├── ARCHITECTURE.md            # This document
    ├── DECISIONS.md               # Decision log
    └── IMPLEMENTATION.md          # Implementation guide
```

---

## Security Considerations

1. **CORS wide open** (`allow_origins=["*"]`): Appropriate for internal tool only. The tool is designed for LAN/internal network use.

2. **No file path traversal protection in preview**: The `file_id` maps to a database row with a stored `full_path`. Users can only access files that have been indexed.

3. **JWT authentication required**: All preview and search endpoints require a valid JWT token.

4. **Permission-based access control**: Users can only search/preview formats they have been granted permission for.

5. **File size limit on conversion**: Office files larger than `MAX_CONVERT_SIZE_MB` are rejected from conversion to prevent resource exhaustion.