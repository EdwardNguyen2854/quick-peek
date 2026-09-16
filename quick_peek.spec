import sys
import os
from pathlib import Path

spec_dir = Path(SPECPATH).resolve()
root = spec_dir.parent
static_dir = root / "backend" / "app" / "static"

datas = []
if static_dir.exists():
    datas.append((str(static_dir), "app/static"))

a = Analysis(
    [str(root / "backend" / "app" / "main.py")],
    pathex=[str(root / "backend")],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "uvicorn", "uvicorn.loop", "uvicorn.config", "uvicorn.main", "uvicorn.loops.auto",
        "uvicorn.protocols", "uvicorn.protocols.http", "uvicorn.protocols.http.auto",
        "uvicorn.lifespan", "uvicorn.lifespan.auto",
        "fastapi", "starlette", "pydantic", "pydantic.fields", "pydantic.main",
        "starlette.middleware", "starlette.middleware.cors",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="QuickPeek",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulator=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
    manifest=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="QuickPeek",
)
