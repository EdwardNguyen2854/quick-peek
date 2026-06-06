# Decision Log — Document Preview Feature

> **Quick Peek v0.3** — Document Preview Release

---

## Pure Python over LibreOffice for Office Conversion

### Decision (v0.3 supersedes earlier decision)
Use **pure Python libraries** (python-docx, openpyxl, python-pptx) to convert Office documents to **HTML** instead of LibreOffice headless conversion to PDF.

### Rationale

1. **No system dependency**: LibreOffice requires system-level installation on the server. Pure Python libraries install via pip and work anywhere Python runs.

2. **Cross-platform without setup**: With pip packages, there's no need to detect OS-specific paths (e.g., `/Applications/LibreOffice.app` on macOS, `soffice` on Linux, `C:\Program Files\LibreOffice\...` on Windows).

3. **Works offline**: No external binaries needed. Works in isolated/air-gapped environments where LibreOffice cannot be installed.

4. **Simpler deployment**: One `pip install -r requirements.txt` command handles all dependencies. No need for system package managers or manual LibreOffice installation.

5. **HTML output is browser-native**: Browsers render HTML natively without plugins. PDF requires the browser's PDF viewer which may vary in quality.

6. **Sufficient for preview**: The goal is document preview (readability), not perfect fidelity reproduction. HTML extraction preserves text content and basic formatting.

### Alternatives Considered

| Alternative | Why Rejected |
|-------------|--------------|
| LibreOffice headless → PDF | Requires system-level installation. More complex detection logic. PDF rendering varies by browser. |
| `Aspose.Total` | Commercial license required. Overkill for text extraction. |
| `unoconv` | Wrapper around LibreOffice but less reliable and not actively maintained. |
| Microsoft Office COM automation | Windows-only. Requires Office installed on server. Not cross-platform. |
| No conversion (placeholder only) | Rejected — the core value of this release is preview capability. |

### Consequences
- **Python package dependencies**: `python-docx`, `openpyxl`, and `python-pptx` must be in `requirements.txt`.
- **Limited fidelity**: HTML extraction cannot perfectly replicate complex Word/Excel/PowerPoint formatting (macros, advanced graphics, formulas).
- **HTML output**: All Office formats convert to HTML, not PDF. Browser renders HTML directly.
- **Graceful degradation**: If a library fails to import or convert, users see a "Conversion unavailable" message.

---

## ~~LibreOffice for Office Format Conversion~~

> **SUPERSEDED** — This decision has been replaced by "Pure Python over LibreOffice for Office Conversion" (v0.3). The implementation uses python-docx/openpyxl/python-pptx instead of LibreOffice headless.

### Decision
Use **LibreOffice headless** as the Office-to-PDF conversion engine for `.doc`, `.docx`, `.xls`, `.xlsx`, `.ppt`, `.pptx` files.

### Rationale

1. **Universal format support**: LibreOffice handles all Microsoft Office formats reliably, including legacy `.doc`, `.xls`, `.ppt` formats that other tools struggle with.

2. **Cross-platform**: Works on macOS, Linux, and Windows without code changes. The auto-detection covers all three platforms.

3. **PDF output quality**: LibreOffice produces reliable, consistent PDF output suitable for in-app viewing.

4. **No library dependencies**: Uses the installed LibreOffice application rather than a Python library (e.g., `python-docx` for Word only, `openpyxl` for Excel only), avoiding the need for multiple format-specific libraries.

5. **Industry standard**: LibreOffice is the de facto standard for headless Office conversion on servers.

### Alternatives Considered

| Alternative | Why Rejected |
|-------------|--------------|
| `python-docx` + `openpyxl` + `python-pptx` | Each library handles one format. Would require 3 separate conversion paths. No PDF generation. |
| `Aspose.Total` | Commercial license required. Overkill for this use case. |
| `unoconv` | Wrapper around LibreOffice but less reliable and not actively maintained. |
| Microsoft Office COM automation | Windows-only. Requires Office installed on server. Not cross-platform. |
| `pandoc` | Good for docx→HTML but doesn't handle Excel/PowerPoint. |
| No conversion (placeholder only) | Rejected — the core value of this release is preview capability. |

### Consequences
- **Dependency**: Requires LibreOffice to be installed on the server for Office format previews.
- **Graceful degradation**: If LibreOffice is unavailable, users see a "Conversion not available" message.
- **Performance**: Conversion is synchronous and on-demand. Large files may take 10-30 seconds.

---

## Markdown Package for .md Conversion

### Decision
Use the Python **`markdown`** library (from PyPI) for Markdown-to-HTML conversion.

