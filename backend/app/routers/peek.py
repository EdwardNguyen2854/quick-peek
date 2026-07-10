from __future__ import annotations

import fnmatch
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from ..auth import current_user, require_permission
from ..config import APP_SECONDS_PER_FILE, FOLDER_DEFAULT_ALLOW, MANUAL_SECONDS_PER_FILE
from ..db import get_conn, json_dumps, row_to_dict, utc_now
from ..file_index import index_folder, search_index
from ..preview import ensure_preview
from ..schemas import OpenLogRequest, SearchRequest

router = APIRouter(prefix="/api", tags=["peek"])

FORMAT_PERMISSION = {
    "step": "view_step",
    "pdf": "view_pdf",
    "dxf": "view_dxf",
    "obj": "view_obj",
    "doc": "view_doc",
    "xls": "view_xls",
    "ppt": "view_ppt",
    "md": "view_md",
    "txt": "view_txt",
    "html": "view_html",
}


def _file_payload(row: dict, file_format: str) -> dict:
    preview = ensure_preview(row, file_format)
    kind = preview["kind"]
    return {
        "file_id": row["id"],
        "filename": row["filename"],
        "extension": row["extension"],
        "size_bytes": row["size_bytes"],
        "modified_at": row["modified_at"],
        "preview_kind": kind,
        "preview_ready": bool(preview["ready"]),
        "message": preview["message"],
        "preview_url": f"/api/files/{row['id']}/preview?format={file_format}",
        "raw_url": f"/api/files/{row['id']}/raw",
    }


@router.post("/peek/search")
def search(payload: SearchRequest, user=Depends(require_permission("use_quick_peek"))):
    permissions = user.get("permissions", [])
    if user.get("role") != "admin" and FORMAT_PERMISSION[payload.format] not in permissions:
        raise HTTPException(status_code=403, detail=f"Missing permission: {FORMAT_PERMISSION[payload.format]}")

    cleaned = []
    seen = set()
    for code in payload.codes:
        c = code.strip()
        if c and c not in seen:
            cleaned.append(c); seen.add(c)

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

    indexed_results = search_index(payload.format, cleaned, root_path=folder_path)
    results = []
    files_found = 0
    for item in indexed_results:
        matches = item["matches"]
        files_found += len(matches)
        files = [_file_payload(m, payload.format) for m in matches[:5]]
        status = "not_found" if not matches else ("multiple_matches" if len(matches) > 1 else "found")
        results.append({
            "code": item["code"],
            "status": status,
            "matches_count": len(matches),
            "files": files,
        })

    seconds_saved = max(0, MANUAL_SECONDS_PER_FILE - APP_SECONDS_PER_FILE) * files_found
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO usage_logs (user_id, action, format, codes_count, files_found, seconds_saved, details_json, created_at)
            VALUES (?, 'search', ?, ?, ?, ?, ?, ?)
            """,
            (user["id"], payload.format, len(cleaned), files_found, seconds_saved, json_dumps({"codes": cleaned[:200], "folder_path": folder_path}), utc_now()),
        )
    return {"format": payload.format, "codes_count": len(cleaned), "files_found": files_found, "folder_path": folder_path, "results": results}


@router.post("/usage/open")
def log_open(payload: OpenLogRequest, user=Depends(require_permission("use_quick_peek"))):
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO usage_logs (user_id, action, format, codes_count, files_found, seconds_saved, details_json, created_at)
            VALUES (?, 'open_preview', ?, 0, 1, 0, ?, ?)
            """,
            (user["id"], payload.format, json_dumps({"file_id": payload.file_id}), utc_now()),
        )
    return {"ok": True}


def _media_type_for_extension(extension: str) -> Optional[str]:
    ext = extension.lower().lstrip(".")
    if ext == "pdf":
        return "application/pdf"
    if ext == "dxf":
        return "application/dxf"
    if ext in {"stp", "step"}:
        return "application/step"
    if ext == "obj":
        return "model/obj"
    return None


# ── Folder scope access control (v0.4) ──────────────────────────────────


def _normalize_path(full_path: str) -> str:
    """Normalize a file path for pattern matching: forward slashes, resolved."""
    try:
        return str(Path(full_path).resolve())
    except (OSError, ValueError):
        return str(full_path).replace("\\", "/")


def _pattern_matches(pattern: str, normalized_path: str) -> bool:
    """Check if a path matches a glob pattern. Supports ** for recursive."""
    pat = pattern.replace("\\", "/")
    norm = normalized_path.replace("\\", "/")
    if "**" in pat:
        parts = pat.split("**")
        prefix = parts[0]
        suffix = parts[-1] if len(parts) > 1 else ""
        if norm.startswith(prefix) and (not suffix or norm.endswith(suffix)):
            return True
        # Also try fnmatch substitution
        simple = pat.replace("**", "*")
        if fnmatch.fnmatch(norm, simple):
            return True
        return False
    return fnmatch.fnmatch(norm, pat)


