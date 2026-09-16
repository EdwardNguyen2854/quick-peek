from __future__ import annotations

import unittest

from app.search_engine import (
    classify_folder,
    fuzzy_suggestions,
    match_candidate,
    normalize_code,
    parse_filename,
    ranking_key,
)


def candidate(
    *,
    filename: str,
    compact_stem: str,
    compact_code: str,
    parsed_code: str,
    normalized_stem: str | None = None,
    folder_priority: int = 250,
    revision_rank: int = 0,
    modified_at: float = 0,
    tokens: str = "",
    full_path: str | None = None,
    file_id: int = 1,
):
    return {
        "id": file_id,
        "filename": filename,
        "extension": ".stp",
        "compact_stem": compact_stem,
        "compact_code": compact_code,
        "parsed_code": parsed_code,
        "normalized_stem": normalized_stem or parsed_code,
        "folder_priority": folder_priority,
        "revision_rank": revision_rank,
        "modified_at": modified_at,
        "tokens": tokens,
        "full_path": full_path or f"/files/{filename}",
        "folder_class": "normal",
        "revision_raw": None,
    }


class SearchEngineTests(unittest.TestCase):
    def test_normalize_case_separator_and_extension(self):
        value = normalize_code('  "abc_123.step"  ')
        self.assertEqual(value.cleaned, "abc_123")
        self.assertEqual(value.normalized, "ABC-123")
        self.assertEqual(value.compact, "ABC123")

    def test_numeric_excel_dot_zero_is_removed_only_for_numeric_values(self):
        self.assertEqual(normalize_code("12345.0").cleaned, "12345")
        self.assertEqual(normalize_code("ABC.0").cleaned, "ABC.0")

    def test_revision_and_descriptor_parsing(self):
        parsed = parse_filename("ABC-123_REV_C.stp", "/vault/released/ABC-123_REV_C.stp")
        self.assertEqual(parsed.parsed_code, "ABC-123")
        self.assertEqual(parsed.compact_code, "ABC123")
        self.assertEqual(parsed.revision_raw, "C")
        self.assertGreater(parsed.revision_rank, 0)
        self.assertEqual(parsed.folder_class, "released")

        drawing = parse_filename("ABC123_drawing.pdf", "/vault/current/ABC123_drawing.pdf")
        self.assertEqual(drawing.parsed_code, "ABC123")
        self.assertEqual(drawing.compact_code, "ABC123")

    def test_folder_word_boundaries_do_not_mark_folder_as_old(self):
        self.assertEqual(classify_folder("/projects/folder/ABC123.step")[0], "normal")
        self.assertEqual(classify_folder("/projects/old-data/ABC123.step")[0], "archive")

    def test_separator_difference_is_exact_normalized(self):
        query = normalize_code("ABC-123")
        row = candidate(
            filename="ABC123.stp",
            compact_stem="ABC123",
            compact_code="ABC123",
            parsed_code="ABC123",
            normalized_stem="ABC123",
        )
        self.assertEqual(match_candidate(query, row)[0], "exact_normalized")

    def test_exact_match_beats_newer_partial_match(self):
        query = normalize_code("ABC123")
        exact = candidate(
            filename="ABC123.stp",
            compact_stem="ABC123",
            compact_code="ABC123",
            parsed_code="ABC123",
            modified_at=10,
        )
        partial = candidate(
            filename="OLDABC123BACKUP.stp",
            compact_stem="OLDABC123BACKUP",
            compact_code="OLDABC123BACKUP",
            parsed_code="OLDABC123BACKUP",
            modified_at=999999,
        )
        self.assertGreater(ranking_key(query, exact), ranking_key(query, partial))

    def test_released_folder_beats_higher_archive_revision(self):
        query = normalize_code("ABC123")
        released_b = candidate(
            filename="ABC123_REV_B.stp",
            compact_stem="ABC123REVB",
            compact_code="ABC123",
            parsed_code="ABC123",
            folder_priority=500,
            revision_rank=1002,
        )
        archive_c = candidate(
            filename="ABC123_REV_C.stp",
            compact_stem="ABC123REVC",
            compact_code="ABC123",
            parsed_code="ABC123",
            folder_priority=50,
            revision_rank=1003,
        )
        self.assertGreater(ranking_key(query, released_b), ranking_key(query, archive_c))

    def test_fuzzy_result_is_suggestion_not_strong_match(self):
        query = normalize_code("R502A1B10M11BFL")
        row = candidate(
            file_id=7,
            filename="R502A1B10M11BF1.stp",
            compact_stem="R502A1B10M11BF1",
            compact_code="R502A1B10M11BF1",
            parsed_code="R502A1B10M11BF1",
        )
        self.assertIsNone(match_candidate(query, row)[0])
        suggestions = fuzzy_suggestions(query, [row])
        self.assertEqual(len(suggestions), 1)
        self.assertEqual(suggestions[0]["file_id"], 7)
        self.assertEqual(suggestions[0]["distance"], 1)


if __name__ == "__main__":
    unittest.main()
