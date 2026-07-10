import sys
import os
from pathlib import Path

# PyInstaller entry point — imported by the .bat script.
# Run with: python -m PyInstaller quick_peek.spec

spec_dir = Path(SPECPATH).resolve()
root = spec_dir.parent

a = Analysis(
    [str(root / "backend" / "app" / "main.py")],
    pathex=[str(root / "backend")],
    binaries=[],
    datas=[],
    hiddenimports=[
        "uvicorn", "uvicorn.loop", "uvicorn.config", "uvicorn.main", "uvicorn.loops.auto",
        "uvicorn.protocols", "uvicorn.protocols.http", "uvicorn.protocols.http.auto",
        "uvicorn.lifespan", "uvicorn.lifespan.auto",
        "fastapi", "starlette", "pydantic", "pydantic.fields", "pydantic.main",
        "python_jose", "python_jose.jwa", "python_jose.jwt",
        "jose", "jose.backends", "jose.exceptions", "jose.backends._asymmetric",
        "cryptography", "cryptography.hazmat", "cryptography.hazmat.binders._openssl",
        "python_multipart",
        "starlette.middleware", "starlette.middleware.cors",
        "ldap3", "ldap3.core", "ldap3.protocol", "ldap3.strategy",
        "ldap3.operation", "ldap3.utils",
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