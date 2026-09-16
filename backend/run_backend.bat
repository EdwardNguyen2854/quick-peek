@echo off
setlocal
cd /d "%~dp0"
if "%QUICKPEEK_HOST%"=="" set "QUICKPEEK_HOST=127.0.0.1"

if not exist ".venv\Scripts\python.exe" (
  echo Creating backend virtual environment...
  py -m venv .venv
  if errorlevel 1 (
    echo ERROR: Could not create the Python virtual environment.
    exit /b 1
  )
)

echo Installing backend dependencies...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 exit /b 1

".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
  echo ERROR: Backend dependency installation failed. Server was not started.
  exit /b 1
)

echo Starting Quick Peek API on http://%QUICKPEEK_HOST%:8000
".venv\Scripts\python.exe" -m uvicorn app.main:app --reload --host %QUICKPEEK_HOST% --port 8000
