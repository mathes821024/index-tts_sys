#!/usr/bin/env python3
import os
import shutil
import logging
import argparse
from huggingface_hub import snapshot_download

# 配置日志格式
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

def clear_huggingface_cache():
    """清理 Hugging Face 下载缓存"""
    cache_dir = os.path.expanduser("~/.cache/huggingface")
    if os.path.exists(cache_dir):
        logging.info("🧹 清理 Hugging Face 旧缓存...")
        shutil.rmtree(cache_dir)
        os.makedirs(cache_dir, exist_ok=True)
        logging.info("✅ 缓存清理完成")

def check_disk_space(local_dir, min_required_gb=50):
    """检查磁盘空间"""
    total, used, free = shutil.disk_usage("/")
    free_gb = free // (2**30)
    logging.info(f"可用磁盘空间: {free_gb} GB")
    
    if free_gb < min_required_gb:
        logging.error(f"磁盘空间不足，仅剩 {free_gb}GB，请清理空间")
        exit(1)

    os.makedirs(local_dir, exist_ok=True)

def download_model(repo_id, local_dir, max_workers, force_download):
    """主下载流程"""
    try:
        logging.info(f"🚀 开始下载 {repo_id} 到 {local_dir} (max_workers={max_workers}, force_download={force_download})")

        # 1️⃣ 清理 Hugging Face 缓存（下载前）
        clear_huggingface_cache()

        # 2️⃣ 检查磁盘空间
        check_disk_space(local_dir)

        # 3️⃣ 下载模型文件
        snapshot_download(
            repo_id=repo_id,
            local_dir=local_dir,
            resume_download=True,
            force_download=force_download,
            max_workers=max_workers
        )

        logging.info(f"✅ 🎉 模型 {repo_id} 下载完成，文件存储在 {local_dir}")

        # 4️⃣ 清理 Hugging Face 缓存（下载后）
        clear_huggingface_cache()

    except Exception as e:
        logging.error(f"❌ 下载失败: {e}", exc_info=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hugging Face 模型下载管理器")
    parser.add_argument("--repo_id", type=str, required=True, help="Hugging Face 模型仓库 ID")
    parser.add_argument("--local_dir", type=str, required=True, help="本地存储目录")
    parser.add_argument("--max_workers", type=int, default=16, help="并行下载线程数")
    parser.add_argument("--force_download", action="store_true", help="是否强制重新下载")

    args = parser.parse_args()

    download_model(
        repo_id=args.repo_id,
        local_dir=args.local_dir,
        max_workers=args.max_workers,
        force_download=args.force_download
    )

