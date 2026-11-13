@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\build_game.ps1" %*
exit /b %errorlevel%
