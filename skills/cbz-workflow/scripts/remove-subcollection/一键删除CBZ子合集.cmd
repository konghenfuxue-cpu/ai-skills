@echo off
setlocal
chcp 65001 >nul
title CBZ Subcollection Remover
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 "%~dp0remove_cbz_subcollection.py" %*
) else (
    python "%~dp0remove_cbz_subcollection.py" %*
)

echo.
pause
endlocal
