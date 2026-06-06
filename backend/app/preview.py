from __future__ import annotations

import hashlib
import shlex
import subprocess
from pathlib import Path
from typing import Dict

from .config import MAX_CONVERT_SIZE_MB, PREVIEW_DIR, STEP_CONVERTER_CMD
from .converters.markdown_to_html import markdown_to_html
from .converters.office_to_html import office_to_html
from .dxf_preview import dxf_to_svg


def file_key(path: Path) -> str:
    st = path.stat()
    src = f"{path.resolve()}|{st.st_mtime}|{st.st_size}".encode("utf-8", errors="ignore")
    return hashlib.sha256(src).hexdigest()[:24]


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
            except Exception as exc:
                out.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 400"><rect width="600" height="400" fill="white"/><text x="30" y="60" font-family="Arial" font-size="18">DXF preview failed</text><text x="30" y="95" font-family="Arial" font-size="13">{str(exc)}</text></svg>', encoding="utf-8")
                return {"kind": "svg", "ready": False, "message": f"DXF preview failed: {exc}", "cache_file": str(out)}
        return {"kind": "svg", "ready": True, "message": None, "cache_file": str(out)}
    if file_format == "obj":
        return {"kind": "obj", "ready": True, "message": None, "cache_file": None}
    if file_format == "step":
        out = PREVIEW_DIR / f"{key}.glb"
        if out.exists():
            return {"kind": "glb", "ready": True, "message": None, "cache_file": str(out)}
        if STEP_CONVERTER_CMD:
            try:
                cmd = STEP_CONVERTER_CMD.format(input=str(path), output=str(out))
                subprocess.run(shlex.split(cmd), check=True, timeout=180)
                if out.exists() and out.stat().st_size > 0:
                    return {"kind": "glb", "ready": True, "message": None, "cache_file": str(out)}
                return {"kind": "step", "ready": False, "message": "Converter ran but did not create GLB output.", "cache_file": None}
            except Exception as exc:
                return {"kind": "step", "ready": False, "message": f"STEP found, but preview conversion failed: {exc}", "cache_file": None}
        return {"kind": "step", "ready": False, "message": "STEP file found. Configure QUICKPEEK_STEP_CONVERTER_CMD to generate browser 3D GLB previews.", "cache_file": None}
    if file_format in {"doc", "xls", "ppt"}:
        # Check file size before conversion
        try:
            size_mb = path.stat().st_size / (1024 * 1024)
            if size_mb > MAX_CONVERT_SIZE_MB:
                return {"kind": file_format, "ready": False, "message": f"File too large ({size_mb:.1f} MB > {MAX_CONVERT_SIZE_MB} MB limit).", "cache_file": None}
        except Exception as exc:
            return {"kind": file_format, "ready": False, "message": f"Could not check file size: {exc}", "cache_file": None}

        out = PREVIEW_DIR / f"{key}.html"
        if out.exists():
            return {"kind": "html", "ready": True, "message": None, "cache_file": str(out)}
        try:
            if office_to_html(path, out):
                return {"kind": "html", "ready": True, "message": None, "cache_file": str(out)}
            return {"kind": file_format, "ready": False, "message": "Office document preview conversion failed. Ensure python-docx, openpyxl, and python-pptx are installed.", "cache_file": None}
        except Exception as exc:
            return {"kind": file_format, "ready": False, "message": f"Office conversion failed: {exc}", "cache_file": None}
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
