# rich 모듈 누락 문제 해결 가이드

## 문제 증상
```
ModuleNotFoundError: No module named 'rich'
(발생 위치: /workspace/lib/platform/config_utils.py)
```

## 원인 분석
- `requirements-hsmr.txt`에 `rich` 패키지가 누락됨
- HSMR 코드(`lib/platform/config_utils.py`, `lib/kits/debug.py` 등)에서 `rich`를 사용하지만 requirements에 없음

---

## 해결 방법

### 방법 1: 임시 핫픽스 (즉시 실행 가능)

**현재 실행 중인 컨테이너에 rich 설치:**

```bash
# 컨테이너가 실행 중인 경우
docker compose --profile pipeline exec hsmr pip install rich==13.9.4

# 또는 컨테이너 이름으로 직접 접근
docker exec pipeline-hsmr pip install rich==13.9.4

# 설치 확인
docker compose --profile pipeline exec hsmr python -c "import rich; print(rich.__version__)"
```

**그 다음 파이프라인 재실행:**
```bash
cd /home/geonwoo/D-PoSE
./run_full_pipeline.sh
```

---

### 방법 2: 영구 수정 (권장)

**Dockerfile 수정 완료됨** ✅

변경 사항:
- `requirements-hsmr-filtered.txt` 설치 후 `rich==13.9.4` 명시적 설치 추가
- 재빌드 시 자동으로 rich가 설치됨

**이미지 재빌드:**

```bash
# HSMR 이미지만 재빌드 (캐시 무시)
cd /home/geonwoo/D-PoSE
docker compose build --no-cache hsmr

# 또는 전체 재빌드
docker compose build --no-cache

# 빌드 확인
docker compose config | grep -A 10 "hsmr:"

# 파이프라인 재실행
./run_full_pipeline.sh
```

---

## Dockerfile 변경 사항 (Diff)

```diff
# 2) pip/setuptools/wheel pin → torch/torchvision → numpy pin → requirements (patch numpy/scipy/opencv, exclude 'lib'/'chumpy') → chumpy (legacy)
 RUN pip install --no-cache-dir pip==25.3 setuptools==80.9.0 wheel==0.45.1 \
     && pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cu121 \
     && pip install --no-cache-dir "numpy==1.26.4" \
     && cp requirements-hsmr.txt requirements-hsmr-patched.txt \
     && sed -i 's/numpy==2\.2\.6/numpy==1.26.4/g' requirements-hsmr-patched.txt \
     && sed -i 's/scipy==1\.16\.1/scipy==1.11.4/g' requirements-hsmr-patched.txt \
     && sed -i 's/opencv-python==4\.12\.0\.88/opencv-python==4.8.1.78/g' requirements-hsmr-patched.txt \
     && grep -v '^lib==' requirements-hsmr-patched.txt | grep -v '^chumpy==' > requirements-hsmr-filtered.txt \
     && pip install --no-cache-dir -r requirements-hsmr-filtered.txt --extra-index-url https://download.pytorch.org/whl/cu121 \
-    && pip install --no-cache-dir --no-build-isolation chumpy==0.70
+    && pip install --no-cache-dir --no-build-isolation chumpy==0.70 \
+    && pip install --no-cache-dir rich==13.9.4
```

**변경 위치**: `/home/geonwoo/HSMR/Dockerfile` 및 `/data/home/HSMR/Dockerfile` (43번째 줄)

---

## 검증

### 1. 임시 핫픽스 검증
```bash
# rich 설치 확인
docker compose --profile pipeline exec hsmr python -c "import rich; print('rich version:', rich.__version__)"
```

### 2. 영구 수정 검증 (재빌드 후)
```bash
# 새로 빌드된 이미지에서 rich 확인
docker run --rm pipeline-hsmr:latest python -c "import rich; print('rich version:', rich.__version__)"
```

### 3. 파이프라인 실행 검증
```bash
cd /home/geonwoo/D-PoSE
./run_full_pipeline.sh
```

---

## 추가 참고사항

### requirements-hsmr.txt에 직접 추가하는 방법 (선택사항)

만약 원본 `requirements-hsmr.txt`에도 추가하고 싶다면:

```bash
# HSMR 디렉터리에서
cd /data/home/HSMR  # 또는 /home/geonwoo/HSMR
echo "rich==13.9.4" >> requirements-hsmr.txt
```

하지만 Dockerfile에서 이미 명시적으로 설치하므로 필수는 아님.

### rich 버전 선택 이유

- `rich==13.9.4`: Python 3.10과 호환되는 안정 버전
- 최신 버전도 가능하지만, 재현성을 위해 pin 권장

---

## 요약

| 방법 | 속도 | 권장도 | 명령어 |
|------|------|--------|--------|
| **임시 핫픽스** | 즉시 | ⚠️ 임시 | `docker compose exec hsmr pip install rich==13.9.4` |
| **영구 수정** | 재빌드 필요 | ✅ 권장 | `docker compose build --no-cache hsmr` |

**권장 순서**: 임시 핫픽스로 먼저 실행 → 영구 수정으로 재빌드
