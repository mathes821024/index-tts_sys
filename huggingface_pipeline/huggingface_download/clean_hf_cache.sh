#!/bin/bash
# clean_hf_cache.sh - 清理 Hugging Face 本地缓存目录（全量/增量）

set -euo pipefail

# 默认路径（可传参覆盖）
CACHE_DIR="${1:-$HOME/.cache/huggingface}"

echo "🧹 正在清理 Hugging Face 缓存目录: $CACHE_DIR"

if [ ! -d "$CACHE_DIR" ]; then
    echo "📁 缓存目录不存在，跳过清理"
    exit 0
fi

echo "🔍 删除 .lock 文件..."
find "$CACHE_DIR" -type f -name "*.lock" -delete

echo "🔍 删除 .json / .tmp / .incomplete 文件..."
find "$CACHE_DIR" -type f \( -name "*.json" -o -name "*.tmp" \) -delete
find "$CACHE_DIR" -type d -name "*.incomplete" -exec rm -rf {} +

echo "📦 当前缓存目录占用："
du -sh "$CACHE_DIR"

echo "✅ Hugging Face 缓存清理完成"

