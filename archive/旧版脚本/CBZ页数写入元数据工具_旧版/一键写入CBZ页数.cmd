@echo off
chcp 65001 >nul
setlocal
set "PYTHONUTF8=1"
title CBZ PageCount Metadata Tool

cd /d "%~dp0"

where py >nul 2>nul
if not errorlevel 1 goto run_with_py

where python >nul 2>nul
if not errorlevel 1 goto run_with_python

echo [ERROR] Python 3 was not found.
echo Install Python 3 and enable "Add Python to PATH".
goto finish

:run_with_py
py -3 "%~dp0cbz_pagecount_metadata.py" %*
goto finish

:run_with_python
python "%~dp0cbz_pagecount_metadata.py" %*

:finish
echo.
pause
endlocal
