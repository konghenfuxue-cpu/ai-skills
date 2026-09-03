@echo off
setlocal EnableExtensions
chcp 65001 >nul
title CBZ Collection Splitter
cd /d "%~dp0"

set "PYTHON_CMD="
where python.exe >nul 2>nul
if not errorlevel 1 set "PYTHON_CMD=python.exe"
if defined PYTHON_CMD goto RUN_SCRIPT
where py.exe >nul 2>nul
if not errorlevel 1 set "PYTHON_CMD=py.exe -3"
if defined PYTHON_CMD goto RUN_SCRIPT
echo [ERROR] Python was not found. Install Python and enable Add Python to PATH.
pause
exit /b 1

:RUN_SCRIPT
%PYTHON_CMD% "%~dp0split_cbz_collection.py" %*
set "EXIT_CODE=%ERRORLEVEL%"
if "%EXIT_CODE%"=="0" goto END
echo.
echo [ERROR] The splitter stopped with exit code %EXIT_CODE%.

:END
echo.
pause
endlocal
