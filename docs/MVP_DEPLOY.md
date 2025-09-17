# IndexTTS2 MVP Deployment Guide (macOS/Linux/Windows)

This guide walks through a minimal setup that you can reproduce on any developer laptop (tested on macOS M1) and reuse on Linux/Windows. It installs the runtime, fetches only the files you need from Hugging Face using the new universal downloader, and shows how to launch IndexTTS2 once the full checkpoints are in place.

## 1. Prerequisites

- Git and Git LFS (`brew install git git-lfs` on macOS, `sudo apt install git git-lfs` on Linux, Git for Windows installer on Windows). Run `git lfs install` once per machine.
- Python 3.10+ (the project pins 3.10.18 when using `uv`). No manual venv activation is required; `uv` takes care of it.
- Optional: FFmpeg if you plan to resample/customise audio (`brew install ffmpeg`, `sudo apt install ffmpeg`, Windows builds from gyan.dev are fine).

## 2. Clone and bootstrap the project

```bash
cd /path/to/workspace
git clone https://github.com/index-tts/index-tts.git
cd index-tts
uv sync --extra webui          # install dependencies into .venv
```

`uv sync` may take a few minutes on the first run because it pulls PyTorch, Gradio, and model tooling. Subsequent invocations are incremental.

## 3. Download models with the universal script

We created `huggingface_pipeline/hf_universal_downloader.py` to combine the best parts of the previous shell and Python pipelines in a single cross-platform tool.

Key capabilities:
- macOS/Linux/Windows compatible – no `sudo` or `/proc` tricks required.
- Single or multiple repositories (`--repo-id` or `--jobs-file`).
- Built-in disk-space check, logging to both console and file (`logs/`).
- Hugging Face mirror friendly (`--endpoint https://hf-mirror.com`).
- Optional pattern filters and compressed packaging (`--package`).

### 3.1 Quick sanity download (config only)

```bash
.venv/bin/python huggingface_pipeline/hf_universal_downloader.py \
  --repo-id IndexTeam/IndexTTS-2 \
  --output-dir checkpoints \
  --include config.yaml README.md
```

This fetches only the lightweight files so you can verify connectivity. The script stores partial outputs under `checkpoints/IndexTeam__IndexTTS-2` and writes logs to `logs/`.

### 3.2 Full model download

Remove the `--include` filter to grab the entire repository (~20+ GB). Add your token if the repo is gated:

```bash
export HF_TOKEN="<your_pat>"          # or set in PowerShell: $env:HF_TOKEN="..."
.venv/bin/python huggingface_pipeline/hf_universal_downloader.py \
  --repo-id IndexTeam/IndexTTS-2 \
  --output-dir checkpoints \
  --max-workers 8
```

If you prefer a mirror:

```bash
.venv/bin/python huggingface_pipeline/hf_universal_downloader.py \
  --repo-id IndexTeam/IndexTTS-2 \
  --endpoint https://hf-mirror.com \
  --output-dir checkpoints
```

Packaging the result into a transferable archive is one flag away:

```bash
.venv/bin/python huggingface_pipeline/hf_universal_downloader.py \
  --repo-id IndexTeam/IndexTTS-2 \
  --output-dir checkpoints \
  --package \
  --package-format zst            # falls back to tar.gz if zstandard is missing
```

To download multiple repositories in one shot, create a text file (one repo per line, optional `local_dir`/`revision` via JSON/YAML/TOML) and pass `--jobs-file repos.txt`.

## 4. Verify PyTorch backend (optional but recommended)

```bash
uv run python - <<'PY'
import torch
print("Torch", torch.__version__, "MPS available:", torch.backends.mps.is_available())
PY
```

For NVIDIA GPUs on Linux/Windows, substitute `torch.cuda.is_available()`.

## 5. Run IndexTTS2

### 5.1 WebUI demo

```bash
uv run webui.py
```
Open http://127.0.0.1:7860 and point the checkpoints path to the folder created in step 3.

Useful flags:
- `uv run webui.py -h` – list all options (FP16, DeepSpeed, compiled CUDA kernels, etc.).
- `uv run webui.py --fp16` – enable half precision where supported.

### 5.2 Programmatic usage (Python API)

```bash
PYTHONPATH="$PYTHONPATH:." uv run python - <<'PY'
from indextts.infer_v2 import IndexTTS2

tts = IndexTTS2(
    cfg_path="checkpoints/config.yaml",
    model_dir="checkpoints",
    use_fp16=False,
    use_cuda_kernel=False,
    use_deepspeed=False,
    device="mps"  # change to "cuda:0" or "cpu" as needed
)

text = "大家好，这是在 macOS M1 上运行的 IndexTTS2 MVP。"
tts.infer(
    spk_audio_prompt="examples/voice_01.wav",
    text=text,
    output_path="gen.wav",
    verbose=True
)
PY
```

Adjust the prompt paths, `emo_*` parameters, or use `IndexTTS` for legacy v1 inference.

## 6. Housekeeping tips

- Logs: every downloader run stores a timestamped log under `logs/` (or your custom `--log-dir`).
- Cache: Hugging Face caches live in `~/.cache/huggingface`. You can relocate via `HF_HOME` or use the downloader’s `--cache-dir`.
- Disk space: the downloader aborts if free space dips below `--min-free-gb` (default 2 GB).
- Offline transfers: combine `--package` with rsync/SSH to move archives onto air-gapped GPU servers, then reuse the existing `hf_unpack_and_deploy.sh` if you need automatic vLLM deployments.

---

With these steps you get a repeatable MVP path: install once with `uv`, fetch models quickly with the universal downloader, and launch either the WebUI or Python API on macOS, Linux, or Windows.
