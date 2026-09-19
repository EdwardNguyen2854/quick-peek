from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, Iterator, Optional

from .config import DB_PATH


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(str(DB_PATH), timeout=30)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def row_to_dict(row: sqlite3.Row | None) -> Optional[Dict[str, Any]]:
    if row is None:
        return None
    return {key: row[key] for key in row.keys()}


def _ensure_columns(conn: sqlite3.Connection, table: str, columns: dict[str, str]) -> None:
    existing = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    for name, definition in columns.items():
        if name not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(
            """
            PRAGMA journal_mode=WAL;
            PRAGMA synchronous=NORMAL;

            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                full_path TEXT NOT NULL UNIQUE,
                extension TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                modified_at REAL NOT NULL,
                indexed_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS index_state (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                status TEXT NOT NULL DEFAULT 'idle',
                phase TEXT NOT NULL DEFAULT 'idle',
                last_started_at TEXT,
                last_completed_at TEXT,
                files_count INTEGER NOT NULL DEFAULT 0,
                roots_count INTEGER NOT NULL DEFAULT 0,
                current_root TEXT NOT NULL DEFAULT '',
                files_indexed INTEGER NOT NULL DEFAULT 0,
                last_error TEXT
            );

            CREATE TABLE IF NOT EXISTS index_root_state (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                root_path TEXT NOT NULL UNIQUE,
                status TEXT NOT NULL DEFAULT 'idle',
                last_started_at TEXT,
                last_completed_at TEXT,
                files_count INTEGER NOT NULL DEFAULT 0,
                last_error TEXT
            );
            """
        )

        _ensure_columns(
            conn,
            "index_state",
            {
                "phase": "TEXT NOT NULL DEFAULT 'idle'",
                "current_root": "TEXT NOT NULL DEFAULT ''",
                "files_indexed": "INTEGER NOT NULL DEFAULT 0",
            },
        )

        conn.execute(
            "INSERT OR IGNORE INTO index_state (id, status, phase, files_count, roots_count) VALUES (1, 'idle', 'idle', 0, 0)"
        )

        _ensure_columns(
            conn,
            "files",
            {
                "file_format": "TEXT NOT NULL DEFAULT ''",
                "normalized_filename": "TEXT NOT NULL DEFAULT ''",
                "normalized_stem": "TEXT NOT NULL DEFAULT ''",
                "compact_stem": "TEXT NOT NULL DEFAULT ''",
                "parsed_code": "TEXT NOT NULL DEFAULT ''",
                "compact_code": "TEXT NOT NULL DEFAULT ''",
                "revision_raw": "TEXT",
                "revision_rank": "INTEGER NOT NULL DEFAULT 0",
                "tokens": "TEXT NOT NULL DEFAULT ''",
                "folder_class": "TEXT NOT NULL DEFAULT 'normal'",
                "folder_priority": "INTEGER NOT NULL DEFAULT 250",
                "root_path": "TEXT NOT NULL DEFAULT ''",
            },
        )

        conn.executescript(
            """
            CREATE INDEX IF NOT EXISTS idx_files_extension ON files(extension);
            CREATE INDEX IF NOT EXISTS idx_files_filename ON files(filename);
            CREATE INDEX IF NOT EXISTS idx_files_file_format ON files(file_format);
            CREATE INDEX IF NOT EXISTS idx_files_compact_stem ON files(compact_stem);
            CREATE INDEX IF NOT EXISTS idx_files_compact_code ON files(compact_code);
            CREATE INDEX IF NOT EXISTS idx_files_normalized_stem ON files(normalized_stem);
            CREATE INDEX IF NOT EXISTS idx_files_folder_priority ON files(folder_priority);
            CREATE INDEX IF NOT EXISTS idx_files_modified_at ON files(modified_at);
            """
        )


def set_index_state(
    *,
    status: Optional[str] = None,
    phase: Optional[str] = None,
    last_started_at: Optional[str] = None,
    last_completed_at: Optional[str] = None,
    files_count: Optional[int] = None,
    roots_count: Optional[int] = None,
    current_root: Optional[str] = None,
    files_indexed: Optional[int] = None,
    last_error: Optional[str] = None,
) -> None:
    fields: list[str] = []
    values: list[Any] = []

    for key, value in (
        ("status", status),
        ("phase", phase),
        ("last_started_at", last_started_at),
        ("last_completed_at", last_completed_at),
        ("files_count", files_count),
        ("roots_count", roots_count),
        ("current_root", current_root),
        ("files_indexed", files_indexed),
        ("last_error", last_error),
    ):
        if value is not None:
            fields.append(f"{key} = ?")
            values.append(value)

    if not fields:
        return

    values.append(1)
    with get_conn() as conn:
        conn.execute(f"UPDATE index_state SET {', '.join(fields)} WHERE id = ?", tuple(values))


def get_index_state() -> dict[str, Any]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM index_state WHERE id = 1").fetchone()
        count = conn.execute("SELECT COUNT(*) AS count FROM files").fetchone()["count"]
        root_rows = conn.execute("SELECT * FROM index_root_state").fetchall()

    item = row_to_dict(row) or {
        "status": "idle",
        "phase": "idle",
        "last_started_at": None,
        "last_completed_at": None,
        "files_count": 0,
        "roots_count": 0,
        "current_root": "",
        "files_indexed": 0,
        "last_error": None,
    }
    item["files_count"] = int(count)
    item["roots"] = [row_to_dict(r) for r in root_rows]
    return item


def set_root_state(
    *,
    root_path: str,
    status: Optional[str] = None,
    last_started_at: Optional[str] = None,
    last_completed_at: Optional[str] = None,
    files_count: Optional[int] = None,
    last_error: Optional[str] = None,
) -> None:
    fields: list[str] = []
    values: list[Any] = []

    for key, value in (
        ("status", status),
        ("last_started_at", last_started_at),
        ("last_completed_at", last_completed_at),
        ("files_count", files_count),
        ("last_error", last_error),
    ):
        if value is not None:
            fields.append(f"{key} = ?")
            values.append(value)

    if not fields:
        return

    values.append(root_path)
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT id FROM index_root_state WHERE root_path = ?", (root_path,)
        ).fetchone()
        if existing:
            conn.execute(
                f"UPDATE index_root_state SET {', '.join(fields)} WHERE root_path = ?",
                tuple(values),
            )
        else:
            conn.execute(
                f"INSERT INTO index_root_state (root_path, {', '.join(f.split('=')[0].strip() for f in fields)}) VALUES (?, {', '.join(['?'] * len(fields))})",
                (root_path, *values[:-1]),
            )


def get_root_states() -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM index_root_state").fetchall()
    return [row_to_dict(r) for r in rows]


def delete_root_state(root_path: str) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM index_root_state WHERE root_path = ?", (root_path,))
