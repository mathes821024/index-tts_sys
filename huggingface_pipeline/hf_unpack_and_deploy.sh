#!/bin/bash
# 🧩 企业级无网部署脚本：解压 Hugging Face 模型并启动 vLLM 服务
# 用法: bash hf_unpack_and_deploy.sh Qwen3-14B [PORT]

set -euo pipefail

# ========= 🔧 参数准备 =========
MODEL_NAME="${1:-}"
PORT="${2:-8000}"

if [[ -z "$MODEL_NAME" ]]; then
  echo "❌ 错误：未传入模型名称"
  echo "👉 用法: bash $0 Qwen3-14B [PORT]"
  exit 1
fi

MODEL_SNAKE_NAME="${MODEL_NAME//-/_}"
MODEL_TAR="/data/transfer/${MODEL_NAME}.tar.zst"
TARGET_DIR="/data/models/huggingface/${MODEL_NAME}"
DEPLOY_DIR="/data/vllm_deploy/${MODEL_NAME}"
GPU_LIST=$(nvidia-smi --query-gpu=index --format=csv,noheader | paste -sd "," -)
TP_SIZE=$(nvidia-smi -L | wc -l)
MAX_LEN=32768
LOG_DIR="/var/log/vllm"
mkdir -p "$LOG_DIR"

# ========= 🧪 工具检测 =========
for cmd in docker zstd tar; do
  if ! command -v $cmd &>/dev/null; then
    echo "❌ 缺少命令: $cmd，请先安装"
    exit 1
  fi
done

# ========= 📦 模型包校验 =========
if [ ! -f "$MODEL_TAR" ]; then
  echo "❌ 未找到模型包: $MODEL_TAR"
  exit 1
fi

echo "📦 正在部署模型: $MODEL_NAME (TP=$TP_SIZE, PORT=$PORT)"

# ========= 📂 解压模型 =========
echo "📂 解压路径: $TARGET_DIR"
mkdir -p "$(dirname "$TARGET_DIR")"
tar --use-compress-program zstd -xf "$MODEL_TAR" -C "$(dirname "$TARGET_DIR")"

# ========= 🏗️ 准备部署目录 =========
mkdir -p "$DEPLOY_DIR"
cd "$DEPLOY_DIR"

# ========= ✏️ 写入 .env =========
cat > .env <<EOF
PORT=${PORT}
GPU_LIST=${GPU_LIST}
MODEL_PATH=${TARGET_DIR}
MODEL_NAME=${MODEL_NAME}
SHM_SIZE=8g
VLLM_ALLOW_LONG_MAX_MODEL_LEN=1
DTYPE=float16
MAX_LEN=${MAX_LEN}
MAX_NUM_SEQS=256
TOKENIZER_POOL_SIZE=2
RAG_ENABLED=false
EOF

# ========= 📜 写入 docker-compose.yml =========
cat > docker-compose.yml <<EOF
version: '3.9'

services:
  ${MODEL_SNAKE_NAME}_vllm:
    image: vllm/vllm-openai:v0.8.3
    container_name: vllm_${MODEL_SNAKE_NAME}
    restart: unless-stopped
    ports:
      - "\${PORT}:8000"
    volumes:
      - \${MODEL_PATH}:/models
    shm_size: \${SHM_SIZE}
    environment:
      - HF_HUB_OFFLINE=1
      - CUDA_VISIBLE_DEVICES=\${GPU_LIST}
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: ${TP_SIZE}
              capabilities: ["gpu"]
    command: [
      "--model", "/models",
      "--served-model-name", "\${MODEL_NAME}",
      "--port", "8000",
      "--trust-remote-code",
      "--gpu-memory-utilization", "0.9",
      "--enforce-eager",
      "--max-model-len", "\${MAX_LEN}",
      "--max-num-seqs", "\${MAX_NUM_SEQS}",
      "--tokenizer-pool-size", "\${TOKENIZER_POOL_SIZE}",
      "--tensor-parallel-size", "${TP_SIZE}"
    ]
EOF

# ========= ▶️ 启动容器 =========
echo "🚀 启动 vLLM 服务..."
docker compose --env-file .env up -d

# ========= ✅ 校验容器状态 =========
sleep 3
if docker ps -a | grep -q "vllm_${MODEL_SNAKE_NAME}"; then
  echo "✅ 模型 ${MODEL_NAME} 已成功部署 🎉"
  docker logs "vllm_${MODEL_SNAKE_NAME}" > "$LOG_DIR/${MODEL_NAME}.log" 2>&1
  echo "📄 日志路径: $LOG_DIR/${MODEL_NAME}.log"
else
  echo "❌ 容器未正常启动，请手动排查：docker logs vllm_${MODEL_SNAKE_NAME}"
  exit 1
fi

# ========= 📊 展示资源状态 =========
echo "🖥️ 当前 GPU 使用状态："
nvidia-smi
echo "📦 当前容器运行状态："
docker ps -a | grep "vllm_${MODEL_SNAKE_NAME}"

