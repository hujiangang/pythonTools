@echo off
setlocal
cd /d "%~dp0"
python watermark_remover_asr.py input.mp4 -o output --no-subtitle
if errorlevel 1 (
    echo.
    echo Task failed.
    if not "%NO_PAUSE%"=="1" pause > nul
    exit /b 1
)
echo.
echo Task completed.
if not "%NO_PAUSE%"=="1" pause > nul
