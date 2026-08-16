@echo off
setlocal
cd /d "%~dp0"
title Yu (Yu)

echo.
echo  ==========================================
echo    Yu (Yu) - one-click start
echo  ==========================================
echo.

if exist ".venv\Scripts\python.exe" goto :deps
echo  [1/4] Creating Python virtualenv .venv ...
python -m venv .venv
if errorlevel 1 goto :fail

:deps
echo  [1/4] Virtualenv ready.
echo  [2/4] Checking backend deps ...
".venv\Scripts\python.exe" -m pip install -e ".[api]" --quiet
if errorlevel 1 goto :fail
echo  [2/4] Backend deps ready.

echo  [3/4] Building frontend ...
pushd apps\web
if exist node_modules goto :build
echo       First run: installing frontend deps ...
call npm install --no-audit --no-fund
if errorlevel 1 goto :fail_npm

:build
call npm run build
if errorlevel 1 goto :fail_npm
popd
echo  [3/4] Frontend ready.

echo  [4/4] Starting Yu ... opening http://127.0.0.1:8787
start "" /b cmd /c "ping -n 4 127.0.0.1 >nul & start http://127.0.0.1:8787"
".venv\Scripts\python.exe" -m yu.api
goto :eof

:fail_npm
popd
:fail
echo.
echo  [ERROR] Start failed. See messages above.
echo  Press any key to exit...
pause >nul
exit /b 1
