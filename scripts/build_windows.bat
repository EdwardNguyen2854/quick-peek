@echo off
:: ============================================================
:: Quick Peek — Windows Build Script
:: Packages the app as a standalone Windows .exe using
:: PyInstaller (onefile mode) + embedded React frontend.
::
:: Requirements (install first):
::   - Node.js   https://nodejs.org
::   - Python 3.9+ (add to PATH)
::   - pip install pyinstaller
:: ============================================================

setlocal enabledelayedexpansion

set "ROOT=%~dp0.."
set "BACKEND=%ROOT%\backend"
set "FRONTEND=%ROOT%\frontend"
set "OUT=%ROOT%\dist"
set "PYINSTALLER_OPTS=--onefile --windowed --clean"

echo [1/5] Checking Node.js...
where node >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js not found. Install from https://nodejs.org
    exit /b 1
)

echo [2/5] Installing frontend dependencies...
cd /d "%FRONTEND%"
call npm install
if errorlevel 1 (
    echo ERROR: npm install failed
    exit /b 1
)

echo [3/5] Building React frontend (outputs to backend/app/static)...
call npx vite build
if errorlevel 1 (
    echo ERROR: Vite build failed
    exit /b 1
)

echo [4/5] Installing Python build dependencies...
python -m pip install pyinstaller -q
if errorlevel 1 (
    echo WARNING: Could not install PyInstaller. Ensure it is installed.
)

echo [5/5] Packaging with PyInstaller...
if exist "%OUT%\QuickPeek.exe" del /q "%OUT%\QuickPeek.exe"
python -m PyInstaller "%ROOT%\quick_peek.spec" --distpath "%OUT%" --workpath "%ROOT%\build"
if errorlevel 1 (
    echo ERROR: PyInstaller packaging failed
    exit /b 1
)

echo.
echo ============================================================
echo Build complete: %OUT%\QuickPeek\QuickPeek.exe
echo.
echo Copy the entire %OUT%\QuickPeek folder to the target machine.
echo Required folder structure:
echo   QuickPeek/
echo     QuickPeek.exe
echo     data/
echo       files/     <- your CAD files
echo       quickpeek.sqlite3  <- created on first run
echo.
echo Configure with environment variables or a .env file:
echo   QUICKPEEK_FILE_ROOTS      = C:\path\to\files
echo   QUICKPEEK_ADMIN_USERNAME  = admin
echo   QUICKPEEK_ADMIN_PASSWORD  = your_password
echo ============================================================
exit /b 0