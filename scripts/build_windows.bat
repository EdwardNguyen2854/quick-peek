@echo off
setlocal enabledelayedexpansion

set "ROOT=%~dp0.."
set "BACKEND=%ROOT%\backend"
set "FRONTEND=%ROOT%\frontend"
set "OUT=%ROOT%\dist"

echo [1/6] Checking Node.js...
where node >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js not found.
    exit /b 1
)

echo [2/6] Installing frontend dependencies...
cd /d "%FRONTEND%"
call npm install
if errorlevel 1 exit /b 1

echo [3/6] Building React frontend...
call npm run build
if errorlevel 1 exit /b 1

echo [4/6] Installing backend dependencies...
cd /d "%BACKEND%"
py -m pip install -r requirements.txt
if errorlevel 1 exit /b 1

echo [5/6] Installing PyInstaller...
py -m pip install pyinstaller
if errorlevel 1 exit /b 1

echo [6/6] Packaging Quick Peek...
if exist "%OUT%\QuickPeek" rmdir /s /q "%OUT%\QuickPeek"
py -m PyInstaller "%ROOT%\quick_peek.spec" --distpath "%OUT%" --workpath "%ROOT%\build"
if errorlevel 1 exit /b 1

echo.
echo Build complete: %OUT%\QuickPeek\QuickPeek.exe
echo Configure QUICKPEEK_FILE_ROOTS and QUICKPEEK_STEP_CONVERTER_CMD as needed.
exit /b 0
