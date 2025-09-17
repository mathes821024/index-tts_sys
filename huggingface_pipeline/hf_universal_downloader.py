#!/usr/bin/env python3
"""Cross-platform Hugging Face repository downloader with optional packaging.

This script combines the convenience of the existing shell pipeline with the
robust logging and resume-friendly workflow from the Python manager.

Features:
- macOS / Linux / Windows compatible (no POSIX-only commands).
- Single or multi-repo download via CLI flags or a plain-text job file.
- Resume support, optional force refresh, configurable concurrency.
- Optional include / exclude glob patterns (huggingface_hub allow_patterns).
- Disk-space checks and dual console/log-file output.
- Optional packaging step (tar.zst if zstandard exists, otherwise tar.gz).

Example:
    python hf_universal_downloader.py \
        --repo-id IndexTeam/IndexTTS-2 \
        --output-dir checkpoints \
        --max-workers 8
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import platform
import shutil
import sys
import textwrap
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional

from huggingface_hub import snapshot_download

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover
    yaml = None

LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
DEFAULT_LOG_DIR = Path.home() / "logs"
DEFAULT_BASE_OUTPUT = Path.cwd() / "hf_models"


@dataclass
class DownloadJob:
    repo_id: str
    local_dir: Path
    revision: Optional[str] = None
    includes: Optional[List[str]] = None
    excludes: Optional[List[str]] = None


def human_bytes(num: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if num < 1024 or unit == "TB":
            return f"{num:.2f} {unit}"
        num /= 1024
    return f"{num:.2f} TB"


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def setup_logging(log_dir: Path, log_level: str) -> Path:
    """Configure logging with a best-effort fallback inside the workspace."""

    def build_handler(target_dir: Path) -> tuple[Path, logging.FileHandler]:
        ensure_dir(target_dir)
        candidate = target_dir / f"hf_download_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        handler = logging.FileHandler(candidate, encoding="utf-8")
        return candidate, handler

    try:
        log_path, file_handler = build_handler(log_dir)
    except OSError:
        fallback_dir = Path.cwd() / "logs"
        log_path, file_handler = build_handler(fallback_dir)

    stream_handler = logging.StreamHandler(sys.stdout)
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format=LOG_FORMAT,
        handlers=[file_handler, stream_handler],
    )
    return log_path


def disk_free_gb(path: Path) -> float:
    total, used, free = shutil.disk_usage(path)
    return free / (1024 ** 3)


def sanitize_repo_path(repo_id: str) -> str:
    return repo_id.replace("/", "__").replace(":", "_")


def load_jobs_from_file(file_path: Path, base_output: Path) -> List[DownloadJob]:
    if not file_path.exists():
        raise FileNotFoundError(f"Job file not found: {file_path}")

    if file_path.suffix in {".json", ".jsonl"}:
        data = json.loads(file_path.read_text(encoding="utf-8"))
    elif file_path.suffix in {".toml"} and tomllib:
        data = tomllib.loads(file_path.read_text(encoding="utf-8"))
    elif file_path.suffix in {".yml", ".yaml"} and yaml:
        data = yaml.safe_load(file_path.read_text(encoding="utf-8"))
    else:
        repos = [line.strip() for line in file_path.read_text(encoding="utf-8").splitlines() if line.strip() and not line.strip().startswith("#")]
        data = [{"repo_id": repo} for repo in repos]

    jobs: List[DownloadJob] = []
    if isinstance(data, dict):
        data = data.get("jobs") or data.get("models") or []
    for entry in data:
        if isinstance(entry, str):
            entry = {"repo_id": entry}
        repo_id = entry["repo_id"]
        local_dir = Path(entry.get("local_dir") or base_output / sanitize_repo_path(repo_id))
        job = DownloadJob(
            repo_id=repo_id,
            revision=entry.get("revision"),
            local_dir=local_dir,
            includes=entry.get("include") or entry.get("includes"),
            excludes=entry.get("exclude") or entry.get("excludes"),
        )
        jobs.append(job)
    return jobs


def build_jobs(args: argparse.Namespace) -> List[DownloadJob]:
    jobs: List[DownloadJob] = []
    base_output = Path(args.output_dir or DEFAULT_BASE_OUTPUT)
    ensure_dir(base_output)

    if args.jobs_file:
        jobs.extend(load_jobs_from_file(Path(args.jobs_file), base_output))

    if args.repo_id:
        local_dir = Path(args.local_dir) if args.local_dir else base_output / sanitize_repo_path(args.repo_id)
        jobs.append(
            DownloadJob(
                repo_id=args.repo_id,
                revision=args.revision,
                local_dir=local_dir,
                includes=args.include if args.include else None,
                excludes=args.exclude if args.exclude else None,
            )
        )

    if not jobs:
        raise ValueError("No download jobs specified. Provide --repo-id or --jobs-file.")

    return jobs


def resolve_token(args: argparse.Namespace) -> Optional[str]:
    if args.token:
        return args.token
    return os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACEHUB_API_TOKEN")


def maybe_set_endpoint(endpoint: Optional[str]) -> None:
    if endpoint:
        os.environ["HF_ENDPOINT"] = endpoint
        logging.info("Using custom HF endpoint: %s", endpoint)


def run_download(job: DownloadJob, args: argparse.Namespace, token: Optional[str]) -> Path:
    ensure_dir(job.local_dir)
    logging.info("Starting download: repo_id=%s", job.repo_id)
    logging.info("Target directory: %s", job.local_dir)
    if job.revision:
        logging.info("Revision: %s", job.revision)
    logging.info("Free space (before): %.2f GB", disk_free_gb(job.local_dir))

    download_kwargs = dict(
        repo_id=job.repo_id,
        cache_dir=args.cache_dir,
        local_dir=str(job.local_dir),
        force_download=args.force_download,
        max_workers=args.max_workers,
        token=token,
        allow_patterns=job.includes,
        ignore_patterns=job.excludes,
    )

    if job.revision:
        download_kwargs["revision"] = job.revision
    if args.endpoint:
        download_kwargs["endpoint"] = args.endpoint

    snapshot_download(**download_kwargs)

    logging.info("Download complete: %s", job.repo_id)
    logging.info("Free space (after): %.2f GB", disk_free_gb(job.local_dir))
    return job.local_dir


def package_directory(src_dir: Path, package_dir: Path, preferred: str = "zst") -> Path:
    ensure_dir(package_dir)
    archive_base = package_dir / src_dir.name

    if preferred == "zst":
        try:
            import tarfile
            import zstandard as zstd
        except ModuleNotFoundError:
            preferred = "gz"
        else:
            tmp_tar = archive_base.with_suffix(".tar")
            with tarfile.open(tmp_tar, "w") as tar:
                tar.add(src_dir, arcname=src_dir.name)
            out_path = archive_base.with_suffix(".tar.zst")
            cctx = zstd.ZstdCompressor(level=10)
            with tmp_tar.open("rb") as inp, out_path.open("wb") as out:
                out.write(cctx.compress(inp.read()))
            tmp_tar.unlink()
            return out_path

    import tarfile

    out_path = archive_base.with_suffix(".tar.gz")
    with tarfile.open(out_path, "w:gz") as tar:
        tar.add(src_dir, arcname=src_dir.name)
    return out_path


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Universal Hugging Face model downloader",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("--repo-id", help="Hugging Face repo id, e.g. IndexTeam/IndexTTS-2")
    parser.add_argument("--revision", help="Specific git revision/tag to download")
    parser.add_argument("--jobs-file", help="Path to file describing multiple jobs (txt/json/yaml/toml)")
    parser.add_argument("--local-dir", help="Explicit destination directory for a single job")
    parser.add_argument("--output-dir", help="Base directory used when local-dir not provided")
    parser.add_argument("--cache-dir", help="Optional cache directory to reuse across runs")
    parser.add_argument("--max-workers", type=int, default=min(8, os.cpu_count() or 4), help="Concurrent download workers")
    parser.add_argument("--include", nargs="*", help="Allow patterns (glob) passed to snapshot_download")
    parser.add_argument("--exclude", nargs="*", help="Ignore patterns (glob) passed to snapshot_download")
    parser.add_argument("--force-download", action="store_true", help="Force re-download even if files exist")
    parser.add_argument("--token", help="Explicit Hugging Face token (otherwise env vars are used)")
    parser.add_argument("--endpoint", help="Custom HF endpoint or mirror URL")
    parser.add_argument("--min-free-gb", type=float, default=2.0, help="Abort if free disk space (GB) is below this value")
    parser.add_argument("--log-level", default="INFO", help="Logging level (INFO, DEBUG, ...)")
    parser.add_argument("--log-dir", default=str(DEFAULT_LOG_DIR), help="Directory to store log files")
    parser.add_argument("--package", action="store_true", help="Create a compressed archive after download")
    parser.add_argument("--package-dir", help="Directory to store archives (defaults to output-dir)")
    parser.add_argument("--package-format", choices=["zst", "gz"], default="zst", help="Preferred archive format")
    parser.add_argument("--dry-run", action="store_true", help="Validate options without downloading")

    args = parser.parse_args(list(argv) if argv is not None else None)
    return args


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = parse_args(argv)

    log_path = setup_logging(Path(args.log_dir), args.log_level)
    logging.info("Log file: %s", log_path)
    logging.info("Platform: %s", platform.platform())
    logging.info("Python: %s", sys.version.split()[0])

    token = resolve_token(args)
    if token:
        logging.info("Auth token detected via args/env")
    else:
        logging.warning("No HF token provided; public models only")

    jobs = build_jobs(args)
    logging.info("Planned jobs: %s", ", ".join(job.repo_id for job in jobs))

    root = Path(args.output_dir or DEFAULT_BASE_OUTPUT)
    ensure_dir(root)
    free_gb = disk_free_gb(root)
    logging.info("Initial free space: %.2f GB", free_gb)
    if free_gb < args.min_free_gb:
        logging.error("Insufficient disk space (%.2f GB < required %.2f GB)", free_gb, args.min_free_gb)
        return 2

    if args.dry_run:
        logging.info("Dry run complete. Exiting without download.")
        return 0

    maybe_set_endpoint(args.endpoint)

    results: List[str] = []
    for job in jobs:
        try:
            local_path = run_download(job, args, token)
            if args.package:
                archive_dir = Path(args.package_dir) if args.package_dir else root
                archive_path = package_directory(local_path, archive_dir, preferred=args.package_format)
                logging.info("Archive created: %s (%s)", archive_path, human_bytes(archive_path.stat().st_size))
            results.append(str(local_path))
        except Exception:
            logging.exception("Download failed for %s", job.repo_id)

    if not results:
        logging.error("All jobs failed")
        return 1

    summary = textwrap.dedent(
        """
        === Download Summary ===
        Completed: {completed}
        Output directories:
        {paths}
        """
    ).strip().format(
        completed=len(results),
        paths="\n".join(f"  - {path}" for path in results),
    )
    logging.info(summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
