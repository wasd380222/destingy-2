@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

cd /d "%~dp0"

:: 检测 Python
set PYEXE=
if exist ".venv\Scripts\python.exe" (
    set PYEXE=.venv\Scripts\python.exe
) else (
    where python >nul 2>&1 && set PYEXE=python
)
if "!PYEXE!"=="" (
    where py >nul 2>&1 && set PYEXE=py -3
)
if "!PYEXE!"=="" (
    echo.
    echo   [X] 没找到 Python，请先运行 install.bat 安装
    echo       或安装 Python 3.11 ~ 3.13: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

:: 创建日志目录
if not exist "logs" mkdir logs

:: 清理上一次的残留状态 (避免 overlay 读到旧 exit=true 立即退出)
if exist "logs\overlay_status.json" del /q "logs\overlay_status.json" >nul 2>&1

echo.
echo   D2 Ogre Kick  -  F8=Start  F10=Stop  Ctrl+C=Exit
echo.

:: 后台启动悬浮框, 输出重定向到日志 (崩溃信息可在 logs\overlay.log 查看)
start "" /B !PYEXE! src\overlay_main.py > logs\overlay.log 2>&1

:: 前台启动主脚本
!PYEXE! src\run.py

:: run.py 退出后, 等 overlay 自动关闭 (心跳超时 15s)
:: 如果 overlay 卡住, 不会阻塞 — start /B 进程随父窗口关闭

pause
