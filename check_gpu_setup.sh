#!/usr/bin/env bash
# GPU 런타임 설정 진단 스크립트
# 사용법: ./check_gpu_setup.sh

set -e

echo "=========================================="
echo "GPU Runtime 진단 스크립트"
echo "=========================================="
echo ""

# 1. GPU 드라이버 확인
echo "[1/5] GPU 드라이버 확인..."
if command -v nvidia-smi &> /dev/null; then
    nvidia-smi
    echo "✅ GPU 드라이버 정상"
else
    echo "❌ nvidia-smi 명령어 없음. NVIDIA 드라이버 미설치 가능성."
    exit 1
fi
echo ""

# 2. libnvidia-ml.so.1 확인
echo "[2/5] libnvidia-ml.so.1 라이브러리 확인..."
if [ -f "/usr/lib/x86_64-linux-gnu/libnvidia-ml.so.1" ]; then
    ls -lh /usr/lib/x86_64-linux-gnu/libnvidia-ml.so.1
    echo "✅ libnvidia-ml.so.1 존재"
elif [ -f "/usr/lib/libnvidia-ml.so.1" ]; then
    ls -lh /usr/lib/libnvidia-ml.so.1
    echo "✅ libnvidia-ml.so.1 존재 (다른 경로)"
else
    echo "❌ libnvidia-ml.so.1 없음. nvidia-utils 설치 필요."
    echo "   실행: sudo apt install nvidia-utils-535"
    exit 1
fi
echo ""

# 3. Docker NVIDIA 런타임 확인
echo "[3/5] Docker NVIDIA 런타임 확인..."
if docker info 2>/dev/null | grep -qi nvidia; then
    docker info | grep -i nvidia
    echo "✅ Docker NVIDIA 런타임 인식됨"
else
    echo "❌ Docker에서 NVIDIA 런타임 미인식"
    echo "   실행: sudo apt install nvidia-container-toolkit"
    echo "   실행: sudo nvidia-ctk runtime configure --runtime=docker"
    echo "   실행: sudo systemctl restart docker"
    exit 1
fi
echo ""

# 4. 간단한 GPU 테스트
echo "[4/5] Docker 컨테이너 GPU 접근 테스트..."
if docker run --rm --runtime=nvidia nvidia/cuda:12.1.1-base-ubuntu22.04 nvidia-smi &>/dev/null; then
    echo "✅ Docker 컨테이너에서 GPU 접근 성공"
else
    echo "❌ Docker 컨테이너에서 GPU 접근 실패"
    echo "   nvidia-container-toolkit 재설치 및 Docker 재시작 필요"
    exit 1
fi
echo ""

# 5. docker-compose.yml GPU 설정 확인
echo "[5/5] docker-compose.yml GPU 설정 확인..."
if [ -f "docker-compose.yml" ]; then
    if grep -q "runtime: nvidia" docker-compose.yml; then
        echo "✅ docker-compose.yml에 runtime: nvidia 설정됨"
    elif grep -q "deploy:" docker-compose.yml && grep -q "nvidia" docker-compose.yml; then
        echo "⚠️  docker-compose.yml에 deploy.resources 방식 사용 중"
        echo "   호환성 문제 시 runtime: nvidia로 변경 권장"
    else
        echo "❌ docker-compose.yml에 GPU 설정 없음"
    fi
else
    echo "⚠️  docker-compose.yml 파일 없음"
fi
echo ""

echo "=========================================="
echo "✅ 모든 검증 통과!"
echo "=========================================="
echo ""
echo "다음 단계: ./run_full_pipeline.sh 실행"
