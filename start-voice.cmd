@echo off
setlocal
rem Resolve PowerShell from PATH instead of relying on the .ps1 file association.
set "YU_PWSH="
for /f "delims=" %%P in ('where pwsh.exe 2^>nul') do if not defined YU_PWSH set "YU_PWSH=%%P"
if not defined YU_PWSH (
  echo PowerShell 7 was not found in PATH. Open PowerShell 7 and run start-voice.ps1.
  pause
  exit /b 1
)
"%YU_PWSH%" -NoLogo -NoProfile -NoExit -File "%~dp0start-voice.ps1"
endlocal
