# Implementation Guide — Document Preview Feature

> **Quick Peek v0.3** — Document Preview Release

---

## Overview

This guide covers the step-by-step implementation for adding document preview support (doc, docx, xls, xlsx, ppt, pptx, md, txt, html) to Quick Peek.

---

## Backend Changes

### 1. `config.py` — Add New Formats and Permissions

**File**: `backend/app/config.py`

**Changes**:

```python
# 1. Add SUPPORTED_FORMATS entries for new formats
SUPPORTED_FORMATS = {
    "step": [".stp", ".step"],
    "pdf": [".pdf"],
    "dxf": [".dxf"],
    "obj": [".obj"],
    "doc": [".doc", ".docx"],      # NEW
    "xls": [".xls", ".xlsx"],     # NEW
    "ppt": [".ppt", ".pptx"],     # NEW
    "md": [".md"],                 # NEW
    "txt": [".txt"],               # NEW
    "html": [".html", ".htm"],     # NEW
}

# 2. Add LibreOffice configuration
LIBREOFFICE_CMD = _get("QUICKPEEK_LIBREOFFICE_CMD", "").strip()  # auto-detect if empty
MAX_CONVERT_SIZE_MB = int(_get("QUICKPEEK_MAX_CONVERT_SIZE_MB", "100"))

# 3. Add per-format permissions
DEFAULT_USER_PERMISSIONS = [
    "use_quick_peek",
    "view_step", "view_pdf", "view_dxf", "view_obj",
    "view_doc", "view_xls", "view_ppt",  # NEW
    "view_md", "view_txt", "view_html",  # NEW
]
ADMIN_PERMISSIONS = DEFAULT_USER_PERMISSIONS + [
    "view_dashboard", "manage_users", "download_files"
]
```

**Checklist**:
- [ ] All new format extensions added to `SUPPORTED_FORMATS`
- [ ] `LIBREOFFICE_CMD` env var defined
- [ ] `MAX_CONVERT_SIZE_MB` env var defined (with sensible default)
- [ ] `view_doc`, `view_xls`, `view_ppt`, `view_md`, `view_txt`, `view_html` in `DEFAULT_USER_PERMISSIONS`
- [ ] Admin has all new permissions

---

### 2. `converters/office_to_html.py` — Pure Python Office Converters

**File**: `backend/app/converters/office_to_html.py` (new file)

**Implementation**:

