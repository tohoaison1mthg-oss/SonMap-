@echo off
setlocal
cd /d "%~dp0"
where code >nul 2>&1
if errorlevel 1 goto missing
call code "%~dp0SonMap.code-workspace"
exit /b
:missing
echo Open this folder in Visual Studio Code and install the official OpenAI Codex extension.
echo Optional VS Code install: winget install --id Microsoft.VisualStudioCode -e --source winget
echo Extension ID: openai.chatgpt
pause
