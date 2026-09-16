from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .db import init_db
from .file_index import reindex_files
from .routers import folders, peek


def _resource_path(relative_path: str) -> Path:
    """Return a bundled resource path in source and PyInstaller builds."""
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).resolve().parents[2]
    return base / relative_path


def create_app() -> FastAPI:
    init_db()
    try:
        reindex_files()
    except Exception:
        # The app should still start if a configured drive is offline.
        pass

    app = FastAPI(title="Quick Peek API", version="0.5.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(peek.router)
    app.include_router(folders.router)

    @app.get("/api/health")
    def health():
        return {"ok": True, "name": "Quick Peek"}

    static_path = _resource_path("app/static")
    if static_path.exists():
        app.mount("/", StaticFiles(directory=str(static_path), html=True), name="frontend")

    return app


app = create_app()
