from __future__ import annotations

import hashlib
import threading
from pathlib import Path
from typing import Dict

from .cache_eviction import evict_preview_cache, mark_preview_accessed
from .config import LIBREOFFICE_CMD, MAX_CONVERT_SIZE_MB, PREVIEW_DIR
from .converters.markdown_to_html import markdown_to_html
from .converters.office_to_html import office_to_html
from .dxf_preview import dxf_to_svg


def file_key(path: Path) -> str:
    st = path.stat()
    src = f"{path.resolve()}|{st.st_mtime}|{st.st_size}".encode("utf-8", errors="ignore")
    return hashlib.sha256(src).hexdigest()[:24]


_legacy_conversions_inflight: set[str] = set()


def schedule_legacy_conversion(path: Path, out: Path) -> None:
    """Convert a legacy Office file off the request path, one attempt per file."""
    cache_key = str(out)
    if cache_key in _legacy_conversions_inflight:
        return
    _legacy_conversions_inflight.add(cache_key)

    def _run() -> None:
        try:
            if office_to_html(path, out):
                evict_preview_cache()
        finally:
            _legacy_conversions_inflight.discard(cache_key)

    threading.Thread(target=_run, daemon=True).start()


def ensure_preview(file_row: dict, file_format: str) -> Dict[str, str | bool | None]:
    path = Path(file_row["full_path"])
    key = file_key(path)
    if file_format == "pdf":
        return {"kind": "pdf", "ready": True, "message": None, "cache_file": None}
    if file_format == "dxf":
        out = PREVIEW_DIR / f"{key}.svg"
        if not out.exists():
            try:
                out.write_text(dxf_to_svg(path, path.name), encoding="utf-8")
                evict_preview_cache()
            except Exception as exc:
                out.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 400"><rect width="600" height="400" fill="white"/><text x="30" y="60" font-family="Arial" font-size="18">DXF preview failed</text><text x="30" y="95" font-family="Arial" font-size="13">{str(exc)}</text></svg>', encoding="utf-8")
                return {"kind": "svg", "ready": False, "message": f"DXF preview failed: {exc}", "cache_file": str(out)}
        return {"kind": "svg", "ready": True, "message": None, "cache_file": str(out)}
    if file_format == "step":
        # STEP is tessellated in the browser with OpenCascade WebAssembly.
        return {"kind": "step", "ready": True, "message": None, "cache_file": None}
    if file_format in {"doc", "xls", "ppt"}:
        try:
            size_mb = path.stat().st_size / (1024 * 1024)
            if size_mb > MAX_CONVERT_SIZE_MB:
                return {"kind": file_format, "ready": False, "message": f"File too large ({size_mb:.1f} MB > {MAX_CONVERT_SIZE_MB} MB limit).", "cache_file": None}
        except Exception as exc:
            return {"kind": file_format, "ready": False, "message": f"Could not check file size: {exc}", "cache_file": None}

        out = PREVIEW_DIR / f"{key}.html"
        if out.exists():
            return {"kind": "html", "ready": True, "message": None, "cache_file": str(out)}

        ext = path.suffix.lower()
        if ext in {".docx", ".xlsx", ".pptx"}:
            try:
                if office_to_html(path, out):
                    evict_preview_cache()
                    return {"kind": "html", "ready": True, "message": None, "cache_file": str(out)}
                if not LIBREOFFICE_CMD:
                    return {"kind": file_format, "ready": False, "message": "Preview unavailable. Set QUICKPEEK_LIBREOFFICE_CMD to enable Office preview.", "cache_file": None}
                return {"kind": file_format, "ready": False, "message": "Office document preview conversion failed.", "cache_file": None}
            except Exception as exc:
                return {"kind": file_format, "ready": False, "message": f"Office conversion failed: {exc}", "cache_file": None}

        if not LIBREOFFICE_CMD:
            return {"kind": file_format, "ready": False, "message": "Preview unavailable. Set QUICKPEEK_LIBREOFFICE_CMD to enable legacy .doc/.xls/.ppt preview.", "cache_file": None}
        schedule_legacy_conversion(path, out)
        return {"kind": file_format, "ready": False, "message": "Preview pending. Legacy Office conversion is running in the background.", "cache_file": None}
    if file_format == "md":
        # Check file size before conversion
        try:
            size_mb = path.stat().st_size / (1024 * 1024)
            if size_mb > MAX_CONVERT_SIZE_MB:
                return {"kind": "md", "ready": False, "message": f"File too large ({size_mb:.1f} MB > {MAX_CONVERT_SIZE_MB} MB limit).", "cache_file": None}
        except Exception as exc:
            return {"kind": "md", "ready": False, "message": f"Could not check file size: {exc}", "cache_file": None}
        out = PREVIEW_DIR / f"{key}.html"
        if out.exists():
            return {"kind": "html", "ready": True, "message": None, "cache_file": str(out)}
        try:
            if markdown_to_html(path, out):
                evict_preview_cache()
                return {"kind": "html", "ready": True, "message": None, "cache_file": str(out)}
            return {"kind": "md", "ready": False, "message": "Markdown to HTML conversion failed.", "cache_file": None}
        except Exception as exc:
            return {"kind": "md", "ready": False, "message": f"Markdown conversion failed: {exc}", "cache_file": None}
    if file_format == "txt":
        # Check file size before returning text content
        try:
            size_mb = path.stat().st_size / (1024 * 1024)
            if size_mb > MAX_CONVERT_SIZE_MB:
                return {"kind": "txt", "ready": False, "message": f"File too large ({size_mb:.1f} MB > {MAX_CONVERT_SIZE_MB} MB limit).", "cache_file": None}
        except Exception as exc:
            return {"kind": "txt", "ready": False, "message": f"Could not check file size: {exc}", "cache_file": None}
        return {"kind": "txt", "ready": True, "message": None, "cache_file": None}
    if file_format == "html":
        return {"kind": "html", "ready": True, "message": None, "cache_file": None}
    return {"kind": "unknown", "ready": False, "message": "Unsupported format", "cache_file": None}
