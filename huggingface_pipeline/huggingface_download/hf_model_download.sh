#!/bin/bash
# hf_model_download.sh - 企业级 Hugging Face 模型批量下载器

set -euo pipefail

# ========= 配置区 =========
MODEL_LIST=(
  #"deepseek-ai/DeepSeek-R1-Distill-Qwen-14B"
  #"Qwen/Qwen3-14B"
  #"moka-ai/m3e-base"
  "BAAI/bge-m3"
)

LOCAL_BASE_DIR="$HOME/models"
PYTHON_ENV_TYPE="conda"  # 可选：conda / venv
CONDA_PATH="/home/ubuntu/miniconda3"
CONDA_ENV_NAME="vllm_env"
MAX_WORKERS=32
LOG_DIR="$HOME/logs"
LOG_FILE="$LOG_DIR/download_hf_model.log"

# ========= 环境准备 =========
mkdir -p "$LOG_DIR"
echo "📦 日志输出: $LOG_FILE"

if [ "$PYTHON_ENV_TYPE" = "conda" ]; then
  if [ -f "$CONDA_PATH/bin/conda" ]; then
    echo "✅ 激活 Conda 环境: $CONDA_ENV_NAME"
    source "$CONDA_PATH/etc/profile.d/conda.sh"
    conda activate "$CONDA_ENV_NAME"
  else
    echo "❌ Conda 未找到: $CONDA_PATH"
    exit 1
  fi
elif [ "$PYTHON_ENV_TYPE" = "venv" ]; then
  if [ -f "$VENV_ACTIVATE_PATH" ]; then
    echo "✅ 激活虚拟环境: $VENV_ACTIVATE_PATH"
    source "$VENV_ACTIVATE_PATH"
  else
    echo "❌ 虚拟环境未找到: $VENV_ACTIVATE_PATH"
    exit 1
  fi
else
  echo "❌ 无效的环境类型: $PYTHON_ENV_TYPE"
  exit 1
fi

echo "🐍 Python 版本: $(python --version)"

# ========= 缓存清理（下载前） =========
echo "🧹 清理 Hugging Face 缓存（下载前）..."
rm -rf ~/.cache/huggingface/*

echo "🧹 清理 Linux 页缓存（下载前）..."
sync; echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null

echo "💾 当前磁盘空间（下载前）:"
df -h ~

# ========= 下载模型 =========
for REPO_ID in "${MODEL_LIST[@]}"; do
  MODEL_NAME=$(basename "$REPO_ID")
  LOCAL_DIR="$LOCAL_BASE_DIR/$MODEL_NAME"

  echo "🚀 开始下载模型: $REPO_ID → $LOCAL_DIR" | tee -a "$LOG_FILE"
  python3 hf_download_manager.py \
    --repo_id "$REPO_ID" \
    --local_dir "$LOCAL_DIR" \
    --max_workers "$MAX_WORKERS" | tee -a "$LOG_FILE"
done

# ========= 缓存清理（下载后） =========
echo "🧹 清理 Hugging Face 缓存（下载后）..."
rm -rf ~/.cache/huggingface/*

echo "🧹 清理 Linux 页缓存（下载后）..."
sync; echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null

echo "💾 当前磁盘空间（下载后）:"
df -h ~

# ========= 环境退出 =========
if [ "$PYTHON_ENV_TYPE" = "conda" ]; then
  conda deactivate
else
  deactivate || true
fi

echo "✅ 🎉 所有模型下载任务已完成！详细日志请见: $LOG_FILE"