### Rationale

1. **Pure Python**: No system dependencies, works everywhere Python runs.

2. **Extensible**: Supports extensions for GitHub-flavored features (`fenced_code`, `tables`, `codehilite`).

3. **Well-maintained**: The `markdown` package is the standard Markdown processor for Python.

4. **Lightweight**: Simple API — `markdown.markdown(content, extensions=[...])`.

5. **Styling flexibility**: Can inject custom CSS for consistent, branded styling.

### Alternatives Considered

| Alternative | Why Rejected |
|-------------|--------------|
| `mistune` | Also pure Python, but `markdown` has more extensions and wider adoption. |
| `CommonMark` parser | Too low-level; would require implementing all extensions manually. |
| `panDoc` | Excellent but a system dependency, same problem as LibreOffice. |
| Frontend rendering (e.g., `marked`) | Rejected — converting on the backend allows caching and consistent styling. |
| No conversion (raw text) | Rejected — Markdown files deserve proper rendering. |

### Consequences
- **Python package dependency**: The `markdown` package must be in `requirements.txt`.
- **Graceful degradation**: If `markdown` import fails, returns `False` and shows "Unsupported format".

---

## Format Grouping: doc, xls, ppt as Separate Types

### Decision
Use **three separate format types** (`doc`, `xls`, `ppt`) rather than a single `office` type or grouping by conversion method.

### Rationale

1. **User mental model**: Users think in terms of Word documents, Excel spreadsheets, and PowerPoint presentations — not "Office files".

2. **Permission granularity**: Allows fine-grained access control (e.g., user can preview Excel files but not Word docs).

3. **Frontend UX**: Separate format cards in the UI map directly to these types.

4. **Database efficiency**: The `files.extension` column stores the actual extension (`.docx`), and the format grouping is a logical layer on top.

### Alternatives Considered

| Alternative | Why Rejected |
|-------------|--------------|
| Single `office` type | Would混mix different file types under one search. Less intuitive. |
| All Office under `pdf` | Would hide the source format. Permissions become coarse-grained. |

### Consequences
- Each format type has its own search endpoint and permission check.
- The `FORMAT_PERMISSION` dict maps each format to its corresponding permission string.
- Frontend format selector has 10 items (step, pdf, dxf, obj, doc, xls, ppt, md, txt, html).

---

## Cache Invalidation via file_key (mtime + size)

### Decision
Use `file_key()` — a SHA-256 hash of the file's **absolute path + mtime + size** — as the cache key for all converted previews.

```python
def file_key(path: Path) -> str:
    st = path.stat()
    src = f"{path.resolve()}|{st.st_mtime}|{st.st_size}".encode("utf-8", errors="ignore")
    return hashlib.sha256(src).hexdigest()[:24]
```

### Rationale

1. **Automatic invalidation**: Any edit to a file changes its mtime and/or size, producing a new cache key. No manual cache purge needed.

2. **Collision-resistant**: SHA-256 hash of path+mtime+size is effectively unique across all practical file sets.

3. **No database dependency**: Doesn't require querying SQLite to check if a cached file is valid.

4. **Simple**: One function handles all formats uniformly.

5. **Storage efficiency**: Only stores the converted file, not metadata. Cache is just a directory of files.

### Alternatives Considered

| Alternative | Why Rejected |
|-------------|--------------|
| Store cache metadata in SQLite | More complex. Would need to track cache entries on file update/delete. |
| Check file mtime at request time | Would require reading file stat on every request, even when cache exists. |
| TTL-based expiration | Files could be edited and still show stale preview until TTL expires. |
| Content hash (MD5 of file) | Would require reading the entire file to compute hash. |

### Consequences
- Old cached files accumulate in `cache/previews/` when source files are deleted or moved.
- The cache directory grows over time but has no negative impact (files are small).
- No cache purge mechanism exists (not needed given automatic invalidation).

---

## Graceful Degradation When LibreOffice Unavailable

### Decision
When LibreOffice is not installed or the `QUICKPEEK_LIBREOFFICE_CMD` path is invalid, Office format searches return results normally but previews show a "Conversion not available" message instead of an error.

### Rationale

1. **User experience**: The app should still be **searchable** even without preview conversion. Users can still find files by code and download them via the raw file endpoint.

2. **No hard failures**: A missing LibreOffice installation should not crash the app or prevent it from starting.

3. **Clear messaging**: The `message` field in `FileItem` tells the user exactly why the preview is unavailable.

4. **Operational flexibility**: Some deployments may intentionally omit LibreOffice (e.g., no Office files in the organization).

### Implementation

