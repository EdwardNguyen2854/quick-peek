from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

import app.db as db


class DatabaseMigrationTests(unittest.TestCase):
    def test_old_files_table_is_enriched_in_place(self):
        original_path = db.DB_PATH
        with tempfile.TemporaryDirectory() as temp_dir:
            test_path = Path(temp_dir) / "quickpeek.sqlite3"
            db.DB_PATH = test_path
            try:
                conn = sqlite3.connect(test_path)
                conn.executescript(
                    """
                    CREATE TABLE files (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        filename TEXT NOT NULL,
                        full_path TEXT NOT NULL UNIQUE,
                        extension TEXT NOT NULL,
                        size_bytes INTEGER NOT NULL,
                        modified_at REAL NOT NULL,
                        indexed_at TEXT NOT NULL
                    );
                    INSERT INTO files (
                        filename, full_path, extension, size_bytes, modified_at, indexed_at
                    ) VALUES (
                        'ABC123.stp', '/tmp/ABC123.stp', '.stp', 100, 1.0, 'old'
                    );
                    """
                )
                conn.commit()
                conn.close()

                db.init_db()

                conn = sqlite3.connect(test_path)
                columns = {row[1] for row in conn.execute("PRAGMA table_info(files)").fetchall()}
                row = conn.execute("SELECT filename FROM files WHERE id = 1").fetchone()
                state = conn.execute("SELECT status FROM index_state WHERE id = 1").fetchone()
                conn.close()

                self.assertIn("compact_code", columns)
                self.assertIn("revision_rank", columns)
                self.assertIn("folder_priority", columns)
                self.assertEqual(row[0], "ABC123.stp")
                self.assertEqual(state[0], "idle")
            finally:
                db.DB_PATH = original_path

    def test_v0p8_index_state_migrates_in_place(self):
        original_path = db.DB_PATH
        with tempfile.TemporaryDirectory() as temp_dir:
            test_path = Path(temp_dir) / "quickpeek.sqlite3"
            db.DB_PATH = test_path
            try:
                conn = sqlite3.connect(test_path)
                conn.executescript(
                    """
                    CREATE TABLE files (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        filename TEXT NOT NULL,
                        full_path TEXT NOT NULL UNIQUE,
                        extension TEXT NOT NULL,
                        size_bytes INTEGER NOT NULL,
                        modified_at REAL NOT NULL,
                        indexed_at TEXT NOT NULL
                    );
                    INSERT INTO files (
                        filename, full_path, extension, size_bytes, modified_at, indexed_at
                    ) VALUES (
                        'ABC123.stp', '/tmp/ABC123.stp', '.stp', 100, 1.0, 'old'
                    );
                    CREATE TABLE index_state (
                        id INTEGER PRIMARY KEY CHECK (id = 1),
                        status TEXT NOT NULL DEFAULT 'idle',
                        last_started_at TEXT,
                        last_completed_at TEXT,
                        files_count INTEGER NOT NULL DEFAULT 0,
                        roots_count INTEGER NOT NULL DEFAULT 0,
                        last_error TEXT
                    );
                    INSERT INTO index_state (id, status, files_count, roots_count)
                    VALUES (1, 'indexing', 42, 3);
                    """
                )
                conn.commit()
                conn.close()

                db.init_db()

                conn = sqlite3.connect(test_path)
                columns = {row[1] for row in conn.execute("PRAGMA table_info(index_state)").fetchall()}
                state = conn.execute("SELECT status, phase, files_count, roots_count FROM index_state WHERE id = 1").fetchone()
                files_row = conn.execute("SELECT filename FROM files WHERE id = 1").fetchone()
                conn.close()

                self.assertIn("phase", columns)
                self.assertIn("current_root", columns)
                self.assertIn("files_indexed", columns)
                self.assertEqual(state[0], "indexing")
                self.assertEqual(state[1], "idle")
                self.assertEqual(state[2], 42)
                self.assertEqual(state[3], 3)
                self.assertEqual(files_row[0], "ABC123.stp")
            finally:
                db.DB_PATH = original_path

    def test_old_database_gets_index_root_state_table(self):
        original_path = db.DB_PATH
        with tempfile.TemporaryDirectory() as temp_dir:
            test_path = Path(temp_dir) / "quickpeek.sqlite3"
            db.DB_PATH = test_path
            try:
                conn = sqlite3.connect(test_path)
                conn.executescript(
                    """
                    CREATE TABLE files (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        filename TEXT NOT NULL,
                        full_path TEXT NOT NULL UNIQUE,
                        extension TEXT NOT NULL,
                        size_bytes INTEGER NOT NULL,
                        modified_at REAL NOT NULL,
                        indexed_at TEXT NOT NULL
                    );
                    CREATE TABLE index_state (
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
                    INSERT INTO index_state (id, status, phase, files_count, roots_count)
                    VALUES (1, 'idle', 'idle', 0, 0);
                    """
                )
                conn.commit()
                conn.close()

                db.init_db()

                conn = sqlite3.connect(test_path)
                tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
                root_state_columns = {row[1] for row in conn.execute("PRAGMA table_info(index_root_state)").fetchall()}
                conn.close()

                self.assertIn("index_root_state", tables)
                self.assertIn("root_path", root_state_columns)
                self.assertIn("status", root_state_columns)
                self.assertIn("last_error", root_state_columns)
            finally:
                db.DB_PATH = original_path


if __name__ == "__main__":
    unittest.main()
