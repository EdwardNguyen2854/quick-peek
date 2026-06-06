from __future__ import annotations

from pathlib import Path
import html

try:
    import markdown
    MARKDOWN_AVAILABLE = True
except ImportError:
    MARKDOWN_AVAILABLE = False


def markdown_to_html(input_path: Path, output_path: Path) -> bool:
    """
    Convert a Markdown file to styled HTML.

    Args:
        input_path: Path to the input Markdown file
        output_path: Path to the output HTML file

    Returns:
        True if HTML was created successfully, False otherwise
    """
    if not MARKDOWN_AVAILABLE:
        return False

    try:
        content = input_path.read_text(encoding="utf-8", errors="ignore")

        # Convert markdown with extensions
        html_body = markdown.markdown(
            content,
            extensions=["fenced_code", "tables", "codehilite"]
        )

        # Wrap in styled HTML
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(input_path.name)}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.6;
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
            color: #333;
        }}
        pre {{
            background-color: #f6f8fa;
            padding: 16px;
            border-radius: 6px;
            overflow-x: auto;
        }}
        code {{
            font-family: "SF Mono", Monaco, Consolas, "Liberation Mono", monospace;
            font-size: 14px;
            background-color: #f6f8fa;
            padding: 2px 6px;
            border-radius: 3px;
        }}
        pre code {{
            padding: 0;
            background-color: transparent;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 16px 0;
        }}
        th, td {{
            border: 1px solid #d0d7de;
            padding: 8px 12px;
            text-align: left;
        }}
        th {{
            background-color: #f6f8fa;
        }}
        blockquote {{
            border-left: 4px solid #d0d7de;
            margin: 16px 0;
            padding-left: 16px;
            color: #6e7781;
        }}
 img {{
            max-width: 100%;
            height: auto;
        }}
</style>
</head>
<body>
{html_body}
</body>
</html>"""

        output_path.write_text(html_content, encoding="utf-8")
        return True

    except Exception:
        return False
