# NVIDIA GPU Runtime 오류 해결 Runbook

## 오류 증상
```
Error: nvidia-container-cli: initialization error: load library failed:
libnvidia-ml.so.1: cannot open shared object file: no such file or directory
```

---

## 1단계: 호스트 진단

### 1.1 GPU 드라이버 확인
```bash
# GPU가 인식되는지 확인
nvidia-smi

# 출력 예시:
# +-----------------------------------------------------------------------------+
# | NVIDIA-SMI 535.xx      Driver Version: 535.xx      CUDA Version: 12.x     |
# +-----------------------------------------------------------------------------+
```

**예상 결과**: GPU 정보가 정상 출력되어야 함. 실패 시 NVIDIA 드라이버 미설치/미인식.

### 1.2 libnvidia-ml.so.1 라이브러리 위치 확인
```bash
# 라이브러리 파일 존재 확인
ls -l /usr/lib/x86_64-linux-gnu/libnvidia-ml.so.1
ls -l /usr/lib/libnvidia-ml.so.1
find /usr -name "libnvidia-ml.so.1" 2>/dev/null

# 또는 locate 사용 (mlocate 설치 필요)
sudo updatedb
locate libnvidia-ml.so.1
```

**예상 결과**: 파일이 존재해야 함. 없으면 nvidia-utils 패키지 미설치.

### 1.3 Docker NVIDIA 런타임 확인
```bash
# Docker가 NVIDIA 런타임을 인식하는지 확인
docker info | grep -i nvidia

# 출력 예시:
# Runtimes: nvidia runc
# Default Runtime: runc
```

**예상 결과**: `Runtimes: nvidia` 또는 `nvidia-container-runtime`가 보여야 함.

### 1.4 GPU 런타임 테스트 (간단한 컨테이너 실행)
```bash
# NVIDIA CUDA 베이스 이미지로 GPU 접근 테스트
docker run --rm --gpus all nvidia/cuda:12.1.1-base-ubuntu22.04 nvidia-smi

# 또는 runtime 명시
docker run --rm --runtime=nvidia nvidia/cuda:12.1.1-base-ubuntu22.04 nvidia-smi
```

**예상 결과**: 컨테이너 내부에서 `nvidia-smi` 출력이 정상적으로 나와야 함.

---

## 2단계: 문제 진단 및 해결

### 시나리오 A: nvidia-smi 실패 (드라이버 미설치)

```bash
# Ubuntu 24.04 기준 NVIDIA 드라이버 설치
# 1) 패키지 리스트 업데이트
sudo apt update

# 2) NVIDIA 드라이버 설치 (권장: 최신 stable)
sudo apt install -y nvidia-driver-535 nvidia-utils-535

# 또는 자동 감지 설치
sudo ubuntu-drivers autoinstall

# 3) 재부팅
sudo reboot

# 4) 재부팅 후 확인
nvidia-smi
```

### 시나리오 B: libnvidia-ml.so.1 없음 (nvidia-utils 미설치)

```bash
# nvidia-utils 패키지 설치
sudo apt update
sudo apt install -y nvidia-utils-535

# 또는 드라이버와 함께 재설치
sudo apt install --reinstall nvidia-driver-535 nvidia-utils-535

# 라이브러리 확인
ls -l /usr/lib/x86_64-linux-gnu/libnvidia-ml.so.1
```

### 시나리오 C: Docker NVIDIA 런타임 미설치/미설정

```bash
# 1) nvidia-container-toolkit 설치
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
    sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

sudo apt update
sudo apt install -y nvidia-container-toolkit

# 2) Docker 런타임 설정
sudo nvidia-ctk runtime configure --runtime=docker

# 3) Docker 재시작
sudo systemctl restart docker

# 4) 확인
docker info | grep -i nvidia
```

### 시나리오 D: Rootless Docker 사용 중

```bash
# Rootless Docker에서 NVIDIA 런타임 사용은 복잡함.
# 옵션 1: Rootful Docker로 전환 (권장)
# 옵션 2: Rootless용 설정 (고급)

# Rootless 확인
docker info | grep "Root Dir"

# Rootless인 경우, rootful로 전환:
# 1) 현재 사용자에서 docker context 확인
docker context ls

# 2) default context로 전환
docker context use default

# 3) sudo로 docker 실행하도록 변경
```

---

## 3단계: docker-compose.yml GPU 설정 점검 및 수정

### 현재 설정 (Compose v2 표준)
```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: 1
          capabilities: [gpu]
```

### 대체 설정 옵션

#### 옵션 1: `runtime: nvidia` (레거시, 가장 호환성 좋음)
```yaml
services:
  hsmr:
    # ... 기존 설정 ...
    runtime: nvidia
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
    # deploy 섹션 제거
```

#### 옵션 2: `gpus: all` (Compose v2, 간단)
```yaml
services:
  hsmr:
    # ... 기존 설정 ...
    gpus: all
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
    # deploy 섹션 제거
```

#### 옵션 3: `device_requests` (일부 버전)
```yaml
services:
  hsmr:
    # ... 기존 설정 ...
    device_requests:
      - driver: nvidia
        count: 1
        capabilities: [gpu]
```

---

## 4단계: 수정된 docker-compose.yml 적용

### 권장 수정안 (호환성 최대화)

아래 패치를 적용하거나, `docker-compose.yml`을 아래 내용으로 교체:

