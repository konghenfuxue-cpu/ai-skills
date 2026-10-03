@echo off
setlocal
chcp 65001 >nul
where py >nul 2>nul
if %errorlevel%==0 (
    py -3 "%~dp0one_click_epub.py" %*
) else (
    python "%~dp0one_click_epub.py" %*
)
echo.
pause
