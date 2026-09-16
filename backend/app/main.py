from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .db import init_db
from .file_index import reindex_files
from .routers import folders, peek


def _static_path() -> Path:
    """Return the generated frontend directory in source and PyInstaller builds."""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "app" / "static"
    return Path(__file__).resolve().parent / "static"


def create_app() -> FastAPI:
    init_db()
    try:
        reindex_files()
    except Exception:
        # The app should still start if a configured drive is offline.
        pass

    app = FastAPI(title="Quick Peek API", version="0.8.0")
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

    static_path = _static_path()
    if static_path.exists():
        app.mount("/", StaticFiles(directory=str(static_path), html=True), name="frontend")

    return app


app = create_app()
