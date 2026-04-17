@echo off
setlocal
cd /d "%~dp0"

set "VIDEO=input.mp4"
set "PICK_TIME=1"
set "START_TIME=0"
set "END_TIME=4"
set "REGION_NAME=watermark"

if not "%~1"=="" set "PICK_TIME=%~1"
if not "%~2"=="" set "START_TIME=%~2"
if not "%~3"=="" set "END_TIME=%~3"
if not "%~4"=="" set "REGION_NAME=%~4"

if not "%~1"=="" goto RUN_PICKER
if "%NO_PROMPT%"=="1" goto RUN_PICKER

echo Pick watermark region coordinates
echo.
echo Video file: %VIDEO%
echo Press Enter to use the default value shown in brackets.
echo.

set "ASK_PICK_TIME="
set /p "ASK_PICK_TIME=Frame time to display, seconds [%PICK_TIME%]: "
if not "%ASK_PICK_TIME%"=="" set "PICK_TIME=%ASK_PICK_TIME%"

set "ASK_START_TIME="
set /p "ASK_START_TIME=Watermark start time, seconds [%START_TIME%]: "
if not "%ASK_START_TIME%"=="" set "START_TIME=%ASK_START_TIME%"

set "ASK_END_TIME="
set /p "ASK_END_TIME=Watermark end time, seconds [%END_TIME%]: "
if not "%ASK_END_TIME%"=="" set "END_TIME=%ASK_END_TIME%"

set "ASK_REGION_NAME="
set /p "ASK_REGION_NAME=Region name [%REGION_NAME%]: "
if not "%ASK_REGION_NAME%"=="" set "REGION_NAME=%ASK_REGION_NAME%"

if "%PICK_TIME%"=="" set "PICK_TIME=1"
if "%START_TIME%"=="" set "START_TIME=0"
if "%END_TIME%"=="" set "END_TIME=4"
if "%REGION_NAME%"=="" set "REGION_NAME=watermark"

:RUN_PICKER
echo.
python pick_region.py "%VIDEO%" --time %PICK_TIME% --start %START_TIME% --end %END_TIME% --name "%REGION_NAME%"

if errorlevel 1 (
    echo.
    echo Pick region failed.
    if not "%NO_PAUSE%"=="1" pause > nul
    exit /b 1
)

echo.
echo Pick region finished.
if not "%NO_PAUSE%"=="1" pause > nul
