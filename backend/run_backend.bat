@echo off
setlocal
cd /d "%~dp0"

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

echo Starting Quick Peek API on http://127.0.0.1:8000
".venv\Scripts\python.exe" -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
