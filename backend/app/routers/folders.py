from __future__ import annotations

import os
import string
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from ..auth import require_permission
from ..config import BASE_DIR, FILE_ROOTS
from ..db import get_conn, rows_to_dicts, utc_now
from ..schemas import FolderPresetCreate

router = APIRouter(prefix="/api/folders", tags=["folders"])


def _normalize_dir(value: str | None) -> Path:
    raw = (value or "").strip().strip('"')
    if not raw:
        return Path.home() if Path.home().exists() else BASE_DIR
    p = Path(raw).expanduser()
    if not p.is_absolute():
        p = (BASE_DIR / p).resolve()
    return p


def _windows_drives() -> List[str]:
    drives: List[str] = []
    if os.name == "nt":
        for letter in string.ascii_uppercase:
            root = f"{letter}:\\"
            if Path(root).exists():
                drives.append(root)
    return drives


def _seed_roots() -> List[str]:
    roots: List[str] = []
    roots.extend(_windows_drives())
    for p in [Path.home(), BASE_DIR, *FILE_ROOTS]:
        try:
            if p.exists() and p.is_dir():
                s = str(p.resolve())
                if s not in roots:
                    roots.append(s)
        except OSError:
            continue
    if not roots:
        roots.append(str(Path.cwd()))
    return roots


@router.get("/browse")
def browse_folder(path: Optional[str] = Query(default=None), user=Depends(require_permission("use_quick_peek"))):
    folder = _normalize_dir(path)
    if not folder.exists():
        raise HTTPException(status_code=404, detail="Folder does not exist")
    if not folder.is_dir():
        raise HTTPException(status_code=400, detail="Path is not a folder")

    items = []
    try:
        for child in folder.iterdir():
            try:
                if child.is_dir():
                    items.append({
                        "name": child.name or str(child),
                        "path": str(child.resolve()),
                    })
            except OSError:
                continue
    except PermissionError:
        raise HTTPException(status_code=403, detail="No permission to read this folder")
    except OSError as exc:
        raise HTTPException(status_code=400, detail=f"Cannot read folder: {exc}")

    items.sort(key=lambda x: x["name"].lower())
    parent = None
    try:
        if folder.parent != folder:
            parent = str(folder.parent.resolve())
    except OSError:
        parent = None

    return {
        "path": str(folder.resolve()),
        "parent": parent,
        "roots": _seed_roots(),
        "items": items,
    }


@router.get("/presets")
def list_presets(user=Depends(require_permission("use_quick_peek"))):
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, name, path, created_at, updated_at
            FROM folder_presets
            WHERE user_id = ?
            ORDER BY name COLLATE NOCASE
            """,
            (user["id"],),
        ).fetchall()
    return {"presets": rows_to_dicts(rows)}


@router.post("/presets")
def save_preset(payload: FolderPresetCreate, user=Depends(require_permission("use_quick_peek"))):
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Preset name is required")
    folder = _normalize_dir(payload.path)
    if not folder.exists() or not folder.is_dir():
        raise HTTPException(status_code=400, detail="Preset path must be an existing folder")

    now = utc_now()
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO folder_presets (user_id, name, path, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id, name) DO UPDATE SET
                path=excluded.path,
                updated_at=excluded.updated_at
            """,
            (user["id"], name, str(folder.resolve()), now, now),
        )
        row = conn.execute(
            "SELECT id, name, path, created_at, updated_at FROM folder_presets WHERE user_id = ? AND name = ?",
            (user["id"], name),
        ).fetchone()
    return {"preset": dict(row)}


@router.delete("/presets/{preset_id}")
def delete_preset(preset_id: int, user=Depends(require_permission("use_quick_peek"))):
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM folder_presets WHERE id = ? AND user_id = ?", (preset_id, user["id"]))
    return {"ok": cur.rowcount > 0}
