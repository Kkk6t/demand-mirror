@echo off
chcp 65001 >nul
title 先别做
cd /d "%~dp0"

echo.
echo   先别做：动手写代码之前，先花一周搞清楚到底有没有人要
echo.

rem 1. 检查 Python
python --version >nul 2>nul
if errorlevel 1 (
    echo [!] 没有找到 Python。
    echo     马上帮你打开下载页面。安装时一定要勾选最下面的 "Add python.exe to PATH"，
    echo     装好后重新双击这个文件。
    start "" https://www.python.org/downloads/
    pause
    exit /b 1
)

rem 2. 第一次运行：建一个独立环境，不影响电脑上别的 Python 程序
if not exist ".venv\Scripts\python.exe" (
    echo [1/3] 第一次运行，正在准备环境，大约 1 到 3 分钟……
    python -m venv .venv
    if errorlevel 1 (
        echo [!] 创建环境失败。请确认 Python 版本是 3.10 或更高。
        pause
        exit /b 1
    )
)

rem 3. 依赖有变化时才重新安装（先用清华镜像，国内更快；失败再用官方源）
fc /b requirements.txt ".venv\installed.txt" >nul 2>nul
if errorlevel 1 (
    echo [2/3] 正在安装需要的组件……
    ".venv\Scripts\python.exe" -m pip install -q --disable-pip-version-check -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
    if errorlevel 1 (
        ".venv\Scripts\python.exe" -m pip install -q --disable-pip-version-check -r requirements.txt
        if errorlevel 1 (
            echo [!] 安装失败，检查一下网络后重新双击这个文件。
            pause
            exit /b 1
        )
    )
    copy /y requirements.txt ".venv\installed.txt" >nul
)

rem 4. 启动
echo [3/3] 正在启动，浏览器会自动打开。用完关掉这个黑色窗口就行。
echo       如果浏览器没打开，手动访问 http://localhost:8501
echo.
".venv\Scripts\python.exe" -m streamlit run app.py
pause
