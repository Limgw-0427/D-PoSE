#!/usr/bin/env bash
# rich 모듈 빠른 수정 스크립트
# 사용법: ./quick_fix_rich.sh

set -e

echo "=========================================="
echo "rich 모듈 빠른 수정"
echo "=========================================="
echo ""

# 옵션 1: 실행 중인 컨테이너에 설치 (임시)
echo "[옵션 1] 실행 중인 컨테이너에 rich 설치 (임시 핫픽스)..."
if docker ps --format '{{.Names}}' | grep -q "^pipeline-hsmr$"; then
    echo "컨테이너가 실행 중입니다. rich 설치 중..."
    docker exec pipeline-hsmr pip install --no-cache-dir rich==13.9.4
    echo "✅ rich 설치 완료"
    echo ""
    echo "다음 단계: 파이프라인 재실행"
    echo "  ./run_full_pipeline.sh"
else
    echo "⚠️  실행 중인 컨테이너가 없습니다."
    echo ""
fi

# 옵션 2: 이미지 재빌드 (영구)
echo "[옵션 2] 이미지 재빌드 (영구 수정)..."
echo "HSMR 이미지를 재빌드합니다..."
cd "$(dirname "$0")"
docker compose build --no-cache hsmr

echo ""
echo "✅ 이미지 재빌드 완료"
echo ""
echo "다음 단계: 파이프라인 실행"
echo "  ./run_full_pipeline.sh"
