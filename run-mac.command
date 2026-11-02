#!/bin/bash
# 需求照妖镜：macOS / Linux 一键启动。macOS 上可以直接双击 run-mac.command。
cd "$(dirname "$0")"
if ! command -v python3 >/dev/null 2>&1; then
  echo "没有找到 Python 3，请先到 https://www.python.org/downloads/ 安装（3.10 或更高）。"
  exit 1
fi
if [ ! -x .venv/bin/python ]; then
  echo "第一次运行，正在准备环境……"
  python3 -m venv .venv || exit 1
fi
if ! cmp -s requirements.txt .venv/installed.txt; then
  echo "正在安装需要的组件……"
  .venv/bin/python -m pip install -q --disable-pip-version-check -r requirements.txt || exit 1
  cp requirements.txt .venv/installed.txt
fi
echo "正在启动，浏览器会自动打开。如果没打开，访问 http://localhost:8501"
exec .venv/bin/python -m streamlit run app.py
