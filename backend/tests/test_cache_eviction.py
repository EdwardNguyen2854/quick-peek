from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path

from app import cache_eviction
from app.config import PREVIEW_CACHE_MAX_AGE_DAYS, PREVIEW_CACHE_MAX_SIZE_MB


class CacheEvictionTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.preview_dir = Path(self.temp_dir.name) / "previews"
        self.preview_dir.mkdir()
        self.original_preview_dir = cache_eviction.PREVIEW_DIR
        self.original_max_size = cache_eviction.MAX_SIZE_BYTES
        self.original_max_age = cache_eviction.MAX_AGE_SECONDS
        cache_eviction.PREVIEW_DIR = self.preview_dir
        cache_eviction.MAX_SIZE_BYTES = 100 * 1024
        cache_eviction.MAX_AGE_SECONDS = 7 * 86400
        cache_eviction._last_eviction_time = 0.0
        cache_eviction._recently_accessed.clear()

    def tearDown(self):
        self.temp_dir.cleanup()
        cache_eviction.PREVIEW_DIR = self.original_preview_dir
        cache_eviction.MAX_SIZE_BYTES = self.original_max_size
        cache_eviction.MAX_AGE_SECONDS = self.original_max_age

    def _create_cache_file(self, name: str, content: str, age_seconds: int = 0) -> Path:
        path = self.preview_dir / name
        path.write_text(content, encoding="utf-8")
        if age_seconds > 0:
            old_time = time.time() - age_seconds
            Path(path).touch()
            import os
            os.utime(path, (old_time, old_time))
        return path

    def test_age_eviction_removes_old_files(self):
        self._create_cache_file("abc123.svg", "x" * 50, age_seconds=8 * 86400)
        self._create_cache_file("def456.html", "y" * 50, age_seconds=8 * 86400)
        count, _ = cache_eviction.evict_preview_cache()
        self.assertEqual(count, 2)
        self.assertFalse((self.preview_dir / "abc123.svg").exists())
        self.assertFalse((self.preview_dir / "def456.html").exists())

    def test_size_eviction_removes_oldest_files_first(self):
        cache_eviction.MAX_SIZE_BYTES = 80
        self._create_cache_file("oldest.svg", "x" * 30, age_seconds=0)
        self._create_cache_file("newer.svg", "y" * 30, age_seconds=0)
        self._create_cache_file("newest.svg", "z" * 30, age_seconds=0)
        cache_eviction._recently_accessed.add("oldest.svg")
        count, _ = cache_eviction.evict_preview_cache()
        self.assertGreaterEqual(count, 1)
        self.assertTrue((self.preview_dir / "newest.svg").exists())

    def test_recently_accessed_file_not_evicted_for_age(self):
        self._create_cache_file("recent.svg", "x" * 50, age_seconds=8 * 86400)
        cache_eviction.mark_preview_accessed(str(self.preview_dir / "recent.svg"))
        cache_eviction.evict_preview_cache()
        self.assertTrue((self.preview_dir / "recent.svg").exists())

    def test_non_cache_files_ignored(self):
        random_file = self.preview_dir / "not_cache.txt"
        random_file.write_text("random", encoding="utf-8")
        count, _ = cache_eviction.evict_preview_cache()
        self.assertEqual(count, 0)
        self.assertTrue(random_file.exists())

    def test_empty_cache_dir_returns_zero(self):
        count, _ = cache_eviction.evict_preview_cache()
        self.assertEqual(count, 0)

    def test_cooldown_prevents_rapid_eviction(self):
        cache_eviction._last_eviction_time = time.time()
        count, _ = cache_eviction.evict_preview_cache()
        self.assertEqual(count, 0)


class CacheEvictionAccessTrackingTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.preview_dir = Path(self.temp_dir.name) / "previews"
        self.preview_dir.mkdir()
        self.original_preview_dir = cache_eviction.PREVIEW_DIR
        cache_eviction.PREVIEW_DIR = self.preview_dir
        cache_eviction._recently_accessed.clear()

    def tearDown(self):
        self.temp_dir.cleanup()
        cache_eviction.PREVIEW_DIR = self.original_preview_dir
        cache_eviction._recently_accessed.clear()

    def test_mark_preview_accessed_tracks_file(self):
        cache_eviction.mark_preview_accessed(str(self.preview_dir / "test.svg"))
        self.assertIn("test.svg", cache_eviction._recently_accessed)

    def test_clear_accessed_cache_resets_tracking(self):
        cache_eviction.mark_preview_accessed(str(self.preview_dir / "test.svg"))
        cache_eviction.clear_accessed_cache()
        self.assertEqual(len(cache_eviction._recently_accessed), 0)


if __name__ == "__main__":
    unittest.main()
