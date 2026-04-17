@echo off
setlocal
cd /d "%~dp0"

set "VIDEO=input.mp4"
set "OUT_DIR=output\extracted"

if not "%~1"=="" set "VIDEO=%~1"
if not "%~2"=="" set "OUT_DIR=%~2"

python extract_media.py "%VIDEO%" -o "%OUT_DIR%"
if errorlevel 1 (
    echo.
    echo Extract failed.
    if not "%NO_PAUSE%"=="1" pause > nul
    exit /b 1
)

echo.
echo Extract completed.
if not "%NO_PAUSE%"=="1" pause > nul
