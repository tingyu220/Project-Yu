@echo off
cd /d "%~dp0"

echo.
echo  Starting Yu API (8787) and Web dev server (5173)...
echo  Two windows will open. Close both (or Ctrl+C) to stop.
echo.

start "Yu API" cmd /k ".venv\Scripts\python.exe -m yu.api"
start "Yu Web" cmd /k "cd apps\web && npm run dev"

start "" /b cmd /c "ping -n 4 127.0.0.1 >nul & start http://localhost:5173"
