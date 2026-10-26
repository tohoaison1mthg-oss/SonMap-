@echo off
setlocal
cd /d "%~dp0"
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_topology.ps1" -EnvironmentRoot "%LOCALAPPDATA%\SonMapPlus\App" -InstallPython
if not errorlevel 1 exit /b 0
pause
exit /b 1
