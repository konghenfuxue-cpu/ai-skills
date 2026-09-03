@echo off
setlocal EnableExtensions
chcp 65001 >nul
title Reversible CBZ Merger
cd /d "%~dp0"

set "PYTHON_CMD="
where python.exe >nul 2>nul
if not errorlevel 1 set "PYTHON_CMD=python.exe"
if defined PYTHON_CMD goto FIND_SCRIPT
where py.exe >nul 2>nul
if not errorlevel 1 set "PYTHON_CMD=py.exe -3"
if defined PYTHON_CMD goto FIND_SCRIPT
echo [ERROR] Python was not found. Install Python and enable Add Python to PATH.
pause
exit /b 1

:FIND_SCRIPT
set "MERGE_SCRIPT="
for %%F in ("%~dp0merge_cbz*.py") do if not defined MERGE_SCRIPT set "MERGE_SCRIPT=%%~fF"
if defined MERGE_SCRIPT goto RUN_SCRIPT
echo [ERROR] merge_cbz.py was not found in this folder.
pause
exit /b 1

:RUN_SCRIPT
%PYTHON_CMD% "%MERGE_SCRIPT%"
set "EXIT_CODE=%ERRORLEVEL%"
if "%EXIT_CODE%"=="0" goto END
echo.
echo [ERROR] The merger stopped with exit code %EXIT_CODE%.

:END
echo.
pause
endlocal
