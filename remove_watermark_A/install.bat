@echo off
setlocal
cd /d "%~dp0"
echo Installing dependencies, please wait...
python -m pip uninstall -y opencv-python-headless
python -m pip install --force-reinstall opencv-python
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo Install failed.
    if not "%NO_PAUSE%"=="1" pause > nul
    exit /b 1
)
echo.
echo Install completed.
if not "%NO_PAUSE%"=="1" pause > nul