def can_access_folder(
    user: Dict[str, Any],
    full_path: str,
    permission: str = "view",
) -> bool:
    """
    Check if a user can access a file at full_path with the given permission.
    Admin role bypasses all folder checks.

    Composition:
      1. Admin → True
      2. Deny rules (deny wins)
      3. Allow rules
      4. Default (FOLDER_DEFAULT_ALLOW)
    """
    # 1. Admin bypass
    if user.get("role") == "admin":
        return True

    normalized = _normalize_path(full_path)

    # 2. Determine principal type and ID
    if user.get("auth_source") == "api_key":
        principal_type = "api_key"
        principal_id = str(user.get("api_key_id", ""))
    else:
        principal_type = "user"
        principal_id = str(user["id"])

    # 3. Fetch matching grants
    with get_conn() as conn:
        grants = conn.execute(
            """
            SELECT fg.*, fs.pattern
            FROM folder_grants fg
            JOIN folder_scopes fs ON fs.id = fg.scope_id
            WHERE fg.principal_type = ? AND fg.principal_id = ?
            """,
            (principal_type, principal_id),
        ).fetchall()

    # 4. Check deny rules first (deny always wins)
    for g in grants:
        if g["effect"] == "deny" and g["permission"] == permission:
            if _pattern_matches(g["pattern"], normalized):
                return False

    # 5. Check allow rules
    for g in grants:
        if g["effect"] == "allow" and g["permission"] == permission:
            if _pattern_matches(g["pattern"], normalized):
                return True

    # 6. Default
    return FOLDER_DEFAULT_ALLOW


@router.get("/files/{file_id}/raw")
def raw_file(file_id: int, user=Depends(current_user)):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM files WHERE id = ?", (file_id,)).fetchone()
    item = row_to_dict(row)
    if not item:
        raise HTTPException(status_code=404, detail="File not found")
    path = Path(item["full_path"])
    if not path.exists():
        raise HTTPException(status_code=404, detail="File missing on disk")

    # v0.4: Folder scope + download permission check (P0 fix)
    if not can_access_folder(user, item["full_path"], "download"):
        raise HTTPException(status_code=403, detail="Folder scope denies download access")
    if user.get("role") != "admin" and "download_files" not in (user.get("permissions") or []):
        raise HTTPException(status_code=403, detail="Missing permission: download_files")

    # Raw file endpoint is intentionally a download. The preview endpoint below is inline.
    return FileResponse(
        path,
        filename=item["filename"],
        media_type=_media_type_for_extension(item.get("extension", "")),
        content_disposition_type="attachment",
    )


@router.get("/files/{file_id}/preview")
def preview_file(file_id: int, format: str, user=Depends(current_user)):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM files WHERE id = ?", (file_id,)).fetchone()
    item = row_to_dict(row)
    if not item:
        raise HTTPException(status_code=404, detail="File not found")

    # v0.4: Folder scope check (P0 fix)
    if not can_access_folder(user, item["full_path"], "view"):
        raise HTTPException(status_code=403, detail="Folder scope denies view access")
    p = ensure_preview(item, format)
    if p["kind"] == "pdf":
        # Do not pass filename here. Starlette/FastAPI adds Content-Disposition when
        # filename is supplied, and many browsers treat that as a download.
        # This endpoint is for in-app viewing, so return it inline.
        return FileResponse(Path(item["full_path"]), media_type="application/pdf")
    if p["kind"] == "obj":
        # OBJ is a mesh format that Three.js can load directly. Keep it inline for the in-app viewer.
        return FileResponse(Path(item["full_path"]), media_type="model/obj")
    if p["kind"] == "txt":
        # Serve raw text file with text/plain content type
        return FileResponse(Path(item["full_path"]), media_type="text/plain; charset=utf-8")
    if p["kind"] == "html":
        # Serve from cache if exists, else serve raw file
        if p.get("cache_file"):
            cache_path = Path(str(p["cache_file"]))
            if cache_path.exists():
                return FileResponse(cache_path, media_type="text/html; charset=utf-8")
        return FileResponse(Path(item["full_path"]), media_type="text/html; charset=utf-8")
    if p.get("cache_file"):
        cache_path = Path(str(p["cache_file"]))
        if cache_path.exists():
            media = "image/svg+xml" if cache_path.suffix == ".svg" else "model/gltf-binary"
            return FileResponse(cache_path, media_type=media)
    # STEP placeholder SVG if no conversion has been configured.
    name = item["filename"]
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 400">
      <rect width="600" height="400" fill="white"/>
      <rect x="24" y="24" width="552" height="352" rx="18" fill="#f9fafb" stroke="#e5e7eb"/>
      <text x="48" y="78" font-family="Arial" font-size="22" font-weight="700" fill="#111827">STEP file found</text>
      <text x="48" y="118" font-family="Arial" font-size="14" fill="#4b5563">{name}</text>
      <text x="48" y="162" font-family="Arial" font-size="13" fill="#6b7280">Configure STEP → GLB conversion for browser 3D preview.</text>
      <path d="M265 250 L340 210 L415 250 L340 292 Z" fill="#fff" stroke="#111827"/>
      <path d="M265 250 L265 175 L340 135 L340 210 Z" fill="#f3f4f6" stroke="#111827"/>
      <path d="M340 210 L340 135 L415 175 L415 250 Z" fill="#e5e7eb" stroke="#111827"/>
    </svg>"""
    from fastapi.responses import Response
    return Response(svg, media_type="image/svg+xml")
