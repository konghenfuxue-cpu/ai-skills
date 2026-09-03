@echo off
setlocal
chcp 65001 >nul
set "TOOL_DIR=%~dp0"

where py >nul 2>nul
if not errorlevel 1 (
    py -3 "%TOOL_DIR%check_incomplete_reports.py" %*
) else (
    python "%TOOL_DIR%check_incomplete_reports.py" %*
)

echo.
pause