```python
from __future__ import annotations

import platform
from pathlib import Path
from typing import Optional

try:
    import docx
    import openpyxl
    from pptx import Presentation
    OFFICE_LIBS_AVAILABLE = True
except ImportError:
    OFFICE_LIBS_AVAILABLE = False


def docx_to_html(input_path: Path, output_path: Path) -> bool:
    """Convert a Word document to HTML using python-docx."""
    if not OFFICE_LIBS_AVAILABLE:
        return False
    try:
        doc = docx.Document(str(input_path))
        paragraphs = []
        for para in doc.paragraphs:
            if para.text.strip():
                paragraphs.append(f"<p>{para.text}</p>")

        # Extract tables
        tables_html = ""
        for table in doc.tables:
            tables_html += "<table border='1' style='border-collapse: collapse; width: 100%;'>"
            for row in table.rows:
                tables_html += "<tr>"
                for cell in row.cells:
                    tables_html += f"<td style='padding: 8px;'>{cell.text}</td>"
                tables_html += "</tr>"
            tables_html += "</table>"

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{input_path.name}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; padding: 20px; line-height: 1.6; }}
        p {{ margin: 12px 0; }}
        table {{ border-collapse: collapse; margin: 16px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f5f5f5; }}
    </style>
</head>
<body>
    {"".join(paragraphs)}
    {tables_html}
</body>
</html>"""
        output_path.write_text(html_content, encoding="utf-8")
        return True
    except Exception:
        return False


def xlsx_to_html(input_path: Path, output_path: Path) -> bool:
    """Convert an Excel spreadsheet to HTML using openpyxl."""
    if not OFFICE_LIBS_AVAILABLE:
        return False
    try:
        wb = openpyxl.load_workbook(str(input_path), data_only=True)
        tables_html = ""
        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            tables_html += f"<h3>{sheet_name}</h3>"
            tables_html += "<table border='1' style='border-collapse: collapse; width: 100%; margin-bottom: 20px;'>"
            for row in ws.iter_rows(values_only=True):
                tables_html += "<tr>"
                for cell in row:
                    tables_html += f"<td style='padding: 6px 8px;'>{str(cell) if cell is not None else ''}</td>"
                tables_html += "</tr>"
            tables_html += "</table>"

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{input_path.name}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; padding: 20px; }}
        table {{ border-collapse: collapse; margin-bottom: 20px; }}
        th, td {{ border: 1px solid #ddd; padding: 6px 8px; text-align: left; }}
        th {{ background-color: #f5f5f5; font-weight: bold; }}
    </style>
</head>
<body>
    {tables_html}
</body>
</html>"""
        output_path.write_text(html_content, encoding="utf-8")
        return True
    except Exception:
        return False


def pptx_to_html(input_path: Path, output_path: Path) -> bool:
    """Convert a PowerPoint presentation to HTML using python-pptx."""
    if not OFFICE_LIBS_AVAILABLE:
        return False
    try:
        prs = Presentation(str(input_path))
        slides_html = ""
        for i, slide in enumerate(prs.slides, 1):
            slides_html += f"<h2>Slide {i}</h2>"
            for shape in slide.shapes:
                if hasattr(shape, "text") and shape.text.strip():
                    slides_html += f"<p>{shape.text}</p>"

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{input_path.name}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; padding: 20px; }}
        h2 {{ color: #333; border-bottom: 1px solid #ddd; padding-bottom: 8px; }}
        p {{ margin: 10px 0; line-height: 1.5; }}
    </style>
</head>
<body>
    {slides_html}
</body>
</html>"""
        output_path.write_text(html_content, encoding="utf-8")
        return True
    except Exception:
        return False


def office_to_html(input_path: Path, output_path: Path, file_format: str = "") -> bool:
    """
    Convert an Office document to HTML using the appropriate pure Python library.
    Returns True if HTML was created successfully, False otherwise.
    """
    from ..config import MAX_CONVERT_SIZE_MB

    # Check file size
    try:
        size_mb = input_path.stat().st_size / (1024 * 1024)
        if size_mb > MAX_CONVERT_SIZE_MB:
            return False
    except Exception:
        return False

    if not OFFICE_LIBS_AVAILABLE:
        return False

    # Dispatch to appropriate converter based on format
    ext = input_path.suffix.lower()
    if ext in (".doc", ".docx"):
        return docx_to_html(input_path, output_path)
    elif ext in (".xls", ".xlsx"):
        return xlsx_to_html(input_path, output_path)
    elif ext in (".ppt", ".pptx"):
        return pptx_to_html(input_path, output_path)

    return False
```

**Checklist**:
- [ ] `OFFICE_LIBS_AVAILABLE` check handles missing libraries gracefully
- [ ] `docx_to_html()` extracts paragraphs and tables from Word docs
- [ ] `xlsx_to_html()` extracts cell data from all sheets in Excel files
- [ ] `pptx_to_html()` extracts text from all slides in PowerPoint files
- [ ] File size check against `MAX_CONVERT_SIZE_MB`
- [ ] Returns `False` on any failure (no exceptions propagated)

---

### 3. `converters/markdown_to_html.py` — Markdown Converter

**File**: `backend/app/converters/markdown_to_html.py` (new file)

**Implementation**:

```python
from __future__ import annotations

from pathlib import Path
from typing import Optional

try:
    import markdown
    MARKDOWN_AVAILABLE = True
except ImportError:
    MARKDOWN_AVAILABLE = False


def markdown_to_html(input_path: Path, output_path: Path) -> bool:
    """Convert a Markdown file to styled HTML. Returns True on success."""
    if not MARKDOWN_AVAILABLE:
        return False

    try:
        content = input_path.read_text(encoding="utf-8", errors="ignore")
        html_body = markdown.markdown(
            content,
            extensions=["fenced_code", "tables", "codehilite"]
        )

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{input_path.name}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.6;
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
            color: #333;
        }}
        pre {{ background-color: #f6f8fa; padding: 16px; border-radius: 6px; overflow-x: auto; }}
        code {{ font-family: "SF Mono", Monaco, Consolas, monospace; font-size: 14px; background-color: #f6f8fa; padding: 2px 6px; border-radius: 3px; }}
        pre code {{ padding: 0; background-color: transparent; }}
        table {{ border-collapse: collapse; width: 100%; margin: 16px 0; }}
        th, td {{ border: 1px solid #d0d7de; padding: 8px 12px; text-align: left; }}
        th {{ background-color: #f6f8fa; }}
        blockquote {{ border-left: 4px solid #d0d7de; margin: 16px 0; padding-left: 16px; color: #6e7781; }}
        img {{ max-width: 100%; height: auto; }}
    </style>
</head>
<body>
{html_body}
</body>
</html>"""

        output_path.write_text(html_content, encoding="utf-8")
        return True

    except Exception:
        return False
```

