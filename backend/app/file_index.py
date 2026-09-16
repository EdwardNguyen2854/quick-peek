from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from .config import FILE_ROOTS, SUPPORTED_FORMATS
from .db import get_conn, get_index_state, set_index_state, utc_now
from .search_engine import (
    explain_candidate,
    fuzzy_suggestions,
    match_candidate,
    normalize_code,
    parse_filename,
    ranking_key,
)

ALL_EXTENSIONS = {ext for exts in SUPPORTED_FORMATS.values() for ext in exts}
FORMAT_BY_EXTENSION = {
    extension: file_format
    for file_format, extensions in SUPPORTED_FORMATS.items()
    for extension in extensions
}

EXCLUDED_DIRS = {
    ".git",
    ".svn",
    ".hg",
    "node_modules",
    "__pycache__",
    "cache",
    ".venv",
    ".idea",
    ".vscode",
    "$recycle.bin",
    "system volume information",
}
EXCLUDED_SUFFIXES = {".tmp", ".bak", ".swp", ".swo", ".part", ".crdownload"}


def _is_temp_file(name: str) -> bool:
    lower = name.lower()
    if lower.startswith("~$") or lower.startswith(".~"):
        return True
    return any(lower.endswith(suffix) for suffix in EXCLUDED_SUFFIXES)


def _iter_files(roots: Iterable[Path]):
    for root in roots:
        if not root.exists() or not root.is_dir():
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [
                directory
                for directory in dirnames
                if directory.lower() not in EXCLUDED_DIRS and not directory.startswith(".")
            ]
            for name in filenames:
                if _is_temp_file(name):
                    continue
                path = Path(dirpath) / name
                if path.suffix.lower() in ALL_EXTENSIONS:
                    yield path, root


def _upsert_file(conn, path: Path, root: Path, now: str) -> bool:
    try:
        stat = path.stat()
    except OSError:
        return False

    full_path = str(path.resolve())
    existing = conn.execute(
        "SELECT size_bytes, modified_at, file_format FROM files WHERE full_path = ?",
        (full_path,),
    ).fetchone()

    if (
        existing
        and int(existing["size_bytes"]) == int(stat.st_size)
        and float(existing["modified_at"]) == float(stat.st_mtime)
        and str(existing["file_format"] or "")
    ):
        conn.execute(
            "UPDATE files SET indexed_at = ?, root_path = ? WHERE full_path = ?",
            (now, str(root.resolve()), full_path),
        )
        return True

    parsed = parse_filename(path.name, full_path)
    file_format = FORMAT_BY_EXTENSION.get(path.suffix.lower(), "")

    conn.execute(
        """
        INSERT INTO files (
            filename, full_path, extension, size_bytes, modified_at, indexed_at,
            file_format, normalized_filename, normalized_stem, compact_stem,
            parsed_code, compact_code, revision_raw, revision_rank, tokens,
            folder_class, folder_priority, root_path
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(full_path) DO UPDATE SET
            filename=excluded.filename,
            extension=excluded.extension,
            size_bytes=excluded.size_bytes,
            modified_at=excluded.modified_at,
            indexed_at=excluded.indexed_at,
            file_format=excluded.file_format,
            normalized_filename=excluded.normalized_filename,
            normalized_stem=excluded.normalized_stem,
            compact_stem=excluded.compact_stem,
            parsed_code=excluded.parsed_code,
            compact_code=excluded.compact_code,
            revision_raw=excluded.revision_raw,
            revision_rank=excluded.revision_rank,
            tokens=excluded.tokens,
            folder_class=excluded.folder_class,
            folder_priority=excluded.folder_priority,
            root_path=excluded.root_path
        """,
        (
            path.name,
            full_path,
            path.suffix.lower(),
            stat.st_size,
            stat.st_mtime,
            now,
            file_format,
            parsed.normalized_filename,
            parsed.normalized_stem,
            parsed.compact_stem,
            parsed.parsed_code,
            parsed.compact_code,
            parsed.revision_raw,
            parsed.revision_rank,
            "|" + "|".join(parsed.tokens) + "|" if parsed.tokens else "",
            parsed.folder_class,
            parsed.folder_priority,
            str(root.resolve()),
        ),
    )
    return True


