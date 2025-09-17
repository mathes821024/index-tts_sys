#!/bin/bash
# compress_model.sh - 对 Hugging Face 模型进行高压缩率打包（.tar.zst）

set -euo pipefail

# ========= 参数校验 =========
if [ $# -ne 1 ]; then
  echo "❌ 用法错误: $0 <模型目录路径>"
  exit 1
fi

MODEL_PATH="$(realpath "$1")"
MODEL_NAME="$(basename "$MODEL_PATH")"
PARENT_DIR="$(dirname "$MODEL_PATH")"
TRANSFER_DIR="$(realpath "$(dirname "$0")/../transfer_package")"
ZSTD_LEVEL=19

mkdir -p "$TRANSFER_DIR"

ARCHIVE_PATH="${TRANSFER_DIR}/${MODEL_NAME}.tar.zst"
TMP_ARCHIVE_PATH="${ARCHIVE_PATH}.tmp"

echo "📦 开始压缩模型: $MODEL_NAME"
echo "📁 模型路径: $MODEL_PATH"
echo "📤 输出路径: $ARCHIVE_PATH"
echo "🧮 模型目录大小:"
du -sh "$MODEL_PATH"

# ========= 执行压缩 =========
echo "🚀 执行 tar.zst 压缩（zstd -${ZSTD_LEVEL}）..."
if tar --use-compress-program="zstd -${ZSTD_LEVEL} -T0" -cf "$TMP_ARCHIVE_PATH" -C "$PARENT_DIR" "$MODEL_NAME"; then
    mv "$TMP_ARCHIVE_PATH" "$ARCHIVE_PATH"
    echo "✅ 压缩完成！文件大小：$(du -sh "$ARCHIVE_PATH" | awk '{print $1}')"
else
    echo "❌ 压缩失败，清理临时文件"
    rm -f "$TMP_ARCHIVE_PATH"
    exit 1
fi

