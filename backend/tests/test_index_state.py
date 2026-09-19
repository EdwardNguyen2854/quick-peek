from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app.db as db
from app.file_index import _index_roots, index_folder, index_status


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


class MultiRootIndexStateTests(unittest.TestCase):
    def setUp(self):
        self.original_path = db.DB_PATH

    def tearDown(self):
        db.DB_PATH = self.original_path

    def test_multi_root_success_includes_per_root_rows(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            test_path = root / "quickpeek.sqlite3"
            db.DB_PATH = str(test_path)

            root_a = root / "root_a"
            root_b = root / "root_b"
            root_a.mkdir()
            root_b.mkdir()

            (root_a / "FILEA.stp").write_text("content a", encoding="utf-8")
            (root_b / "FILEB.pdf").write_text("content b", encoding="utf-8")

            db.init_db()

            _index_roots([root_a, root_b], prune=False)

            state = index_status()
            self.assertEqual(state["status"], "ready")
            self.assertEqual(len(state["roots"]), 2)

            root_paths = {r["root_path"] for r in state["roots"]}
            self.assertIn(str(root_a.resolve()), root_paths)
            self.assertIn(str(root_b.resolve()), root_paths)

            for r in state["roots"]:
                self.assertEqual(r["status"], "ready")
                self.assertIsNotNone(r["last_completed_at"])

    def test_single_root_failure_does_not_fail_overall_refresh(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            test_path = root / "quickpeek.sqlite3"
            db.DB_PATH = str(test_path)

            root_a = root / "root_a"
            root_b = root / "nonexistent_root"
            root_a.mkdir()

            (root_a / "FILEA.stp").write_text("content a", encoding="utf-8")

            db.init_db()

            _index_roots([root_a, root_b], prune=False)

            state = index_status()
            self.assertEqual(state["status"], "ready")

            root_states = {r["root_path"]: r for r in state["roots"]}
            self.assertEqual(root_states[str(root_a.resolve())]["status"], "ready")
            self.assertEqual(root_states[str(root_b.resolve())]["status"], "error")
            self.assertIn("offline", root_states[str(root_b.resolve())]["last_error"].lower())

    def test_offline_root_recorded_as_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            test_path = root / "quickpeek.sqlite3"
            db.DB_PATH = str(test_path)

            offline_root = root / "nonexistent_root"

            db.init_db()

            _index_roots([offline_root], prune=False)

            state = index_status()
            self.assertEqual(state["status"], "ready")
            self.assertEqual(len(state["roots"]), 1)
            self.assertEqual(state["roots"][0]["status"], "error")
            self.assertIn("offline", state["roots"][0]["last_error"].lower())


if __name__ == "__main__":
    unittest.main()