```yaml
# File-based Docker Compose pipeline: hsmr -> dpose -> fusion (sequential).
# Run from this directory. Ensure HSMR and fusion are at ../HSMR and ../fusion,
# or set build context paths via environment variables.
# Usage: ./run_full_pipeline.sh  (sequential: docker compose run --rm hsmr; dpose; fusion)

services:
  hsmr:
    build:
      context: ${HSMR_CONTEXT:-../HSMR}
      dockerfile: Dockerfile
    image: pipeline-hsmr:latest
    container_name: pipeline-hsmr
    volumes:
      - shared_data:/workspace/shared
    runtime: nvidia
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
    entrypoint: ["/bin/bash", "-c"]
    command:
      - |
        set -e
        mkdir -p /workspace/shared/logs /workspace/shared/hsmr_out
        python exp/run_demo.py -i /workspace/shared/inputs -o /workspace/shared/hsmr_out 2>&1 | tee /workspace/shared/logs/hsmr.log
        exit $${PIPESTATUS[0]}
    profiles:
      - pipeline

  dpose:
    build:
      context: .
      dockerfile: Dockerfile
    image: pipeline-dpose:latest
    container_name: pipeline-dpose
    volumes:
      - shared_data:/workspace/shared
    runtime: nvidia
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
    entrypoint: ["/bin/bash", "-c"]
    command:
      - |
        set -e
        mkdir -p /workspace/shared/logs /workspace/shared/dpose_out
        python demo.py --image_folder /workspace/shared/inputs --output_folder /workspace/shared/dpose_out --cfg configs/dpose_conf.yaml --ckpt data/ckpt/paper_arxiv.ckpt 2>&1 | tee /workspace/shared/logs/dpose.log
        RC=$${PIPESTATUS[0]}
        FIRST_NPZ=$$(ls /workspace/shared/dpose_out/*_dpose.npz 2>/dev/null | head -1)
        if [ -n "$$FIRST_NPZ" ] && [ -f "$$FIRST_NPZ" ]; then
          cp "$$FIRST_NPZ" /workspace/shared/dpose_out/output.npz
        fi
        exit $$RC
    profiles:
      - pipeline

  fusion:
    build:
      context: ${FUSION_CONTEXT:-../fusion}
      dockerfile: Dockerfile
    image: pipeline-fusion:latest
    container_name: pipeline-fusion
    volumes:
      - shared_data:/workspace/shared
    entrypoint: ["/bin/bash", "-c"]
    command:
      - |
        set -e
        mkdir -p /workspace/shared/logs /workspace/shared/fusion_out
        python scripts/run_fusion.py \
          --hsmr-npz /workspace/shared/hsmr_out/export/me_hsmr.npz \
          --dpose-npz /workspace/shared/dpose_out/output.npz \
          --output /workspace/shared/fusion_out/fused_f1.npz 2>&1 | tee /workspace/shared/logs/fusion.log
        exit $${PIPESTATUS[0]}
    profiles:
      - pipeline

volumes:
  shared_data:
    name: shared_data
```

**변경 사항**:
- `deploy.resources.reservations.devices` 제거
- `runtime: nvidia` 추가 (hsmr, dpose에만)
- fusion은 GPU 불필요하므로 runtime 없음

---

## 5단계: 최종 검증 체크리스트

### 5.1 호스트 검증
```bash
# ✅ GPU 드라이버
nvidia-smi

# ✅ 라이브러리 존재
ls -l /usr/lib/x86_64-linux-gnu/libnvidia-ml.so.1

# ✅ Docker NVIDIA 런타임
docker info | grep -i nvidia

# ✅ 간단한 GPU 테스트
docker run --rm --runtime=nvidia nvidia/cuda:12.1.1-base-ubuntu22.04 nvidia-smi
```

### 5.2 docker-compose 검증
```bash
# docker-compose.yml 문법 검사
docker compose config

# GPU 설정 확인 (hsmr 서비스에 runtime: nvidia가 있는지)
docker compose config | grep -A 5 "hsmr:"

# 테스트 실행 (실제 파이프라인 실행 전)
docker compose --profile pipeline run --rm hsmr nvidia-smi
```

### 5.3 파이프라인 재실행
```bash
# 모든 검증 통과 후
cd /home/geonwoo/D-PoSE
./run_full_pipeline.sh
```

---

## 문제 해결 요약

| 증상 | 원인 | 해결책 |
|------|------|--------|
| `nvidia-smi` 실패 | 드라이버 미설치 | `sudo apt install nvidia-driver-535` + 재부팅 |
| `libnvidia-ml.so.1` 없음 | nvidia-utils 미설치 | `sudo apt install nvidia-utils-535` |
| Docker에서 GPU 미인식 | nvidia-container-toolkit 미설치 | `sudo apt install nvidia-container-toolkit` + `sudo nvidia-ctk runtime configure` + `sudo systemctl restart docker` |
| compose에서 GPU 오류 | `deploy.resources` 방식 미지원 | `runtime: nvidia` 사용 |

---

## 추가 참고사항

### Docker Compose 버전 확인
```bash
docker compose version
# v2.x 이상 권장
```

### NVIDIA Container Toolkit 버전 확인
```bash
nvidia-ctk --version
```

### Docker 데몬 설정 확인
```bash
cat /etc/docker/daemon.json
# "runtimes": { "nvidia": {...} } 가 있어야 함
```

### 로그 확인 (오류 발생 시)
```bash
# Docker 로그
sudo journalctl -u docker.service -n 50

# 컨테이너 로그
docker compose --profile pipeline logs hsmr
```
