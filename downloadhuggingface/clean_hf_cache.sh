#!/bin/bash
# clean_hf_cache.sh - 清理 Hugging Face 缓存并检查磁盘空间

echo "💾 磁盘使用情况（清理前）:"
sudo du -ah /home | sort -rh | head -20
df -h

echo "🧹 强制删除 Hugging Face 缓存..."
sudo rm -rf ~/.cache/huggingface/

echo "🧹 清理 Linux 系统缓存..."
sync; echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null

echo "💾 磁盘使用情况（清理后）:"
sudo du -ah /home | sort -rh | head -20
df -h

echo "✅ 清理完成！"

