#!/usr/bin/env bash
# HSMR 컨테이너에서 run_demo 진입점까지 import가 되는지 한 번에 확인
# 사용법: ./scripts/verify_hsmr_container.sh

set -e

cd "$(dirname "$0")/.."

echo "=== HSMR 컨테이너 import 검증 ==="
echo "이미지: pipeline-hsmr:latest"
echo ""

if ! docker image inspect pipeline-hsmr:latest &>/dev/null; then
    echo "이미지가 없습니다. 먼저 빌드하세요:"
    echo "  docker compose build --no-cache hsmr"
    exit 1
fi

echo "run_demo.py 진입점 import 시도 중..."
if docker run --rm --entrypoint python pipeline-hsmr:latest -c "
from lib.kits.hsmr_demo import parse_args
print('OK: 모든 import 성공')
" 2>&1; then
    echo ""
    echo "결과: 검증 통과."
    exit 0
else
    echo ""
    echo "결과: 위 오류의 모듈을 Dockerfile 또는 requirements에 추가한 뒤 이미지를 재빌드하세요."
    exit 1
fi
