@echo off
setlocal
set "sonmap_test=%~dp0test_scan_v8i.ps1"
if not exist "%sonmap_test%" set "sonmap_test=%LOCALAPPDATA%\SonMapPlus\App\test_scan_v8i.ps1"
if not exist "%sonmap_test%" goto missing
echo Open and save the DGN in MicroStation V8i before this test.
"%SystemRoot%\SysWOW64\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File "%sonmap_test%" -Levels "10,23,32"
pause
exit /b
:missing
echo Run Cai_dat.cmd first.
pause
exit /b 1
