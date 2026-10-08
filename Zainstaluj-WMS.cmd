@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0installer\Run-Installer.ps1"
exit /b %ERRORLEVEL%