**Checklist**:
- [ ] Graceful handling if `markdown` library not installed (`MARKDOWN_AVAILABLE`)
- [ ] UTF-8 encoding with `errors="ignore"` for binary robustness
- [ ] Extensions: `fenced_code`, `tables`, `codehilite`
- [ ] Styled HTML wrapper with GitHub-flavored CSS
- [ ] Returns `False` on any exception

---

### 4. `preview.py` — Update `ensure_preview()`

**File**: `backend/app/preview.py`

**Changes**: Add handlers for `doc`, `xls`, `ppt`, `md`, `txt`, `html` formats.

**Updated `ensure_preview()` logic**:

```python
def ensure_preview(file_row: dict, file_format: str) -> Dict[str, str | bool | None]:
    path = Path(file_row["full_path"])
    key = file_key(path)

    # Existing formats
    if file_format == "pdf":
        return {"kind": "pdf", "ready": True, "message": None, "cache_file": None}
    if file_format == "dxf":
        out = PREVIEW_DIR / f"{key}.svg"
        # ... existing DXF logic ...
    if file_format == "obj":
        return {"kind": "obj", "ready": True, "message": None, "cache_file": None}
    if file_format == "step":
        # ... existing STEP logic ...

    # NEW: Office formats (doc, xls, ppt) → HTML
    if file_format in ("doc", "xls", "ppt"):
        out = PREVIEW_DIR / f"{key}.html"
        if not out.exists():
            ok = office_to_html(path, out, file_format)
            if not ok:
                return {"kind": "unknown", "ready": False, "message": "Conversion unavailable. Download to view.", "cache_file": None}
        return {"kind": "html", "ready": True, "message": None, "cache_file": str(out)}

    # NEW: Markdown → HTML
    if file_format == "md":
        out = PREVIEW_DIR / f"{key}.html"
        if not out.exists():
            ok = markdown_to_html(path, out)
            if not ok:
                return {"kind": "unknown", "ready": False, "message": "Markdown conversion failed.", "cache_file": None}
        return {"kind": "html", "ready": True, "message": None, "cache_file": str(out)}

    # NEW: Text and HTML — direct serve
    if file_format == "txt":
        return {"kind": "txt", "ready": True, "message": None, "cache_file": None}
    if file_format == "html":
        return {"kind": "html", "ready": True, "message": None, "cache_file": None}

    return {"kind": "unknown", "ready": False, "message": "Unsupported format", "cache_file": None}
```

**Checklist**:
- [ ] Import `office_to_html` and `markdown_to_html` from converters
- [ ] `doc`, `xls`, `ppt` all route to `office_to_html` → return `kind: "html"`
- [ ] `md` routes to `markdown_to_html` → return `kind: "html"`
- [ ] `txt` returns `kind: "txt"` (no conversion, no cache)
- [ ] `html` returns `kind: "html"` (no conversion, no cache)
- [ ] Graceful fallback on conversion failure

---

### 5. `routers/peek.py` — Update Permission Map and Preview Endpoint

**File**: `backend/app/routers/peek.py`

**Changes**:

```python
# 1. Update FORMAT_PERMISSION to include new formats
FORMAT_PERMISSION = {
    "step": "view_step",
    "pdf": "view_pdf",
    "dxf": "view_dxf",
    "obj": "view_obj",
    "doc": "view_doc",    # NEW
    "xls": "view_xls",    # NEW
    "ppt": "view_ppt",    # NEW
    "md": "view_md",      # NEW
    "txt": "view_txt",    # NEW
    "html": "view_html",  # NEW
}
```

**2. Update `preview_file()` endpoint** to handle new `kind` values:

