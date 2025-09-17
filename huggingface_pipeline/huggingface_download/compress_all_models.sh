#!/bin/bash
# compress_all_models.sh - 批量压缩 Hugging Face 模型为 .tar.zst 格式

set -euo pipefail

MODELS_DIR="$HOME/models"
TRANSFER_DIR="$(realpath "$(dirname "$0")/../transfer_package")"
COMPRESS_SCRIPT="$(realpath "$(dirname "$0")/compress_model.sh")"

mkdir -p "$TRANSFER_DIR"

echo "📦 模型目录: $MODELS_DIR"
echo "🎯 输出目录: $TRANSFER_DIR"
echo "🔄 准备批量压缩所有模型..."

total=0
skipped=0
succeeded=0
failed=0

for model_dir in "$MODELS_DIR"/*; do
  [[ -d "$model_dir" ]] || continue

  model_name="$(basename "$model_dir")"
  output_file="${TRANSFER_DIR}/${model_name}.tar.zst"

  ((total++))
  echo "---------------------------------------------"
  echo "🔍 处理模型: $model_name"

  if [ -f "$output_file" ]; then
    echo "⚠️ 已存在压缩包，跳过: $output_file"
    ((skipped++))
    continue
  fi

  if bash "$COMPRESS_SCRIPT" "$model_dir"; then
    ((succeeded++))
  else
    echo "❌ 压缩失败: $model_name"
    ((failed++))
  fi
done

echo "============================================="
echo "📊 压缩汇总："
echo "✅ 成功: $succeeded"
echo "⚠️ 跳过: $skipped"
echo "❌ 失败: $failed"
echo "📦 总计: $total 模型"