```python
def office_to_pdf(input_path: Path, output_path: Path, timeout: int = 120) -> bool:
    lo_cmd = _find_libreoffice()
    if not lo_cmd:
        return False  # ← Graceful: returns False, not an exception
    # ... conversion ...
```

In `ensure_preview()`:
```python
if file_format in ("doc", "xls", "ppt"):
    out = PREVIEW_DIR / f"{key}.pdf"
    if not out.exists():
        ok = office_to_pdf(path, PREVIEW_DIR / f"{key}.pdf")
        if not ok:
            return {"kind": "unknown", "ready": False, "message": "Conversion unavailable. Download the file to view.", "cache_file": None}
    return {"kind": "pdf", "ready": True, "cache_file": str(out)}
```

### Alternatives Considered

| Alternative | Why Rejected |
|-------------|--------------|
| Raise HTTP 503 error | Too aggressive. The file exists; the user should be able to download it. |
| Block search for Office formats | Would make Office files undiscoverable without LibreOffice. |
| Install LibreOffice via dependency | Not practical — LibreOffice is a system package, not a Python package. |

### Consequences
- Office files are searchable but not previewable without LibreOffice.
- Users see a clear message in the ViewerModal explaining the limitation.
- The raw download endpoint always works regardless of conversion availability.

---

## Direct Serve for txt/html (No Conversion)

### Decision
Serve `.txt` and `.html` files **directly** from their original location with the appropriate MIME type, rather than converting them.

### Rationale

1. **txt is already plain text**: No conversion needed. `text/plain` is universally supported.

2. **html is already rendered**: HTML files are already in the correct format for browser rendering.

3. **Performance**: No conversion step = instant preview.

4. **No cache needed**: The original file IS the preview.

### Implementation

In `preview_file()`:
```python
if p["kind"] in ("txt", "html"):
    return FileResponse(
        Path(item["full_path"]),
        media_type="text/plain" if p["kind"] == "txt" else "text/html"
    )
```

### Consequences
- `.txt` and `.html` files preview instantly with no caching overhead.
- If a file is moved/deleted after indexing, the preview returns 404.

---

## PDF as Direct Serve (No Cache)

### Decision
PDF files are served directly using `FileResponse` pointing to the original file path, with `media_type="application/pdf"`.

### Rationale

1. **PDF is already browser-ready**: No conversion needed. Browsers have built-in PDF renderers.

2. **No conversion overhead**: Instant preview.

3. **No cache needed**: The original file is the preview.

4. **Inline display**: By not passing a `filename` to `FileResponse`, the PDF displays inline rather than downloading (important for the in-app viewer).

### Implementation

```python
if p["kind"] == "pdf":
    return FileResponse(Path(item["full_path"]), media_type="application/pdf")
```

### Consequences
- PDF preview depends on the original file remaining accessible.
- If the file is deleted after indexing, preview returns 404.
- No PDF-specific permission beyond `view_pdf`.

---

## Format-Specific Permission per Type

### Decision
Each format type has its **own permission string** (e.g., `view_doc`, `view_xls`) rather than a single `view_documents` permission or inheriting from a base permission.

### Rationale

1. **Fine-grained access control**: Organizations may want to allow Excel previews but not Word documents (confidentiality).

2. **Matches user mental model**: Users see separate buttons for each format in the UI.

3. **Admin management**: Permissions can be assigned per-format in the admin panel.

### Alternatives Considered

| Alternative | Why Rejected |
|-------------|--------------|
| Single `view_documents` permission | Too coarse. All Office formats would share the same access. |
| `view_pdf` applies to all converted formats | Wrong — PDF is already a distinct format. |
| All formats require only `use_quick_peek` | Too permissive. |

### Consequences
- Admin must grant each format permission explicitly to users.
- Default users get all format permissions (view_doc, view_xls, view_ppt, etc.).
- Frontend disables format buttons for unpermitted formats.

---

## Summary Table

| Decision | Chosen Approach | Key Benefit |
|----------|-----------------|-------------|
| Office converter | `python-docx` + `openpyxl` + `python-pptx` → HTML | No system deps, pure Python, works offline |
| Markdown converter | `markdown` library | Pure Python, extensible, lightweight |
| Format grouping | Separate doc/xls/ppt | User mental model, fine-grained permissions |
| Cache invalidation | file_key (path+mtime+size) | Automatic, no DB dependency |
| Office fallback | Graceful degradation | App still usable, clear message |
| txt/html serve | Direct serve | Instant, no conversion overhead |
| PDF serve | Direct serve | Instant, browser-native rendering |
| Permissions | Per-format | Fine-grained access control |