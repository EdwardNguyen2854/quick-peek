from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from ..cache_eviction import mark_preview_accessed
from ..db import get_conn, row_to_dict
from ..file_index import index_status, search_index, start_background_index
from ..preview import ensure_preview
from ..schemas import IndexRefreshRequest, SearchRequest
from ..search_engine import normalize_code

router = APIRouter(prefix="/api", tags=["peek"])


def _file_payload(row: dict, requested_format: str) -> dict:
    file_format = row.get("file_format") or requested_format
    preview = ensure_preview(row, file_format)
    return {
        "file_id": row["id"],
        "filename": row["filename"],
        "extension": row["extension"],
        "format": file_format,
        "size_bytes": row["size_bytes"],
        "modified_at": row["modified_at"],
        "preview_kind": preview["kind"],
        "preview_ready": bool(preview["ready"]),
        "message": preview["message"],
        "preview_url": f"/api/files/{row['id']}/preview?format={file_format}",
        "raw_url": f"/api/files/{row['id']}/raw",
        "match_type": row.get("match_type"),
        "match_reason": row.get("match_reason"),
        "revision": row.get("revision_raw"),
        "folder_class": row.get("folder_class") or "normal",
        "full_path": row.get("full_path"),
    }


def _clean_codes(codes: list[str]) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()

    for raw in codes:
        normalized = normalize_code(raw)
        if not normalized.cleaned:
            continue

        key = normalized.compact or normalized.normalized
        if key in seen:
            continue

        seen.add(key)
        cleaned.append(normalized.cleaned)

    return cleaned


def _validated_folder(folder_path: Optional[str]) -> Optional[str]:
    value = (folder_path or "").strip()
    if not value:
        return None

    folder = Path(value).expanduser()
    if not folder.is_absolute():
        folder = folder.resolve()

    if not folder.exists() or not folder.is_dir():
        raise HTTPException(status_code=400, detail="Working folder does not exist or is not a folder")

    return str(folder.resolve())


@router.post("/peek/search")
def search(payload: SearchRequest):
    cleaned = _clean_codes(payload.codes)
    folder_path = _validated_folder(payload.folder_path)

    indexed_results = search_index(payload.format, cleaned, root_path=folder_path)
    results = []
    files_found = 0

    for item in indexed_results:
        matches = item["matches"]
        suggestions = item["suggestions"]
        files_found += len(matches)

        files = [_file_payload(match, payload.format) for match in matches[:5]]
        recommended = files[0] if files else None

        if not matches:
            status = "suggested" if suggestions else "not_found"
        elif len(matches) > 1:
            status = "multiple_matches"
        else:
            status = "found"

        results.append(
            {
                "code": item["code"],
                "normalized_code": item["normalized_code"],
                "status": status,
                "matches_count": item["matches_count"],
                "match_type": recommended.get("match_type") if recommended else None,
                "match_reason": recommended.get("match_reason") if recommended else None,
                "recommended_file": recommended,
                "files": files,
                "suggestions": suggestions,
            }
        )

    return {
        "format": payload.format,
        "codes_count": len(cleaned),
        "files_found": files_found,
        "folder_path": folder_path,
        "index": index_status(),
        "results": results,
    }


@router.get("/index/status")
def get_search_index_status():
    return index_status()


@router.post("/index/refresh")
def refresh_search_index(payload: IndexRefreshRequest):
    folder_path = _validated_folder(payload.folder_path)
    try:
        start_background_index(folder_path=folder_path)
    except PermissionError:
        raise HTTPException(status_code=403, detail="No permission to read the selected folder")
    except OSError as exc:
        raise HTTPException(status_code=400, detail=f"Cannot refresh index: {exc}")

    return {
        "folder_path": folder_path,
        "index": index_status(),
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
    file_format = item.get("file_format") or format
    preview = ensure_preview(item, file_format)

    if preview["kind"] == "step":
        return FileResponse(Path(item["full_path"]), media_type="application/step")
    if preview["kind"] == "pdf":
        return FileResponse(Path(item["full_path"]), media_type="application/pdf")
    if preview["kind"] == "txt":
        return FileResponse(Path(item["full_path"]), media_type="text/plain; charset=utf-8")
    if preview["kind"] == "html":
        if preview.get("cache_file"):
            cache_path = Path(str(preview["cache_file"]))
            if cache_path.exists():
                mark_preview_accessed(cache_path)
                return FileResponse(cache_path, media_type="text/html; charset=utf-8")
        return FileResponse(Path(item["full_path"]), media_type="text/html; charset=utf-8")
    if preview.get("cache_file"):
        cache_path = Path(str(preview["cache_file"]))
        if cache_path.exists() and cache_path.suffix == ".svg":
            mark_preview_accessed(cache_path)
            return FileResponse(cache_path, media_type="image/svg+xml")

    raise HTTPException(status_code=404, detail="Preview is not available")
