from __future__ import annotations

import html
from pathlib import Path

try:
    from docx import Document as DocxDocument
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

try:
    from openpyxl import load_workbook
    XLSX_AVAILABLE = True
except ImportError:
    XLSX_AVAILABLE = False

try:
    from pptx import Presentation
    PPTX_AVAILABLE = True
except ImportError:
    PPTX_AVAILABLE = False


DOCX_STYLE = """
body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    line-height: 1.6;
    max-width: 900px;
    margin: 0 auto;
    padding: 20px;
    color: #333;
}
h1, h2, h3 { margin-top: 1.5em; margin-bottom: 0.5em; }
h1 { font-size: 24px; border-bottom: 2px solid #eee; padding-bottom: 8px; }
h2 { font-size: 20px; }
h3 { font-size: 17px; }
p { margin: 0.8em 0; }
ul, ol { margin: 0.8em 0; padding-left: 24px; }
li { margin: 0.3em 0; }
table { border-collapse: collapse; width: 100%; margin: 16px 0; }
th, td { border: 1px solid #d0d7de; padding: 8px 12px; text-align: left; }
th { background-color: #f6f8fa; font-weight: 600; }
code { font-family: "SF Mono", Monaco, Consolas, monospace; font-size: 13px; background-color: #f6f8fa; padding: 2px 6px; border-radius: 3px; }
pre { background-color: #f6f8fa; padding: 16px; border-radius: 6px; overflow-x: auto; }
pre code { padding: 0; background: none; }
blockquote { border-left: 4px solid #d0d7de; margin: 16px 0; padding-left: 16px; color: #6e7781; }
"""

def _make_html(title: str, body_content: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(title)}</title>
    <style>{DOCX_STYLE}</style>
</head>
<body>
{body_content}
</body>
</html>"""


def _escape(text: str) -> str:
    return html.escape(str(text) if text else "")


def docx_to_html(input_path: Path, output_path: Path) -> bool:
    """Convert a Word .docx file to HTML using python-docx."""
    if not DOCX_AVAILABLE:
        return False

    try:
        doc = DocxDocument(str(input_path))
        parts = []

        for para in doc.paragraphs:
            style = para.style.name.lower() if para.style else ""
            text = _escape(para.text).strip()
            if not text:
                continue

            if style.startswith("heading"):
                level = style.replace("heading", "").strip()
                try:
                    lvl = int(level) if level else 1
                except ValueError:
                    lvl = 1
                parts.append(f"<h{lvl}>{text}</h{lvl}>")
            elif style == "list bullet":
                parts.append(f"<li>{text}</li>")
            elif style == "list number":
                parts.append(f"<li>{text}</li>")
            else:
                parts.append(f"<p>{text}</p>")

        # Tables
        for table in doc.tables:
            rows = []
            for row in table.rows:
                cells = [_escape(cell.text).strip() for cell in row.cells]
                rows.append(f"<tr><td>{'</td><td>'.join(cells)}</td></tr>")
            if rows:
                parts.append(f"<table><thead><tr><th>{'</th><th>'.join([_escape(h.text) for h in table.rows[0].cells])}</th></tr></thead><tbody>{''.join(rows[1:])}</tbody></table>")

        body = "\n".join(parts) if parts else "<p>No content found</p>"
        output_path.write_text(_make_html(input_path.name, body), encoding="utf-8")
        return True
    except Exception:
        return False


def xlsx_to_html(input_path: Path, output_path: Path) -> bool:
    """Convert an Excel .xlsx file to HTML using openpyxl."""
    if not XLSX_AVAILABLE:
        return False

    try:
        wb = load_workbook(str(input_path), data_only=True)
        sheets = []

        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            rows = []
            for row in ws.iter_rows(values_only=True):
                cells = [_escape(str(c) if c is not None else "") for c in row]
                if any(c.strip() for c in cells):
                    rows.append(f"<tr><td>{'</td><td>'.join(cells)}</td></tr>")

            table_html = f"<table><tbody>{''.join(rows)}</tbody></table>" if rows else "<p>Empty sheet</p>"
            sheets.append(f'<div style="margin-bottom:24px"><h3 style="margin:0 0 8px">{_escape(sheet_name)}</h3>{table_html}</div>')

        body = "\n".join(sheets) if sheets else "<p>No sheets found</p>"
        output_path.write_text(_make_html(input_path.name, body), encoding="utf-8")
        return True
    except Exception:
        return False


def pptx_to_html(input_path: Path, output_path: Path) -> bool:
    """Convert a PowerPoint .pptx file to HTML using python-pptx."""
    if not PPTX_AVAILABLE:
        return False

    try:
        prs = Presentation(str(input_path))
        slides = []

        for i, slide in enumerate(prs.slides, 1):
            parts = []
            for shape in slide.shapes:
                if hasattr(shape, "text") and shape.text.strip():
                    parts.append(f"<p>{_escape(shape.text.strip())}</p>")

            content = "\n".join(parts) if parts else "<p>Empty slide</p>"
            slides.append(f'<div style="margin-bottom:20px;padding:16px;border:1px solid #eee;border-radius:8px"><h4 style="margin:0 0 8px">Slide {i}</h4>{content}</div>')

        body = "\n".join(slides) if slides else "<p>No slides found</p>"
        output_path.write_text(_make_html(input_path.name, body), encoding="utf-8")
        return True
    except Exception:
        return False


def office_to_html(input_path: Path, output_path: Path) -> bool:
    """
    Convert an Office document (docx, xlsx, pptx) to HTML using pure Python.
    Falls back to trying each converter based on extension.

    Args:
        input_path: Path to the input Office document
        output_path: Path to the output HTML file

    Returns:
        True if HTML was created successfully, False otherwise
    """
    from ..config import MAX_CONVERT_SIZE_MB

    # Check file size
    try:
        size_mb = input_path.stat().st_size / (1024 * 1024)
        if size_mb > MAX_CONVERT_SIZE_MB:
            return False
    except Exception:
        return False

    ext = input_path.suffix.lower()

    if ext in (".docx", ".doc"):
        return docx_to_html(input_path, output_path)
    elif ext in (".xlsx", ".xls"):
        return xlsx_to_html(input_path, output_path)
    elif ext in (".pptx", ".ppt"):
        return pptx_to_html(input_path, output_path)

    return False