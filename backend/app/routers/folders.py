from __future__ import annotations

import os
import string
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from ..config import BASE_DIR, FILE_ROOTS

router = APIRouter(prefix="/api/folders", tags=["folders"])


def _normalize_dir(value: str | None) -> Path:
    raw = (value or "").strip().strip('"')
    if not raw:
        return Path.home() if Path.home().exists() else BASE_DIR
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = (BASE_DIR / path).resolve()
    return path


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
    for path in [Path.home(), BASE_DIR, *FILE_ROOTS]:
        try:
            if path.exists() and path.is_dir():
                value = str(path.resolve())
                if value not in roots:
                    roots.append(value)
        except OSError:
            continue
    if not roots:
        roots.append(str(Path.cwd()))
    return roots


@router.get("/browse")
def browse_folder(path: Optional[str] = Query(default=None)):
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
                    items.append({"name": child.name or str(child), "path": str(child.resolve())})
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
        pass

    return {
        "path": str(folder.resolve()),
        "parent": parent,
        "roots": _seed_roots(),
        "items": items,
    }