```python
@router.get("/files/{file_id}/preview")
def preview_file(file_id: int, format: str, user=Depends(current_user)):
    # ... fetch file ...
    p = ensure_preview(item, format)

    # Direct serve formats
    if p["kind"] == "pdf":
        return FileResponse(Path(item["full_path"]), media_type="application/pdf")
    if p["kind"] == "obj":
        return FileResponse(Path(item["full_path"]), media_type="model/obj")
    if p["kind"] == "txt":
        return FileResponse(Path(item["full_path"]), media_type="text/plain")
    if p["kind"] == "html":
        return FileResponse(Path(item["full_path"]), media_type="text/html")

    # Cached conversions
    if p.get("cache_file"):
        cache_path = Path(str(p["cache_file"]))
        if cache_path.exists():
            if cache_path.suffix == ".svg":
                return FileResponse(cache_path, media_type="image/svg+xml")
            if cache_path.suffix == ".html":
                return FileResponse(cache_path, media_type="text/html")
            if cache_path.suffix == ".glb":
                return FileResponse(cache_path, media_type="model/gltf-binary")
            # PDF from cache
            return FileResponse(cache_path, media_type="application/pdf")

    # Fallback SVG for STEP without converter
    # ... existing placeholder SVG logic ...
```

**Checklist**:
- [ ] `FORMAT_PERMISSION` has all 10 formats
- [ ] `SearchRequest` schema allows new format literals
- [ ] `OpenLogRequest` schema allows new format literals
- [ ] `preview_file()` handles `kind: "txt"` and `kind: "html"` direct serve
- [ ] `preview_file()` handles cached `.html` files from markdown conversion
- [ ] PDF served inline (no `filename=` argument to `FileResponse`)

---

### 6. `schemas.py` — Update Request Schemas

**File**: `backend/app/schemas.py`

**Changes**:

```python
class SearchRequest(BaseModel):
    format: Literal["step", "pdf", "dxf", "obj", "doc", "xls", "ppt", "md", "txt", "html"]
    codes: List[str]
    folder_path: Optional[str] = None


class OpenLogRequest(BaseModel):
    file_id: int
    format: Literal["step", "pdf", "dxf", "obj", "doc", "xls", "ppt", "md", "txt", "html"]
```

**Checklist**:
- [ ] `SearchRequest.format` includes all 10 formats
- [ ] `OpenLogRequest.format` includes all 10 formats

---

### 7. `requirements.txt` — Add Dependencies

**File**: `backend/requirements.txt`

**Changes**: Add `markdown`, `python-docx`, `openpyxl`, and `python-pptx` packages:

```
fastapi==0.115.6
uvicorn[standard]==0.32.1
python-jose[cryptography]==3.3.0
pydantic==2.10.4
python-multipart==0.0.20
markdown>=3.0
python-docx>=1.1.0
openpyxl>=3.1.0
python-pptx>=1.0.0
```

**Note**: All dependencies are pure Python packages installable via pip. No system-level dependencies (LibreOffice) required.

---

## Frontend Changes

### 1. `types.ts` — Add New Permission Types

**File**: `frontend/src/types.ts`

**Changes**:

```typescript
export type Permission =
  | 'use_quick_peek'
  | 'view_step'
  | 'view_pdf'
  | 'view_dxf'
  | 'view_obj'
  | 'view_doc'      // NEW
  | 'view_xls'      // NEW
  | 'view_ppt'      // NEW
  | 'view_md'       // NEW
  | 'view_txt'      // NEW
  | 'view_html'     // NEW
  | 'view_dashboard'
  | 'manage_users'
  | 'download_files';

export type Format = 'step' | 'pdf' | 'dxf' | 'obj' | 'doc' | 'xls' | 'ppt' | 'md' | 'txt' | 'html';  // Updated

export type FileItem = {
  // ... existing fields ...
  preview_kind: 'pdf' | 'svg' | 'glb' | 'step' | 'obj' | 'unknown' | 'html' | 'txt';  // Added 'html', 'txt'
};
```

**Checklist**:
- [ ] All new permissions added to `Permission` type
- [ ] `Format` type expanded to 10 options
- [ ] `FileItem.preview_kind` includes `'html'` and `'txt'`

---

### 2. `QuickPeekPage.tsx` — Update Format Selector

**File**: `frontend/src/pages/QuickPeekPage.tsx`

**Changes**:

