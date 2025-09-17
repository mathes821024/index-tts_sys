# IndexTTS2 MVP 部署指南（macOS / Linux / Windows）

本指南演示如何在日常开发环境（以 macOS M1 为例）完成最小可运行版本的部署流程，并同样适用于 Linux 与 Windows。我们将依次完成环境初始化、使用全新的通用下载脚本获取模型，以及通过 WebUI 或 Python API 启动 IndexTTS2。

## 1. 前置条件

- Git 与 Git LFS：macOS 可执行 `brew install git git-lfs`，Linux 可执行 `sudo apt install git git-lfs`，Windows 建议使用官方安装包。安装后运行一次 `git lfs install`。
- Python 3.10 及以上版本。使用 `uv` 时会自动拉取并创建 3.10.18 的虚拟环境，无需手动 `source`。
- 可选：若需要音频重采样或处理，提前安装 FFmpeg（macOS: `brew install ffmpeg`，Linux: `sudo apt install ffmpeg`，Windows 可从 gyan.dev 下载）。

## 2. 克隆仓库并安装依赖

```bash
cd /path/to/workspace
git clone https://github.com/index-tts/index-tts.git
cd index-tts
uv sync --extra webui          # 在 .venv 中安装所需依赖
```

首次执行 `uv sync` 会下载 PyTorch、Gradio 等大型依赖，耗时稍长，后续重复执行会快很多。

## 3. 使用通用脚本下载 Hugging Face 模型

我们在 `huggingface_pipeline/hf_universal_downloader.py` 中整合了原有 Shell 与 Python 流程的优点，提供统一、跨平台的模型下载体验。

**亮点：**
- 完整支持 macOS / Linux / Windows，无需 `sudo` 或 `/proc` 等平台特性。
- 支持单仓库（`--repo-id`）与批量任务（`--jobs-file`）。
- 自动检测磁盘空间，日志同时输出到终端与文件（默认 `logs/`）。
- 支持 Hugging Face 镜像：`--endpoint https://hf-mirror.com`。
- 可选下载过滤（`--include` / `--exclude`）与压缩打包（`--package`）。

### 3.1 连通性验证（仅下载配置文件）

```bash
.venv/bin/python huggingface_pipeline/hf_universal_downloader.py \
  --repo-id IndexTeam/IndexTTS-2 \
  --output-dir checkpoints \
  --max-workers 8 \
  --include config.yaml README.md
```

仅获取轻量文件，观察脚本是否运行正常。输出默认存放在 `checkpoints/IndexTeam__IndexTTS-2`，日志位于 `logs/`。

### 3.2 下载完整权重

去掉 `--include` 参数即可下载完整模型（约 20+ GB）。若仓库需要登录凭证，需要先配置 Token：

```bash
export HF_TOKEN="<你的 HuggingFace PAT>"          # PowerShell: $env:HF_TOKEN="..."
## 如果这个仓库是公开的，其实可以直接移除 Token，重新下载即可:

###unset HF_TOKEN

.venv/bin/python huggingface_pipeline/hf_universal_downloader.py \
  --repo-id IndexTeam/IndexTTS-2 \
  --output-dir checkpoints \
  --max-workers 8

  
```

使用镜像的示例：

```bash
.venv/bin/python huggingface_pipeline/hf_universal_downloader.py \
  --repo-id IndexTeam/IndexTTS-2 \
  --endpoint https://hf-mirror.com \
  --output-dir checkpoints
```

若需要把模型打包以便离线传输，可加入 `--package`：

```bash
.venv/bin/python huggingface_pipeline/hf_universal_downloader.py \
  --repo-id IndexTeam/IndexTTS-2 \
  --output-dir checkpoints \
  --package \
  --package-format zst            # 若未安装 zstandard，会自动回退到 tar.gz
```

批量下载可在文本文件中列出多个仓库（也支持 JSON/YAML/TOML 格式指定更多参数），然后使用 `--jobs-file repos.txt`。

## 4. 验证 PyTorch 后端（推荐执行）

```bash
uv run python - <<'PY'
import torch
print("Torch", torch.__version__, "MPS available:", torch.backends.mps.is_available())
PY
```

Linux/Windows 搭配 NVIDIA GPU 时，可改为查看 `torch.cuda.is_available()`。

## 5. 运行 IndexTTS2

### 5.1 WebUI 体验

```bash
uv run webui.py
```

打开浏览器访问 http://127.0.0.1:7860 ，在界面中指定模型目录为步骤 3 下载的位置即可。常用参数：
- `uv run webui.py -h` 查看全部选项（如 FP16、DeepSpeed、自定义 CUDA kernel 等）。
- `uv run webui.py --fp16` 在支持的硬件上启用半精推理。

### 5.2 Python API 调用示例

```bash
PYTHONPATH="$PYTHONPATH:." uv run python - <<'PY'
from indextts.infer_v2 import IndexTTS2

tts = IndexTTS2(
    cfg_path="checkpoints/config.yaml",
    model_dir="checkpoints",
    use_fp16=False,
    use_cuda_kernel=False,
    use_deepspeed=False,
    device="mps"  # 可按需改为 "cuda:0" 或 "cpu"
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

可根据业务需求设置情感音频、`emo_*` 参数，或切换为 `IndexTTS` 使用 V1 模型。

## 6. 日常维护提示

- **日志**：每次执行下载脚本都会生成时间戳日志，默认在 `logs/`（或 `--log-dir` 指定路径）。
日志：tail -n 20 /Users/xyl/logs/hf_download_20250917_102451.log
- **缓存**：Hugging Face 缓存默认位于 `~/.cache/huggingface`，可通过设置 `HF_HOME` 或使用脚本的 `--cache-dir` 参数调整位置。
export INDEXTTS_DEVICE=cpu

http://localhost:7860/

- **磁盘空间**：若磁盘剩余空间低于 `--min-free-gb`（默认 2 GB），脚本会自动停止并发出提示。
- **离线部署**：结合 `--package` 生成的压缩包，通过 rsync/scp 等方式传到内网 GPU 服务器，配合现有的 `hf_unpack_and_deploy.sh` 可实现自动解压与 vLLM 服务部署。

---

完成以上步骤即可快速得到一个可复现的 MVP 环境：使用 `uv` 安装依赖、依靠通用脚本高效下载模型、并通过 WebUI 或 API 启动 IndexTTS2，从而在 macOS、Linux、Windows 上快速试用或交付。
