from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from app.converters.office_to_html import (
    LEGACY_FORMATS,
    libreoffice_to_html,
    office_to_html,
)


class OfficeToHtmlTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path("/tmp/test_office_converter")
        self.temp_dir.mkdir(exist_ok=True)

    def test_legacy_formats_defined(self):
        self.assertEqual(LEGACY_FORMATS, {".doc", ".xls", ".ppt"})

    def test_libreoffice_not_configured_returns_false(self):
        with patch("app.config.LIBREOFFICE_CMD", ""):
            input_path = self.temp_dir / "test.doc"
            output_path = self.temp_dir / "test.html"
            result = libreoffice_to_html(input_path, output_path)
            self.assertFalse(result)

    def test_libreoffice_converts_successfully(self):
        with patch("app.config.LIBREOFFICE_CMD", "soffice"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                input_path = self.temp_dir / "test.doc"
                output_path = self.temp_dir / "test.html"
                converted = self.temp_dir / "test.html"
                converted.write_text("<html>test</html>")

                with patch("pathlib.Path.exists", return_value=True):
                    with patch("pathlib.Path.rename"):
                        result = libreoffice_to_html(input_path, output_path)

                self.assertTrue(result)

    def test_libreoffice_returns_false_on_failure(self):
        with patch("app.config.LIBREOFFICE_CMD", "soffice"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=1, stderr="error")
                input_path = self.temp_dir / "test.doc"
                output_path = self.temp_dir / "test.html"

                result = libreoffice_to_html(input_path, output_path)
                self.assertFalse(result)

    def test_office_to_html_no_libreoffice_no_docx(self):
        with patch("app.config.LIBREOFFICE_CMD", ""):
            with patch("app.converters.office_to_html.DOCX_AVAILABLE", False):
                input_path = self.temp_dir / "test.doc"
                output_path = self.temp_dir / "test.html"

                with patch("pathlib.Path.stat") as mock_stat:
                    mock_stat.return_value = MagicMock(st_size=1024)
                    result = office_to_html(input_path, output_path)

                self.assertFalse(result)

    def test_office_to_html_falls_back_to_libreoffice_for_legacy(self):
        with patch("app.config.LIBREOFFICE_CMD", "soffice"):
            with patch("app.converters.office_to_html.docx_to_html", return_value=False):
                with patch("app.converters.office_to_html.libreoffice_to_html", return_value=True) as mock_lo:
                    input_path = self.temp_dir / "test.doc"
                    output_path = self.temp_dir / "test.html"

                    with patch("pathlib.Path.stat") as mock_stat:
                        mock_stat.return_value = MagicMock(st_size=1024)
                        result = office_to_html(input_path, output_path)
                        mock_lo.assert_called_once()

    def test_office_to_html_respects_size_limit(self):
        with patch("app.config.MAX_CONVERT_SIZE_MB", 1):
            input_path = self.temp_dir / "test.docx"
            output_path = self.temp_dir / "test.html"

            with patch("pathlib.Path.stat") as mock_stat:
                mock_stat.return_value = MagicMock(st_size=2 * 1024 * 1024)
                result = office_to_html(input_path, output_path)

            self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
