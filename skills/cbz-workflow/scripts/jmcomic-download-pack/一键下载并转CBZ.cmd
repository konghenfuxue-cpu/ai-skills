@echo off
setlocal EnableExtensions
title JMComic Download and CBZ Builder

cd /d "%~dp0"

where python.exe >nul 2>nul
if errorlevel 1 goto NO_PYTHON

python.exe -c "import jmcomic; import rich; import yaml; import PIL; import zhconv" >nul 2>nul
if errorlevel 1 goto INSTALL_DEPS
goto ASK_ID

:INSTALL_DEPS
echo Installing required Python packages...
python.exe -m pip install --upgrade jmcomic rich pyyaml pillow zhconv
if errorlevel 1 goto INSTALL_FAILED

:ASK_ID
echo.
echo ========================================
echo 1. Download by JM ID
echo 2. Search and select
echo 3. Scan existing JPG folders and resume CBZ
echo 4. Exit
echo ========================================
set "MODE="
set /p "MODE=Select 1, 2, 3 or 4: "
if "%MODE%"=="1" goto DIRECT_ID
if "%MODE%"=="2" goto SEARCH_ID
if "%MODE%"=="3" goto RESUME_SCAN
if "%MODE%"=="4" goto END
echo [ERROR] Invalid menu choice.
goto ASK_ID

:SEARCH_ID
python.exe "%~dp0search_and_select.py" "%~dp0option.yml" "%~dp0selected_id.txt"
if errorlevel 1 goto SEARCH_FAILED
set "JM_ID="
if not exist "%~dp0selected_id.txt" goto ASK_ID
for %%Z in ("%~dp0selected_id.txt") do if %%~zZ==0 goto ASK_ID
goto SELECT_SIZE

:RESUME_SCAN
python.exe "%~dp0resume_scan.py" "D:\JMComic\download" "%~dp0option.yml" "%~dp0pack_cbz.py"
if errorlevel 1 goto PACK_FAILED
goto END

:DIRECT_ID
set "JM_ID="
set /p "JM_ID=Enter JM ID (multiple IDs: 123,456,789): "
if not defined JM_ID goto END
>"%~dp0selected_id.txt" type nul
for %%I in (%JM_ID:,= %) do >>"%~dp0selected_id.txt" echo %%I
goto SELECT_SIZE

:SELECT_SIZE
echo.
echo Image size for mobile CBZ:
echo 1. 1440 px - smaller files
echo 2. 1600 px - recommended
echo 3. 1800 px - sharper
echo 4. Original size
set "SIZE_MODE="
set /p "SIZE_MODE=Select 1, 2, 3 or 4 [2]: "
if not defined SIZE_MODE set "SIZE_MODE=2"
if "%SIZE_MODE%"=="1" set "MAX_WIDTH=1440"
if "%SIZE_MODE%"=="2" set "MAX_WIDTH=1600"
if "%SIZE_MODE%"=="3" set "MAX_WIDTH=1800"
if "%SIZE_MODE%"=="4" set "MAX_WIDTH=0"
if not defined MAX_WIDTH set "MAX_WIDTH=1600"

echo.
echo Processing selected works one by one...
set "FAILED="
for /f "usebackq tokens=* delims=" %%I in ("%~dp0selected_id.txt") do call :PROCESS_ONE "%%I"
if defined FAILED goto MULTI_FAILED

echo.
echo Finished. CBZ output: D:\JMComic\download\CBZ
goto END

:PROCESS_ONE
set "JM_ID=%~1"
echo(%JM_ID%| %SystemRoot%\System32\findstr.exe /r "^[0-9][0-9]*$" >nul
if errorlevel 1 (
    echo [ERROR] Invalid JM ID skipped: %JM_ID%
    set "FAILED=1"
    exit /b
)
echo.
echo Downloading JM%JM_ID%...
jmcomic.exe %JM_ID% --option "%~dp0option.yml"
set "DOWNLOAD_RC=%ERRORLEVEL%"
if not "%DOWNLOAD_RC%"=="0" echo [WARNING] Download returned error; creating the compact integrity report now.
echo Creating CBZ for JM%JM_ID%...
python.exe "%~dp0pack_cbz.py" %JM_ID% "D:\JMComic\download" 25 %MAX_WIDTH% 85 "%~dp0option.yml" %DOWNLOAD_RC%
if errorlevel 1 (
    echo [WARNING] JM%JM_ID% is incomplete or CBZ creation failed. Check its integrity report.
    set "FAILED=1"
)
exit /b

:MULTI_FAILED
echo.
echo [WARNING] Some works failed. Successful works were kept; review messages above.
goto END

:NO_PYTHON
echo [ERROR] Python was not found in PATH.
echo Install Python and enable Add Python to PATH.
goto END

:INSTALL_FAILED
echo [ERROR] Failed to install required Python packages.
goto END

:BAD_ID
echo [ERROR] JM ID must contain digits only.
goto END

:SEARCH_FAILED
echo.
echo [ERROR] Search failed. Review the message above.
goto END

:DOWNLOAD_FAILED
echo.
echo [ERROR] Download did not finish successfully. Review the log above.
goto END

:PACK_FAILED
echo.
echo [ERROR] CBZ creation failed. Review the message above.

:END
echo.
pause
endlocal
