#!/usr/bin/env bash
set -euo pipefail

# Replace with your actual virtual environment path
. /path/to/your/.venv/bin/activate

export DEEPSEEK_API_KEY="your_deepseek_api_key_here"
export DEEPSEEK_BASE_URL="https://api.deepseek.com"
export DEEPSEEK_MODEL="deepseek-chat"

# Replace with your actual project src path
PYTHONPATH=/path/to/your/project/src python -m code_deer
