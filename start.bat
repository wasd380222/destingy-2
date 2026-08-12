@echo off
chcp 65001 >nul
title Destiny 2 Ogre Kick

cd /d "%~dp0"

echo.
echo   ============================================
echo      D2 Ogre Kick
echo      F8 = Start/Stop   F9 = Exit
echo   ============================================
echo.

"C:\Users\Administrator\.workbuddy\binaries\python\envs\d2-ogre-kick\Scripts\python" src\run.py

pause
