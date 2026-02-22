# D-PoSE pipeline service: Python 3.10, isolated Torch, file-based I/O.
# Build context: D-PoSE repo root. Mount shared_data at /workspace/shared.
# output.npz canonical path is created by docker-compose entrypoint.

FROM python:3.10-slim-bookworm

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYOPENGL_PLATFORM=egl

# System deps for OpenCV, rendering, optional runtime libs (OpenEXR), and yolov3 weight download
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libopenexr-dev \
    libimath-dev \
    pkg-config \
    libglfw3-dev \
    libgles2-mesa-dev \
    libturbojpeg0-dev \
    ffmpeg \
    git \
    wget \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

# Copy project
COPY . .

# pip 버전 고정 (26.x에서 chumpy 빌드 시 'No module named pip' 발생 방지)
# chumpy는 별도로 --no-build-isolation 로 설치
RUN pip install --no-cache-dir pip==25.3 setuptools==80.9.0 wheel==0.45.1 \
    && grep -v '^chumpy==' requirements.txt > requirements-filtered.txt \
    && pip install --no-cache-dir -r requirements-filtered.txt \
    && pip install --no-cache-dir --no-build-isolation chumpy==0.70

# yolov3 (multi_person_tracker) expects ~/.torch/models/yolov3.weights and ~/.torch/config/yolov3.cfg
# Pre-download at build so runtime does not need outbound access to pjreddie.com / raw.githubusercontent.com
RUN mkdir -p /root/.torch/models /root/.torch/config \
    && wget -q -O /root/.torch/models/yolov3.weights 'https://pjreddie.com/media/files/yolov3.weights' \
    && wget -q -O /root/.torch/config/yolov3.cfg 'https://raw.githubusercontent.com/mkocabas/yolov3-pytorch/master/yolov3/config/yolov3.cfg'

# Pipeline runs: demo.py --image_folder /workspace/shared/inputs --output_folder /workspace/shared/dpose_out
# output.npz and logging are handled by docker-compose command.
