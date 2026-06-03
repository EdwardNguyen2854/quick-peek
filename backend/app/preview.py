from __future__ import annotations

import hashlib
import shlex
import subprocess
from pathlib import Path
from typing import Dict

from .config import PREVIEW_DIR, STEP_CONVERTER_CMD
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
    return {"kind": "unknown", "ready": False, "message": "Unsupported format", "cache_file": None}
