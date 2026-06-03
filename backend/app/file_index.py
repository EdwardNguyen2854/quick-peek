from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from .config import FILE_ROOTS, SUPPORTED_FORMATS
from .db import get_conn, utc_now

ALL_EXTENSIONS = {ext for exts in SUPPORTED_FORMATS.values() for ext in exts}


def _iter_files(roots: Iterable[Path]):
    for root in roots:
        root.mkdir(parents=True, exist_ok=True)
        for dirpath, dirnames, filenames in os.walk(root):
            # Skip cache/temp/vendor-ish folders.
            dirnames[:] = [d for d in dirnames if d.lower() not in {".git", "node_modules", "__pycache__", "cache", ".venv"}]
            for name in filenames:
                p = Path(dirpath) / name
                if p.suffix.lower() in ALL_EXTENSIONS:
                    yield p


def _upsert_file(conn, p: Path, now: str) -> bool:
    try:
        st = p.stat()
    except OSError:
        return False
    full_path = str(p.resolve())
    conn.execute(
        """
        INSERT INTO files (filename, full_path, extension, size_bytes, modified_at, indexed_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(full_path) DO UPDATE SET
            filename=excluded.filename,
            extension=excluded.extension,
            size_bytes=excluded.size_bytes,
            modified_at=excluded.modified_at,
            indexed_at=excluded.indexed_at
        """,
        (p.name, full_path, p.suffix.lower(), st.st_size, st.st_mtime, now),
    )
    return True


def reindex_files() -> Dict[str, int]:
    indexed = 0
    seen_paths: set[str] = set()
    now = utc_now()
    with get_conn() as conn:
        for p in _iter_files(FILE_ROOTS):
            if _upsert_file(conn, p, now):
                seen_paths.add(str(p.resolve()))
                indexed += 1
        # remove missing files from configured roots only
        existing = conn.execute("SELECT id, full_path FROM files").fetchall()
        resolved_roots = [str(r.resolve()) for r in FILE_ROOTS if r.exists()]
        for row in existing:
            full_path = row["full_path"]
            if full_path not in seen_paths and any(full_path.startswith(root) for root in resolved_roots):
                conn.execute("DELETE FROM files WHERE id = ?", (row["id"],))
    return {"indexed": indexed, "roots": len(FILE_ROOTS)}


def index_folder(folder_path: str | Path) -> Dict[str, int]:
    """Index a user-selected working folder before searching it."""
    root = Path(folder_path).expanduser()
    if not root.is_absolute():
        root = root.resolve()
    if not root.exists() or not root.is_dir():
        raise FileNotFoundError(f"Folder not found: {root}")

    indexed = 0
    now = utc_now()
    with get_conn() as conn:
        for p in _iter_files([root]):
            if _upsert_file(conn, p, now):
                indexed += 1
    return {"indexed": indexed, "root": str(root.resolve())}


def search_index(file_format: str, codes: List[str], limit_per_code: int = 10, root_path: Optional[str] = None) -> List[dict]:
    from .config import SUPPORTED_FORMATS
    exts = SUPPORTED_FORMATS[file_format]
    results: List[dict] = []
    root_prefix = None
    if root_path:
        root = Path(root_path).expanduser()
        if not root.is_absolute():
            root = root.resolve()
        root_prefix = str(root.resolve()).rstrip("\\/")

    with get_conn() as conn:
        for raw in codes:
            code = raw.strip()
            if not code:
                continue
            like = f"%{code}%"
            placeholders = ",".join("?" for _ in exts)
            params = [*exts, like]
            root_clause = ""
            if root_prefix:
                root_clause = " AND (full_path = ? OR full_path LIKE ?)"
                params.extend([root_prefix, root_prefix + os.sep + "%"])
            params.append(limit_per_code)
            rows = conn.execute(
                f"""
                SELECT * FROM files
                WHERE extension IN ({placeholders}) AND filename LIKE ? {root_clause}
                ORDER BY modified_at DESC
                LIMIT ?
                """,
                tuple(params),
            ).fetchall()
            results.append({
                "code": code,
                "matches": [dict(r) for r in rows],
            })
    return results
