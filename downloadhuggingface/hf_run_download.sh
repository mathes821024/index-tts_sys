#!/bin/bash
# hf_run_download.sh - 启动 Hugging Face 下载任务，并在下载前后清理缓存

LOG_DIR="$HOME/logs"
mkdir -p "$LOG_DIR"

LOG_FILE="$LOG_DIR/download_hf_model.log"

echo "🧹 清理 Hugging Face 旧缓存（下载前）..."
rm -rf ~/.cache/huggingface/*

echo "🧹 清理 Linux 系统缓存（下载前）..."
sync; echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null

echo "💾 当前磁盘空间（下载前）:"
df -h /home

echo "🚀 启动 Hugging Face 模型下载任务..."
nohup bash hf_model_download.sh > "$LOG_FILE" 2>&1 &

echo "✅ 下载任务已启动，日志保存在: $LOG_FILE"

