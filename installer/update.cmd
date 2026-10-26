@echo off
setlocal
cd /d "%~dp0"
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File "%~dp0Cai_dat.ps1"
if not errorlevel 1 exit /b 0
echo.
echo Installation stopped. Read the message above, then try again.
pause
exit /b 1
