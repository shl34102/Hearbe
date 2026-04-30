# AI/Dockerfile
FROM nvidia/cuda:12.3.2-cudnn9-runtime-ubuntu22.04

WORKDIR /app

# Python 3.10 설치 (PaddlePaddle 3.0.0 호환)
RUN apt-get update -y && apt-get install -y \
    software-properties-common \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update -y && apt-get install -y \
    python3.10 \
    python3.10-venv \
    python3.10-dev \
    python3-pip \
    curl \
    libsndfile1 \
    ffmpeg \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/bin/python3.10 /usr/bin/python \
    && ln -sf /usr/bin/python3.10 /usr/bin/python3

# pip 업그레이드
RUN python -m pip install --upgrade pip setuptools wheel

# Faster-Whisper (검증된 버전)
RUN pip install --no-cache-dir \
    faster-whisper \
    "ctranslate2>=4.0,<5" \
    "huggingface_hub>=0.23" \
    "tokenizers>=0.13,<1" \
    "onnxruntime>=1.14,<2" \
    "av>=11"

# Qwen3-ASR (선택적 ASR 백엔드)
# blinker 충돌 해결: distutils 설치된 패키지 강제 제거 후 설치
# torch를 cu121 버전으로 재설치하여 NCCL 심볼 문제 해결
RUN rm -rf /usr/lib/python3/dist-packages/blinker* && \
    pip install --no-cache-dir "qwen-asr" && \
    pip install --no-cache-dir --force-reinstall \
    torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# PaddlePaddle 3.0.0 GPU (CUDA 12.x - 중국 미러)
RUN pip install --no-cache-dir \
    paddlepaddle-gpu==3.0.0 \
    -i https://www.paddlepaddle.org.cn/packages/stable/cu126/

# PaddleOCR
RUN pip install --no-cache-dir paddleocr

# FastAPI & 나머지
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Source
COPY . .

# Cache
ENV HF_HOME=/root/.cache/huggingface
ENV PADDLE_HOME=/root/.paddleocr

# Server
ENV SERVER_HOST=0.0.0.0
ENV SERVER_PORT=8000
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=120s \
    CMD curl -f http://localhost:8000/ || exit 1

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
