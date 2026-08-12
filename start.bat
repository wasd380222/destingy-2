@echo off
chcp 65001 >nul

cd /d "%~dp0"

set PYEXE=
if exist ".venv\Scripts\python.exe" set PYEXE=.venv\Scripts\python.exe
if "%PYEXE%"=="" (
    where python >nul 2>&1 && set PYEXE=python
)
if "%PYEXE%"=="" (
    where py >nul 2>&1 && set PYEXE=py -3
)
if "%PYEXE%"=="" (
    echo.
    echo   [X] 没找到 Python，请先安装 Python 3.11 ~ 3.13
    echo       https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

if not exist "logs" mkdir logs

echo.
echo   D2 Ogre Kick  -  F8=Start  F10=Stop  Ctrl+C=Exit
echo.

start "" /B %PYEXE% src\overlay_main.py
%PYEXE% src\run.py

pause