```typescript
const formats: { id: Format; label: string; exts: string; permission: string }[] = [
  { id: 'step', label: 'STEP', exts: '.stp .step', permission: 'view_step' },
  { id: 'pdf', label: 'PDF', exts: '.pdf', permission: 'view_pdf' },
  { id: 'dxf', label: 'DXF', exts: '.dxf', permission: 'view_dxf' },
  { id: 'obj', label: 'OBJ', exts: '.obj', permission: 'view_obj' },
  { id: 'doc', label: 'Word', exts: '.doc .docx', permission: 'view_doc' },    // NEW
  { id: 'xls', label: 'Excel', exts: '.xls .xlsx', permission: 'view_xls' },  // NEW
  { id: 'ppt', label: 'PowerPoint', exts: '.ppt .pptx', permission: 'view_ppt' },  // NEW
  { id: 'md', label: 'Markdown', exts: '.md', permission: 'view_md' },        // NEW
  { id: 'txt', label: 'Text', exts: '.txt', permission: 'view_txt' },        // NEW
  { id: 'html', label: 'HTML', exts: '.html .htm', permission: 'view_html' }, // NEW
];
```

**Checklist**:
- [ ] All 10 formats have entries in the `formats` array
- [ ] Labels are user-friendly ("Word", "Excel", "PowerPoint" rather than "doc", "xls", "ppt")
- [ ] Extensions listed for each format
- [ ] `canView()` function checks new permissions

---

### 3. `ViewerModal.tsx` — Add Handlers for New Formats

**File**: `frontend/src/components/ViewerModal.tsx`

**Changes**:

