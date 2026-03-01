#!/usr/bin/env bash
set -euo pipefail

# 获取脚本所在目录的绝对路径
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# 激活虚拟环境
# 如果你的虚拟环境不在脚本同级目录下的 .venv，请修改此处
if [ -f "$SCRIPT_DIR/.venv/bin/activate" ]; then
    . "$SCRIPT_DIR/.venv/bin/activate"
else
    echo "Warning: Virtual environment not found at $SCRIPT_DIR/.venv"
    echo "Please create a virtual environment and install dependencies."
fi

export DEEPSEEK_API_KEY="your_deepseek_api_key_here"
export DEEPSEEK_BASE_URL="https://api.deepseek.com"
export DEEPSEEK_MODEL="deepseek-chat"

# 设置 PYTHONPATH 并运行
# Usage: ./start.sh [working_directory]
PYTHONPATH="$SCRIPT_DIR/src" python -m code_deer "${1:-.}"
