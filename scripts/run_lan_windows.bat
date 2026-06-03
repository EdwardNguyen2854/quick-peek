@echo off
set ROOT=%~dp0\..
for /f "tokens=2 delims=:" %%A in ('ipconfig ^| findstr /c:"IPv4 Address"') do (
  set IP=%%A
  goto :found
)
:found
set IP=%IP: =%
echo Starting Quick Peek for LAN...
echo.
echo Backend will listen on: http://0.0.0.0:8000
echo Frontend will listen on: http://0.0.0.0:5173
echo.
echo Other users should open: http://%IP%:5173
echo.
start "Quick Peek API" cmd /k "cd /d %ROOT%\backend && run_backend.bat"
start "Quick Peek UI" cmd /k "cd /d %ROOT%\frontend && npm install && npm run dev"
pause
