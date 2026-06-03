@echo off
set ROOT=%~dp0\..
start "Quick Peek API" cmd /k "cd /d %ROOT%\backend && run_backend.bat"
start "Quick Peek UI" cmd /k "cd /d %ROOT%\frontend && npm install && npm run dev"
echo Backend: http://127.0.0.1:8000/api/health
echo Frontend: http://127.0.0.1:5173
