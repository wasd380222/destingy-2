@echo off
chcp 65001 >nul

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo.
    echo   [*] 没找到 .venv, 正在创建虚拟环境...
    echo.

    set PYEXE=
    where python >nul 2>&1 && set PYEXE=python
    if "%PYEXE%"=="" where py >nul 2>&1 && set PYEXE=py -3
    if "%PYEXE%"=="" (
        echo   [X] 没找到 Python，请先安装 Python 3.11 ~ 3.13
        pause
        exit /b 1
    )

    %PYEXE% -m venv .venv
    if errorlevel 1 (
        echo   [X] 创建 venv 失败
        pause
        exit /b 1
    )
)

echo   [*] 正在安装依赖...
.venv\Scripts\python.exe -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
if errorlevel 1 (
    echo   [X] 安装失败，检查网络后重试
    pause
    exit /b 1
)

echo.
echo   [√] 安装完成, 现在可以双击 start.bat 运行
echo.
pause
