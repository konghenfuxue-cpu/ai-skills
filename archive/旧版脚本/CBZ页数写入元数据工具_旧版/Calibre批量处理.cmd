@echo off
chcp 65001 >nul
setlocal
set "PYTHONUTF8=1"
title Calibre CBZ Batch PageCount Tool

cd /d "%~dp0"

echo ============================================================
echo Calibre batch mode: recursive scan, in-place update, no backup
echo ============================================================
echo Close Calibre, Calibre Viewer and Explorer library windows first.
echo This mode does not create backup folders inside the Calibre library.
echo.
choice /C YN /N /M "Continue? [Y/N]: "
if errorlevel 2 goto finish

set "TARGET_PATH=%~1"

where py >nul 2>nul
if not errorlevel 1 goto run_with_py

where python >nul 2>nul
if not errorlevel 1 goto run_with_python

echo [ERROR] Python 3 was not found.
echo Install Python 3 and enable "Add Python to PATH".
goto finish

:run_with_py
if defined TARGET_PATH (
    py -3 "%~dp0cbz_pagecount_metadata.py" -r --no-backup "%TARGET_PATH%"
) else (
    py -3 "%~dp0cbz_pagecount_metadata.py" --no-backup
)
goto finish

:run_with_python
if defined TARGET_PATH (
    python "%~dp0cbz_pagecount_metadata.py" -r --no-backup "%TARGET_PATH%"
) else (
    python "%~dp0cbz_pagecount_metadata.py" --no-backup
)

:finish
echo.
pause
endlocal
