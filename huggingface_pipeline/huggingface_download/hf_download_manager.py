#!/usr/bin/env python3
# hf_download_manager.py - Hugging Face 模型下载主控脚本
# ✅ 支持断点续传、多线程、高可观測性日志记录、下载目录与缓存路径指定

import os
import shutil
import logging
import argparse
from huggingface_hub import snapshot_download

# ========= 日志配置 =========
def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(os.path.expanduser("~/logs/download_hf_model.log")),
            logging.StreamHandler()
        ]
    )

# ========= Hugging Face 缓存清理 =========
def clear_huggingface_cache():
    cache_dir = os.path.expanduser("~/.cache/huggingface")
    if os.path.exists(cache_dir):
        logging.info("🧹 清理 Hugging Face 旧缓存...")
        shutil.rmtree(cache_dir)
        os.makedirs(cache_dir, exist_ok=True)
        logging.info("✅ 缓存清理完成")

# ========= 磁盘空间检查 =========
def check_disk_space(local_dir, min_required_gb=2):
    total, used, free = shutil.disk_usage("/")
    free_gb = free // (2**30)
    logging.info(f"可用磁盘空间: {free_gb} GB")

    if free_gb < min_required_gb:
        logging.error(f"磁盘空间不足，仅剩 {free_gb}GB，请清理空间")
        exit(1)

    os.makedirs(local_dir, exist_ok=True)

# ========= 模型下载主逻辑 =========
def download_model(repo_id, local_dir, max_workers, force_download):
    try:
        logging.info(f"🚀 开始下载 {repo_id} 至 {local_dir} (max_workers={max_workers}, force_download={force_download})")

        clear_huggingface_cache()
        check_disk_space(local_dir)

        snapshot_download(
            repo_id=repo_id,
            local_dir=local_dir,
            resume_download=True,
            force_download=force_download,
            max_workers=max_workers,
            local_dir_use_symlinks=False,
            token=os.getenv("HF_TOKEN")
        )

        logging.info(f"✅ 🎉 模型 {repo_id} 下载完成，文件存储在 {local_dir}")
        clear_huggingface_cache()

    except Exception as e:
        logging.error(f"❌ 下载失败: {e}", exc_info=True)

# ========= 命令行入口 =========
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hugging Face 模型下载管理器")
    parser.add_argument("--repo_id", required=True, help="Hugging Face 模型仓库 ID")
    parser.add_argument("--local_dir", required=True, help="本地存储目录")
    parser.add_argument("--max_workers", type=int, default=16, help="并行下载线程数")
    parser.add_argument("--force_download", action="store_true", help="是否强制重新下载")

    args = parser.parse_args()

    setup_logging()
    download_model(
        repo_id=args.repo_id,
        local_dir=args.local_dir,
        max_workers=args.max_workers,
        force_download=args.force_download
    )

