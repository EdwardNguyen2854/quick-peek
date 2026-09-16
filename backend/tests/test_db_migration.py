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


if __name__ == "__main__":
    unittest.main()
