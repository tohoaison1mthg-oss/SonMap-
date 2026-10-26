@echo off
setlocal
set "sonmap_diag=%~dp0check_connection.ps1"
if not exist "%sonmap_diag%" set "sonmap_diag=%LOCALAPPDATA%\SonMapPlus\App\check_connection.ps1"
if not exist "%sonmap_diag%" goto missing
"%SystemRoot%\SysWOW64\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File "%sonmap_diag%" -VietMapRoot "C:\VietMapXM"
pause
exit /b
:missing
echo Run Cai_dat.cmd first, then run this diagnostic again.
pause
exit /b 1
