@echo off
title D2 踢Boss — 操作录制

cd /d "%~dp0"

echo 启动录制工具...
"C:/Users/Administrator/.workbuddy/binaries/python/envs/d2-ogre-kick/Scripts/python" src/record.py
pause