def _index_roots(roots: list[Path], prune: bool = True) -> Dict[str, int]:
    now = utc_now()
    set_index_state(
        status="indexing",
        last_started_at=now,
        roots_count=len(roots),
        last_error="",
    )

    indexed = 0
    seen_paths: set[str] = set()
    resolved_roots = [str(root.resolve()) for root in roots if root.exists()]

    try:
        with get_conn() as conn:
            for path, root in _iter_files(roots):
                if _upsert_file(conn, path, root, now):
                    resolved = str(path.resolve())
                    seen_paths.add(resolved)
                    indexed += 1

            if prune and resolved_roots:
                rows = conn.execute("SELECT id, full_path FROM files").fetchall()
                for row in rows:
                    full_path = row["full_path"]
                    in_scope = any(
                        full_path == root or full_path.startswith(root + os.sep)
                        for root in resolved_roots
                    )
                    if in_scope and full_path not in seen_paths:
                        conn.execute("DELETE FROM files WHERE id = ?", (row["id"],))

            total = conn.execute("SELECT COUNT(*) AS count FROM files").fetchone()["count"]

        completed = utc_now()
        set_index_state(
            status="ready",
            last_completed_at=completed,
            files_count=int(total),
            roots_count=len(roots),
            last_error="",
        )
        return {"indexed": indexed, "files_count": int(total), "roots": len(roots)}
    except Exception as exc:
        set_index_state(status="error", last_error=str(exc))
        raise


def reindex_files() -> Dict[str, int]:
    return _index_roots(FILE_ROOTS, prune=True)


def index_folder(folder_path: str | Path) -> Dict[str, int]:
    root = Path(folder_path).expanduser()
    if not root.is_absolute():
        root = root.resolve()
    if not root.exists() or not root.is_dir():
        raise FileNotFoundError(f"Folder not found: {root}")
    return _index_roots([root], prune=True)


def refresh_index(folder_path: Optional[str] = None) -> Dict[str, int]:
    if folder_path:
        return index_folder(folder_path)
    return reindex_files()


def index_status() -> dict:
    return get_index_state()


def _scope_clause(root_path: Optional[str]) -> tuple[str, list[str]]:
    if not root_path:
        return "", []

    root = Path(root_path).expanduser()
    if not root.is_absolute():
        root = root.resolve()
    prefix = str(root.resolve()).rstrip("\\/")
    return " AND (full_path = ? OR full_path LIKE ?)", [prefix, prefix + os.sep + "%"]


def _format_clause(file_format: str) -> tuple[str, list[str]]:
    if file_format == "all":
        return "", []
    return " AND file_format = ?", [file_format]


def _fetch_candidates(
    conn,
    *,
    file_format: str,
    query,
    root_path: Optional[str],
    fuzzy: bool = False,
    limit: int = 200,
) -> list[dict]:
    format_clause, format_params = _format_clause(file_format)
    scope_clause, scope_params = _scope_clause(root_path)

    if fuzzy:
        prefix = query.compact[: max(3, min(6, len(query.compact)))]
        if not prefix:
            return []
        candidate_clause = " AND (compact_code LIKE ? OR compact_stem LIKE ?)"
        candidate_params = [prefix + "%", prefix + "%"]
    else:
        candidate_clause = """
            AND (
                compact_code = ?
                OR compact_stem = ?
                OR normalized_stem = ?
                OR compact_stem LIKE ?
                OR tokens LIKE ?
            )
        """
        candidate_params = [
            query.compact,
            query.compact,
            query.normalized,
            "%" + query.compact + "%",
            "%|" + query.compact + "|%",
        ]

    rows = conn.execute(
        f"""
        SELECT * FROM files
        WHERE 1 = 1
        {format_clause}
        {scope_clause}
        {candidate_clause}
        LIMIT ?
        """,
        tuple([*format_params, *scope_params, *candidate_params, limit]),
    ).fetchall()

    return [dict(row) for row in rows]


def search_index(
    file_format: str,
    codes: List[str],
    limit_per_code: int = 10,
    root_path: Optional[str] = None,
) -> List[dict]:
    results: List[dict] = []

    with get_conn() as conn:
        for raw in codes:
            query = normalize_code(raw)
            if not query.cleaned:
                continue

            candidates = _fetch_candidates(
                conn,
                file_format=file_format,
                query=query,
                root_path=root_path,
                fuzzy=False,
                limit=max(100, limit_per_code * 10),
            )

            strong: list[dict] = []
            for row in candidates:
                match_type, _, _ = match_candidate(query, row)
                if match_type:
                    enriched = dict(row)
                    enriched.update(explain_candidate(query, row))
                    strong.append(enriched)

            strong.sort(key=lambda row: ranking_key(query, row), reverse=True)

            suggestions: list[dict] = []
            if not strong:
                fuzzy_pool = _fetch_candidates(
                    conn,
                    file_format=file_format,
                    query=query,
                    root_path=root_path,
                    fuzzy=True,
                    limit=250,
                )
                suggestions = fuzzy_suggestions(query, fuzzy_pool, limit=3)

            results.append(
                {
                    "code": query.cleaned,
                    "normalized_code": query.normalized,
                    "matches": strong[:limit_per_code],
                    "matches_count": len(strong),
                    "suggestions": suggestions,
                }
            )

    return results
