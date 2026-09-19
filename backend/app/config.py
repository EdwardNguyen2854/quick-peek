from __future__ import annotations

import os
from pathlib import Path
from typing import List

try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass

BASE_DIR = Path(__file__).resolve().parents[1]


def _get(name: str, default: str) -> str:
    return os.environ.get(name, default)


DB_PATH = Path(_get("QUICKPEEK_DB_PATH", str(BASE_DIR / "data" / "quickpeek.sqlite3")))
if not DB_PATH.is_absolute():
    DB_PATH = BASE_DIR / DB_PATH
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

CACHE_DIR = BASE_DIR / "cache"
PREVIEW_DIR = CACHE_DIR / "previews"
PREVIEW_DIR.mkdir(parents=True, exist_ok=True)

raw_roots = _get("QUICKPEEK_FILE_ROOTS", str(BASE_DIR / "data" / "files"))
FILE_ROOTS: List[Path] = []
for item in raw_roots.split(";") if ";" in raw_roots else raw_roots.split(","):
    item = item.strip().strip('"')
    if not item:
        continue
    path = Path(item)
    if not path.is_absolute():
        path = BASE_DIR / path
    FILE_ROOTS.append(path)

LIBREOFFICE_CMD = _get("QUICKPEEK_LIBREOFFICE_CMD", "").strip()
MAX_CONVERT_SIZE_MB = int(_get("QUICKPEEK_MAX_CONVERT_SIZE_MB", "100"))

PREVIEW_CACHE_MAX_SIZE_MB = int(_get("QUICKPEEK_PREVIEW_CACHE_MAX_SIZE_MB", "500"))
PREVIEW_CACHE_MAX_AGE_DAYS = int(_get("QUICKPEEK_PREVIEW_CACHE_MAX_AGE_DAYS", "7"))

SUPPORTED_FORMATS = {
    "step": [".stp", ".step"],
    "pdf": [".pdf"],
    "dxf": [".dxf"],
    "doc": [".doc", ".docx"],
    "xls": [".xls", ".xlsx"],
    "ppt": [".ppt", ".pptx"],
    "md": [".md"],
    "txt": [".txt"],
    "html": [".html", ".htm"],
}
