from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List, Optional

try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass

BASE_DIR = Path(__file__).resolve().parents[1]


def _get(name: str, default: str) -> str:
    return os.environ.get(name, default)


SECRET_KEY = _get("QUICKPEEK_SECRET_KEY", "dev-secret-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(_get("QUICKPEEK_ACCESS_TOKEN_EXPIRE_MINUTES", "720"))

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
    p = Path(item)
    if not p.is_absolute():
        p = BASE_DIR / p
    FILE_ROOTS.append(p)

ADMIN_USERNAME = _get("QUICKPEEK_ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = _get("QUICKPEEK_ADMIN_PASSWORD", "admin123")

MANUAL_SECONDS_PER_FILE = int(_get("QUICKPEEK_MANUAL_SECONDS_PER_FILE", "45"))
APP_SECONDS_PER_FILE = int(_get("QUICKPEEK_APP_SECONDS_PER_FILE", "8"))

STEP_CONVERTER_CMD = _get("QUICKPEEK_STEP_CONVERTER_CMD", "").strip()
LIBREOFFICE_CMD = _get("QUICKPEEK_LIBREOFFICE_CMD", "").strip()  # auto-detect if empty
MAX_CONVERT_SIZE_MB = int(_get("QUICKPEEK_MAX_CONVERT_SIZE_MB", "100"))

SUPPORTED_FORMATS = {
    "step": [".stp", ".step"],
    "pdf": [".pdf"],
    "dxf": [".dxf"],
    "obj": [".obj"],
    "doc": [".doc", ".docx"],
    "xls": [".xls", ".xlsx"],
    "ppt": [".ppt", ".pptx"],
    "md": [".md"],
    "txt": [".txt"],
    "html": [".html", ".htm"],
}

DEFAULT_USER_PERMISSIONS = ["use_quick_peek", "view_step", "view_pdf", "view_dxf", "view_obj", "view_doc", "view_xls", "view_ppt", "view_md", "view_txt", "view_html"]
ADMIN_PERMISSIONS = [
    "use_quick_peek",
    "view_step",
    "view_pdf",
    "view_dxf",
    "view_obj",
    "view_doc",
    "view_xls",
    "view_ppt",
    "view_md",
    "view_txt",
    "view_html",
    "view_dashboard",
    "manage_users",
    "download_files",
]

# ── LDAP ────────────────────────────────────────────────────────────────────
LDAP_URL: Optional[str] = _get("QUICKPEEK_LDAP_URL", "") or None
LDAP_BIND_DN_TEMPLATE: str = _get("QUICKPEEK_LDAP_BIND_DN_TEMPLATE", "{username}@domain.local")
LDAP_USER_SEARCH_BASE: str = _get("QUICKPEEK_LDAP_USER_SEARCH_BASE", "DC=domain,DC=local")
LDAP_USER_SEARCH_FILTER: str = _get("QUICKPEEK_LDAP_USER_SEARCH_FILTER", "(sAMAccountName={username})")
LDAP_GROUP_BASE: str = _get("QUICKPEEK_LDAP_GROUP_BASE", "DC=domain,DC=local")
LDAP_USE_SSL: bool = _get("QUICKPEEK_LDAP_USE_SSL", "true").lower() in ("1", "true", "yes")
LDAP_BIND_CACHE_TTL: int = int(_get("QUICKPEEK_LDAP_BIND_CACHE_TTL", "60"))
LDAP_GROUP_PERMISSIONS: str = _get("QUICKPEEK_LDAP_GROUP_PERMISSIONS", "{}")

# ── History / Retention ─────────────────────────────────────────────────────
HISTORY_RETENTION_DAYS: int = int(_get("QUICKPEEK_HISTORY_RETENTION_DAYS", "90"))

# ── Folder Permissions ──────────────────────────────────────────────────────
FOLDER_DEFAULT_ALLOW: bool = _get("QUICKPEEK_FOLDER_DEFAULT_ALLOW", "true").lower() in ("1", "true", "yes")

# ── Tags ────────────────────────────────────────────────────────────────────
MAX_TAGS_PER_FILE: int = int(_get("QUICKPEEK_MAX_TAGS_PER_FILE", "50"))
MAX_DISTINCT_TAGS: int = int(_get("QUICKPEEK_MAX_DISTINCT_TAGS", "1000"))

# ── API Keys ────────────────────────────────────────────────────────────────
API_KEY_DEFAULT_TTL_DAYS: int = int(_get("QUICKPEEK_API_KEY_DEFAULT_TTL_DAYS", "365"))

# ── Rate Limiting ────────────────────────────────────────────────────────────
LOGIN_RATE_LIMIT_PER_MIN: int = int(_get("QUICKPEEK_LOGIN_RATE_LIMIT_PER_MIN", "5"))

# ── LDAP Group Permissions Map (parsed JSON) ────────────────────────────────
try:
    LDAP_GROUP_PERMISSIONS_MAP: dict = json.loads(LDAP_GROUP_PERMISSIONS)
except (json.JSONDecodeError, TypeError):
    LDAP_GROUP_PERMISSIONS_MAP: dict = {}
