from __future__ import annotations

import sys
from pathlib import Path

# ── frozen-exe support ──────────────────────────────────────────
def _resource_path(relative_path: str) -> Path:
    """Return path to a bundled resource whether running as .py or frozen .exe."""
    if getattr(sys, 'frozen', False):
        # PyInstaller sets _MEIPASS to the tmp extracted folder.
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).resolve().parents[2]
    return base / relative_path


from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .auth import ensure_admin_user
from .config import ADMIN_PASSWORD, ADMIN_PERMISSIONS, ADMIN_USERNAME
from .db import init_db
from .file_index import reindex_files
from .routers import admin, auth, dashboard, folders, peek


def create_app() -> FastAPI:
    init_db()
    ensure_admin_user(ADMIN_USERNAME, ADMIN_PASSWORD, ADMIN_PERMISSIONS)
    try:
        reindex_files()
    except Exception:
        # The app should still boot even if a network drive is offline.
        pass

    app = FastAPI(title="Quick Peek API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(auth.router)
    app.include_router(admin.router)
    app.include_router(peek.router)
    app.include_router(dashboard.router)
    app.include_router(folders.router)

    @app.get("/api/health")
    def health():
        return {"ok": True, "name": "Quick Peek"}

    # ── embedded frontend (only present when bundled with PyInstaller) ──
    static_path = _resource_path("app" / "static")
    if static_path.exists():
        app.mount("/", StaticFiles(directory=str(static_path), html=True), name="frontend")

    return app


app = create_app()