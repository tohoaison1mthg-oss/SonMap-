@echo off
setlocal
cd /d "%~dp0"
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_topology.ps1"
if not errorlevel 1 exit /b 0
echo.
echo SonMap could not start. Read the message above and TOPOLOGY.md.
pause
exit /b 1
