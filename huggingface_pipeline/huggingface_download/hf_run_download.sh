#!/bin/bash
# hf_run_download.sh - 后台异步下载 Hugging Face 模型（含前置清理与日志）

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="$HOME/logs"
LOG_FILE="${LOG_DIR}/download_hf_model.log"

# ========= 环境准备 =========
mkdir -p "$LOG_DIR"
echo "📁 下载日志将保存至: $LOG_FILE"

# ========= 缓存清理（下载前） =========
echo "🧹 清理 Hugging Face 缓存..."
rm -rf ~/.cache/huggingface/*

echo "🧹 清理 Linux 页缓存..."
sync; echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null

echo "💾 当前磁盘空间状态:"
df -h ~

# ========= 启动任务 =========
echo "🚀 启动模型下载任务 (后台运行)..."
nohup bash "${SCRIPT_DIR}/hf_model_download.sh" >> "$LOG_FILE" 2>&1 &

PID=$!
echo "📌 后台下载进程 PID: $PID"
echo "📖 可用以下命令实时查看下载日志："
echo ""
echo "  tail -f $LOG_FILE"
echo ""
echo "✅ 下载任务已启动，稍后请检查日志与模型目录增长状态。"

