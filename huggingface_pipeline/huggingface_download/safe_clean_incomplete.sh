#!/bin/bash
# safe_clean_incomplete.sh - 清理 Hugging Face 下载残留的 .incomplete 临时文件与 lock 文件

set -euo pipefail

CACHE_DIR="${1:-$HOME/.cache/huggingface}"

echo "🔍 清理目标目录: $CACHE_DIR"

if [ ! -d "$CACHE_DIR" ]; then
    echo "❌ 缓存目录不存在: $CACHE_DIR"
    exit 1
fi

echo "🧹 开始清理 .incomplete 临时目录..."
find "$CACHE_DIR" -type d -name "*.incomplete" -exec rm -rf {} +

echo "🧹 清理 .lock 文件..."
find "$CACHE_DIR" -type f -name "*.lock" -delete

echo "✅ 清理完成，当前缓存目录大小:"
du -sh "$CACHE_DIR"

