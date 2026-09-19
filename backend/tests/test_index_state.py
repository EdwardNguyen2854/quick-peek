from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import app.db as db
from app.file_index import index_folder, index_status


class IndexStateTransitionTests(unittest.TestCase):
    def setUp(self):
        self.original_path = db.DB_PATH

    def tearDown(self):
        db.DB_PATH = self.original_path

    def test_index_status_reflects_idle_state(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            test_path = root / "quickpeek.sqlite3"
            db.DB_PATH = str(test_path)

            db.init_db()

            state = index_status()
            self.assertEqual(state["status"], "idle")
            self.assertEqual(state["phase"], "idle")

    def test_index_folder_updates_state_to_ready(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            test_path = root / "quickpeek.sqlite3"
            db.DB_PATH = str(test_path)

            files_dir = root / "files"
            files_dir.mkdir()

            (files_dir / "TEST123.stp").write_text("content", encoding="utf-8")

            db.init_db()

            result = index_folder(files_dir)

            self.assertEqual(result["indexed"], 1)
            state = index_status()
            self.assertEqual(state["status"], "ready")
            self.assertEqual(state["phase"], "ready")
            self.assertEqual(state["files_count"], 1)

    def test_search_works_after_indexing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            test_path = root / "quickpeek.sqlite3"
            db.DB_PATH = str(test_path)

            files_dir = root / "files"
            files_dir.mkdir()

            (files_dir / "TEST123.stp").write_text("content", encoding="utf-8")

            db.init_db()

            index_folder(files_dir)

            from app.file_index import search_index

            results = search_index("step", ["TEST123"])
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["matches_count"], 1)

    def test_index_status_includes_progress_fields(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            test_path = root / "quickpeek.sqlite3"
            db.DB_PATH = str(test_path)

            db.init_db()

            state = index_status()
            self.assertIn("phase", state)
            self.assertIn("current_root", state)
            self.assertIn("files_indexed", state)
            self.assertIn("elapsed_seconds", state)


if __name__ == "__main__":
    unittest.main()
