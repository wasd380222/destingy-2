@echo off
chcp 65001 >nul
title D2 Ogre Kick

cd /d "%~dp0"

echo.
echo   ============================================
echo      D2 Ogre Kick
echo      F8 = Start   F10 = Stop   Ctrl+C = Exit
echo   ============================================
echo.

:: 先启动悬浮框独立进程 (后台, 不阻塞)
start "" /B "C:\Users\Administrator\.workbuddy\binaries\python\envs\d2-ogre-kick\Scripts\python" src\overlay_main.py

:: 再启动主脚本 (前台)
"C:\Users\Administrator\.workbuddy\binaries\python\envs\d2-ogre-kick\Scripts\python" src\run.py

:: run.py 退出时已通过 overlay.stop() 通知悬浮框关闭
:: 若 run.py 异常崩溃, 悬浮框会在 15 秒内心跳超时后自动退出

pause
