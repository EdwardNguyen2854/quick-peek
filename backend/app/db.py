from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional

from .config import DB_PATH


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def row_to_dict(row: sqlite3.Row | None) -> Optional[Dict[str, Any]]:
    if row is None:
        return None
    return {k: row[k] for k in row.keys()}


def rows_to_dicts(rows: Iterable[sqlite3.Row]) -> List[Dict[str, Any]]:
    return [row_to_dict(r) or {} for r in rows]


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(
            """
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                permissions_json TEXT NOT NULL DEFAULT '[]',
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_login_at TEXT
            );

            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                full_path TEXT NOT NULL UNIQUE,
                extension TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                modified_at REAL NOT NULL,
                indexed_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_files_extension ON files(extension);
            CREATE INDEX IF NOT EXISTS idx_files_filename ON files(filename);

            CREATE TABLE IF NOT EXISTS usage_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT NOT NULL,
                format TEXT,
                codes_count INTEGER DEFAULT 0,
                files_found INTEGER DEFAULT 0,
                seconds_saved REAL DEFAULT 0,
                details_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );
            CREATE INDEX IF NOT EXISTS idx_usage_created ON usage_logs(created_at);
            CREATE INDEX IF NOT EXISTS idx_usage_user ON usage_logs(user_id);

            CREATE TABLE IF NOT EXISTS folder_presets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                path TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(user_id, name),
                FOREIGN KEY(user_id) REFERENCES users(id)
            );
            CREATE INDEX IF NOT EXISTS idx_folder_presets_user ON folder_presets(user_id);
            """
        )

        # ── v0.4 / Phase 1: Add new columns to users table (idempotent) ──
        for col_sql in [
            "ALTER TABLE users ADD COLUMN auth_source TEXT NOT NULL DEFAULT 'local'",
            "ALTER TABLE users ADD COLUMN ldap_dn TEXT",
            "ALTER TABLE users ADD COLUMN email TEXT",
            "ALTER TABLE users ADD COLUMN display_name TEXT",
            "ALTER TABLE users ADD COLUMN last_synced_at TEXT",
        ]:
            try:
                conn.execute(col_sql)
            except sqlite3.OperationalError:
                pass  # Column already exists

        # ── v0.4 / Phase 1: New tables ──
        conn.executescript(
            """
            -- API Keys
            CREATE TABLE IF NOT EXISTS api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                prefix TEXT NOT NULL,
                key_hash TEXT NOT NULL,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                scopes_json TEXT NOT NULL DEFAULT '[]',
                expires_at TEXT,
                last_used_at TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                revoked_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_api_keys_prefix ON api_keys(prefix);
            CREATE INDEX IF NOT EXISTS idx_api_keys_user ON api_keys(user_id);

            -- Folder Scopes
            CREATE TABLE IF NOT EXISTS folder_scopes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern TEXT NOT NULL,
                description TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_scopes_pattern ON folder_scopes(pattern);

            -- Folder Grants
            CREATE TABLE IF NOT EXISTS folder_grants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scope_id INTEGER NOT NULL REFERENCES folder_scopes(id) ON DELETE CASCADE,
                principal_type TEXT NOT NULL CHECK (principal_type IN ('user','group','api_key')),
                principal_id TEXT NOT NULL,
                permission TEXT NOT NULL CHECK (permission IN ('view','download','index')),
                effect TEXT NOT NULL DEFAULT 'allow' CHECK (effect IN ('allow','deny')),
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_grants_principal ON folder_grants(principal_type, principal_id);
            CREATE INDEX IF NOT EXISTS idx_grants_scope ON folder_grants(scope_id);

            -- Tags
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                scope TEXT NOT NULL DEFAULT 'shared',
                color TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE(name, scope)
            );
            CREATE INDEX IF NOT EXISTS idx_tags_scope ON tags(scope);

            -- File Tags (M2M)
            CREATE TABLE IF NOT EXISTS file_tags (
                file_id INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
                tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
                applied_by INTEGER NOT NULL REFERENCES users(id),
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                PRIMARY KEY(file_id, tag_id)
            );
            CREATE INDEX IF NOT EXISTS idx_file_tags_tag ON file_tags(tag_id);

            -- File Metadata
            CREATE TABLE IF NOT EXISTS file_metadata (
                file_id INTEGER PRIMARY KEY REFERENCES files(id) ON DELETE CASCADE,
                project_code TEXT,
                revision TEXT,
                supplier TEXT,
                cost_center TEXT,
                custom_json TEXT NOT NULL DEFAULT '{}',
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_by INTEGER REFERENCES users(id)
            );
            CREATE INDEX IF NOT EXISTS idx_filemeta_project ON file_metadata(project_code);
            CREATE INDEX IF NOT EXISTS idx_filemeta_revision ON file_metadata(revision);

            -- Recent Files (per-user MRU)
            CREATE TABLE IF NOT EXISTS recent_files (
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                file_id INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
                last_opened_at TEXT NOT NULL DEFAULT (datetime('now')),
                open_count INTEGER NOT NULL DEFAULT 1,
                PRIMARY KEY(user_id, file_id)
            );
            CREATE INDEX IF NOT EXISTS idx_recent_user ON recent_files(user_id, last_opened_at DESC);

            -- Tag Audit Log
            CREATE TABLE IF NOT EXISTS tag_audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id INTEGER NOT NULL,
                tag_id INTEGER NOT NULL,
                action TEXT NOT NULL CHECK (action IN ('add','remove')),
                user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_tag_audit_file ON tag_audit_log(file_id);
            CREATE INDEX IF NOT EXISTS idx_tag_audit_user ON tag_audit_log(user_id);

            -- Folder Schemas (required fields per path)
            CREATE TABLE IF NOT EXISTS folder_schemas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path_prefix TEXT NOT NULL,
                required_fields_json TEXT NOT NULL DEFAULT '[]',
                created_by INTEGER REFERENCES users(id),
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            """
        )

        # ── v0.4: FTS5 full-text search (best-effort) ──
        try:
            conn.executescript(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS fts5_files USING fts5(
                    filename,
                    full_path,
                    content='files',
                    content_rowid='id',
                    tokenize='porter unicode61'
                );
                """
            )
        except sqlite3.OperationalError:
            pass  # FTS5 not available in this SQLite build


def rebuild_fts5() -> None:
    """Rebuild the FTS5 full-text index from the files table."""
    try:
        with get_conn() as conn:
            conn.executescript(
                """
                INSERT OR REPLACE INTO fts5_files(rowid, filename, full_path)
                SELECT id, filename, full_path FROM files;
                """
            )
    except sqlite3.OperationalError:
        pass  # FTS5 not available


def cleanup_history(days: int = 90) -> None:
    """Purge usage_logs and recent_files older than `days`."""
    with get_conn() as conn:
        conn.execute(
            "DELETE FROM usage_logs WHERE created_at < datetime('now', ?)",
            (f"-{days} days",),
        )
        conn.execute(
            "DELETE FROM recent_files WHERE last_opened_at < datetime('now', ?)",
            (f"-{days} days",),
        )


def json_loads(value: str | None, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except Exception:
        return default


def json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)