```typescript
export default function ViewerModal({ code, format, file, onClose }: { code: string; format: Format; file: FileItem; onClose: () => void }) {
  useEffect(() => {
    api('/api/usage/open', { method: 'POST', body: JSON.stringify({ file_id: file.file_id, format }) }).catch(() => null);
  }, [file.file_id, format]);

  const previewUrl = withToken(file.preview_url);
  const rawUrl = withToken(file.raw_url);

  // For text-based formats, use a text-aware iframe
  const textViewUrl = format === 'md' || format === 'html'
    ? previewUrl
    : format === 'txt'
    ? previewUrl
    : null;

  return (
    <div className="modal-backdrop" onMouseDown={onClose}>
      <div className="viewer-modal" onMouseDown={(e) => e.stopPropagation()}>
        {/* ... header with code, filename, message ... */}

        <div className="viewer-body">
          {format === 'step' && file.preview_kind === 'glb' && <StepViewer url={previewUrl} />}
          {format === 'step' && file.preview_kind !== 'glb' && <PanZoomImage url={previewUrl} label="STEP placeholder preview" />}
          {format === 'pdf' && <iframe className="pdf-frame" src={`${previewUrl}#toolbar=1&navpanes=0&scrollbar=1&page=1&view=FitH`} title={file.filename} />}
          {format === 'dxf' && <DxfVectorViewer url={previewUrl} label="DXF preview" />}
          {format === 'obj' && <ObjViewer url={previewUrl} />}
          {(format === 'md' || format === 'html') && (
            <iframe className="pdf-frame" src={previewUrl} title={file.filename} />
          )}
          {format === 'txt' && (
            <iframe className="pdf-frame" src={previewUrl} title={file.filename} />
          )}
          {/* Office formats (doc, xls, ppt) render as HTML */}
          {(format === 'doc' || format === 'xls' || format === 'ppt') && (
            <iframe className="pdf-frame" src={previewUrl} title={file.filename} />
          )}
        </div>
      </div>
    </div>
  );
}
```

**Checklist**:
- [ ] `md` renders as iframe (HTML output)
- [ ] `html` renders as iframe (direct HTML)
- [ ] `txt` renders as iframe (plain text)
- [ ] `doc`, `xls`, `ppt` render as PDF iframe
- [ ] Usage open logged for all formats

---

### 4. `PreviewCard.tsx` — Handle New preview_kind Values

**File**: `frontend/src/components/PreviewCard.tsx`

**Changes**: The existing thumbnail rendering should work for most cases since `md`/`html`/`txt` will return `preview_kind` values the existing code can handle. However, verify:

```typescript
// Ensure thumbnail rendering handles all preview_kind values:
// - 'pdf' → iframe (existing)
// - 'svg' → img (existing)
// - 'glb' → 3D icon (existing)
// - 'obj' → 3D icon (existing)
// - 'html' → img or iframe (NEW - may need adjustment)
// - 'txt' → img (existing, will show broken icon — acceptable)
// - 'step' → placeholder icon (existing)
// - 'unknown' → empty/placeholder (existing)
```

**Checklist**:
- [ ] `html` preview_kind renders acceptably in thumbnail
- [ ] `txt` preview_kind renders acceptably (text files won't have thumbnails — this is expected)

---

## Testing Checklist

### Format-by-Format Testing

#### PDF (.pdf)
- [ ] Search returns results for valid codes
- [ ] Clicking card opens ViewerModal
- [ ] PDF renders inline in iframe
- [ ] Toolbar visible (zoom, page navigation)
- [ ] Download button works

#### Word (.doc, .docx)
- [ ] Search returns results for valid codes
- [ ] Preview converts to HTML (check `cache/previews/` for `.html` file)
- [ ] HTML renders inline in iframe
- [ ] If python-docx unavailable: "Conversion unavailable" message shown
- [ ] Large file (>100MB): "Conversion unavailable" message

#### Excel (.xls, .xlsx)
- [ ] Same as Word, but for spreadsheet
- [ ] Multiple sheets handled correctly
- [ ] Cell data extracted properly

#### PowerPoint (.ppt, .pptx)
- [ ] Same as Word, but for presentations
- [ ] Slides and text content extracted correctly

#### Markdown (.md)
- [ ] Search returns results
- [ ] Preview generates `.html` in cache
- [ ] Markdown renders correctly with:
  - [ ] Code blocks with syntax highlighting
  - [ ] Tables
  - [ ] Fenced code
  - [ ] Blockquotes
  - [ ] Images (if local paths)
- [ ] If `markdown` library unavailable: "Conversion failed" message

#### Plain Text (.txt)
- [ ] Search returns results
- [ ] Preview serves raw text file
- [ ] Text displays in iframe
- [ ] Large text files scroll correctly

#### HTML (.html, .htm)
- [ ] Search returns results
- [ ] Preview serves raw HTML
- [ ] HTML renders correctly in iframe
- [ ] Scripts don't execute (sandboxed by iframe)

### Edge Cases

- [ ] File deleted after indexing → Preview returns 404
- [ ] File moved after indexing → Preview returns 404 (or new path if re-indexed)
- [ ] File modified after indexing → New cache entry created
- [ ] Very long filenames → Truncated in UI, not broken
- [ ] Non-UTF-8 text files → Served with `errors="ignore"` in converter
- [ ] LibreOffice crashes during conversion → Returns False, message shown
- [ ] Multiple users preview same file simultaneously → Both get same cached PDF
- [ ] User without permission tries to search → 403 error returned
- [ ] User without permission views URL directly → 401/403 error

### Permission Testing

- [ ] User with `view_doc` but not `view_xls` can search doc, not xls
- [ ] Admin can search all formats
- [ ] Format buttons disabled for unpermitted formats
- [ ] New user created with no extra permissions → Has all `DEFAULT_USER_PERMISSIONS`

### Performance Testing

- [ ] First preview of a 10MB Word doc: < 5 seconds (conversion)
- [ ] Subsequent preview of same file: < 500ms (cache hit)
- [ ] PDF files > 100MB: Not converted, message shown
- [ ] 50 concurrent previews: System remains responsive

---

## Error Handling Summary

| Scenario | Backend Behavior | Frontend Behavior |
|---------|-----------------|-------------------|
| Office library not installed | `office_to_html()` returns `False` | ViewerModal shows "Conversion unavailable" |
| File too large (>MAX_CONVERT_SIZE_MB) | `office_to_html()` returns `False` | ViewerModal shows "Conversion unavailable" |
| Markdown library not installed | `markdown_to_html()` returns `False` | ViewerModal shows "Markdown conversion failed" |
| File deleted after indexing | `preview_file()` raises 404 | Error message shown |
| No permission | `search()` raises 403 | Format button disabled |
| Conversion produces empty file | `office_to_html()` returns `False` | ViewerModal shows message |

---

## Rollout Checklist

- [ ] Install `markdown` package: `pip install markdown`
- [ ] Install `python-docx`: `pip install python-docx`
- [ ] Install `openpyxl`: `pip install openpyxl`
- [ ] Install `python-pptx`: `pip install python-pptx`
- [ ] Set `QUICKPEEK_MAX_CONVERT_SIZE_MB` if default 100MB is too high/low
- [ ] Restart backend service
- [ ] Clear browser cache (if any frontend caching issues)
- [ ] Verify admin has all new permissions
- [ ] Verify default users have new permissions
- [ ] Test with a real Office document
- [ ] Test with a real Markdown file