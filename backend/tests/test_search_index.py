from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import app.db as db
from app.file_index import index_folder, search_index


class SearchIndexIntegrationTests(unittest.TestCase):
    def test_index_search_ranking_and_fuzzy_suggestions(self):
        original_path = db.DB_PATH
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            db.DB_PATH = root / "quickpeek.sqlite3"
            try:
                released = root / "released"
                archive = root / "archive"
                released.mkdir()
                archive.mkdir()

                (released / "ABC123_REV_B.stp").write_text("released", encoding="utf-8")
                (archive / "ABC123_REV_C.stp").write_text("archive", encoding="utf-8")
                (released / "R502A1B10M11BF1.stp").write_text("suggestion", encoding="utf-8")

                db.init_db()
                index_folder(root)

                exact = search_index("step", ["ABC123"])
                self.assertEqual(exact[0]["matches_count"], 2)
                self.assertEqual(exact[0]["matches"][0]["filename"], "ABC123_REV_B.stp")
                self.assertEqual(exact[0]["matches"][0]["folder_class"], "released")

                fuzzy = search_index("step", ["R502A1B10M11BFL"])
                self.assertEqual(fuzzy[0]["matches_count"], 0)
                self.assertEqual(fuzzy[0]["suggestions"][0]["filename"], "R502A1B10M11BF1.stp")
            finally:
                db.DB_PATH = original_path


if __name__ == "__main__":
    unittest.main()
