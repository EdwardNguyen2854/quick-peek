from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, Response

from ..db import get_conn, row_to_dict
from ..file_index import index_folder, reindex_files, search_index
from ..preview import ensure_preview
from ..schemas import SearchRequest

router = APIRouter(prefix="/api", tags=["peek"])


def _file_payload(row: dict, file_format: str) -> dict:
    preview = ensure_preview(row, file_format)
    return {
        "file_id": row["id"],
        "filename": row["filename"],
        "extension": row["extension"],
        "size_bytes": row["size_bytes"],
        "modified_at": row["modified_at"],
        "preview_kind": preview["kind"],
        "preview_ready": bool(preview["ready"]),
        "message": preview["message"],
        "preview_url": f"/api/files/{row['id']}/preview?format={file_format}",
        "raw_url": f"/api/files/{row['id']}/raw",
    }


@router.post("/peek/search")
def search(payload: SearchRequest):
    cleaned: list[str] = []
    seen: set[str] = set()
    for code in payload.codes:
        value = code.strip()
        if value and value not in seen:
            cleaned.append(value)
            seen.add(value)

    folder_path = (payload.folder_path or "").strip() or None
    if folder_path:
        folder = Path(folder_path).expanduser()
        if not folder.exists() or not folder.is_dir():
            raise HTTPException(status_code=400, detail="Working folder does not exist or is not a folder")
        try:
            index_folder(folder)
        except PermissionError:
            raise HTTPException(status_code=403, detail="No permission to read working folder")
        except OSError as exc:
            raise HTTPException(status_code=400, detail=f"Cannot index working folder: {exc}")
        folder_path = str(folder.resolve())

    if not folder_path:\n        try:\n            reindex_files()\n        except OSError:\n            pass\n\n    indexed_results = search_index(payload.format, cleaned, root_path=folder_path)
    results = []
    files_found = 0
    for item in indexed_results:
        matches = item["matches"]
        files_found += len(matches)
        files = [_file_payload(match, payload.format) for match in matches[:5]]
        status = "not_found" if not matches else ("multiple_matches" if len(matches) > 1 else "found")
        results.append({
            "code": item["code"],
            "status": status,
            "matches_count": len(matches),
            "files": files,
        })

    return {
        "format": payload.format,
        "codes_count": len(cleaned),
        "files_found": files_found,
        "folder_path": folder_path,
        "results": results,
    }


def _media_type_for_extension(extension: str) -> Optional[str]:
    ext = extension.lower().lstrip(".")
    if ext == "pdf":
        return "application/pdf"
    if ext == "dxf":
        return "application/dxf"
    if ext in {"stp", "step"}:
        return "application/step"
    return None


def _get_file(file_id: int) -> dict:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM files WHERE id = ?", (file_id,)).fetchone()
    item = row_to_dict(row)
    if not item:
        raise HTTPException(status_code=404, detail="File not found")
    if not Path(item["full_path"]).exists():
        raise HTTPException(status_code=404, detail="File missing on disk")
    return item


@router.get("/files/{file_id}/raw")
def raw_file(file_id: int):
    item = _get_file(file_id)
    return FileResponse(
        Path(item["full_path"]),
        filename=item["filename"],
        media_type=_media_type_for_extension(item.get("extension", "")),
        content_disposition_type="attachment",
    )


@router.get("/files/{file_id}/preview")
def preview_file(file_id: int, format: str):
    item = _get_file(file_id)
    preview = ensure_preview(item, format)

    if preview["kind"] == "pdf":
        return FileResponse(Path(item["full_path"]), media_type="application/pdf")
    if preview["kind"] == "txt":
        return FileResponse(Path(item["full_path"]), media_type="text/plain; charset=utf-8")
    if preview["kind"] == "html":
        if preview.get("cache_file"):
            cache_path = Path(str(preview["cache_file"]))
            if cache_path.exists():
                return FileResponse(cache_path, media_type="text/html; charset=utf-8")
        return FileResponse(Path(item["full_path"]), media_type="text/html; charset=utf-8")
    if preview.get("cache_file"):
        cache_path = Path(str(preview["cache_file"]))
        if cache_path.exists():
            media = "image/svg+xml" if cache_path.suffix == ".svg" else "model/gltf-binary"
            return FileResponse(cache_path, media_type=media)

    name = item["filename"]
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 400">
      <rect width="600" height="400" fill="white"/>
      <rect x="24" y="24" width="552" height="352" rx="18" fill="#f9fafb" stroke="#e5e7eb"/>
      <text x="48" y="78" font-family="Arial" font-size="22" font-weight="700" fill="#111827">STEP file found</text>
      <text x="48" y="118" font-family="Arial" font-size="14" fill="#4b5563">{name}</text>
      <text x="48" y="162" font-family="Arial" font-size="13" fill="#6b7280">Configure STEP tessellation → GLB for browser 3D preview.</text>
      <path d="M265 250 L340 210 L415 250 L340 292 Z" fill="#fff" stroke="#111827"/>
      <path d="M265 250 L265 175 L340 135 L340 210 Z" fill="#f3f4f6" stroke="#111827"/>
      <path d="M340 210 L340 135 L415 175 L415 250 Z" fill="#e5e7eb" stroke="#111827"/>
    </svg>"""
    return Response(svg, media_type="image/svg+xml")
