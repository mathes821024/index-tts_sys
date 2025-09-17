#!/bin/bash
# hf_model_download.sh - 动态指定 Hugging Face 模型进行下载

CONDA_BASE="/home/ubuntu/miniconda3"
CONDA_ENV="vllm_env"

# Hugging Face 模型仓库
MODEL_LIST=(
    "deepseek-ai/DeepSeek-R1-Distill-Qwen-14B"
    #"deepseek-ai/DeepSeek-32B"
)

LOCAL_DIR_BASE="$HOME/models"
MAX_WORKERS=32

# 确保 Conda 存在
if [ -f "$CONDA_BASE/bin/conda" ]; then
    echo "✅ Conda 发现于: $CONDA_BASE"
    source "$CONDA_BASE/etc/profile.d/conda.sh"
    conda activate "$CONDA_ENV"
else
    echo "❌ Conda 未安装，请检查路径: $CONDA_BASE"
    exit 1
fi

echo "🐍 Python 版本: $(python --version)"
echo "✅ Conda 当前环境: $(conda info --envs | grep '*' | awk '{print $1}')"

# **清理 Hugging Face 旧缓存（下载前）**
echo "🧹 清理 Hugging Face 旧缓存..."
rm -rf ~/.cache/huggingface/*

# **清理 Linux 旧缓存（下载前）**
echo "🧹 清理 Linux 系统缓存..."
sync; echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null

# **检查剩余磁盘空间**
echo "💾 当前磁盘空间（下载前）:"
df -h /home

# **开始循环下载多个 Hugging Face 模型**
for REPO_ID in "${MODEL_LIST[@]}"; do
    LOCAL_DIR="$LOCAL_DIR_BASE/$(basename $REPO_ID)"
    echo "🚀 下载 Hugging Face 模型: $REPO_ID 到 $LOCAL_DIR"
    python hf_download_manager.py --repo_id "$REPO_ID" --local_dir "$LOCAL_DIR" --max_workers "$MAX_WORKERS"
done

# **清理 Hugging Face 旧缓存（下载后）**
echo "🧹 清理 Hugging Face 旧缓存（下载后）..."
rm -rf ~/.cache/huggingface/*

# **清理 Linux 旧缓存（下载后）**
echo "🧹 清理 Linux 系统缓存（下载后）..."
sync; echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null

# **检查剩余磁盘空间**
echo "💾 当前磁盘空间（下载后）:"
df -h /home

# 退出 Conda 环境
conda deactivate
echo "✅ 🎉 所有模型下载完成！"

