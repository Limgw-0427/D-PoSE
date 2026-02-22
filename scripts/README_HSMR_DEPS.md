# HSMR 의존성 한 번에 확인하는 방법

두 가지 방법을 제공합니다.

---

## 1) 컨테이너에서 실제 import 검증 (가장 확실)

이미지 빌드 후 **실제로 run_demo 진입점까지 import**가 되는지 한 번에 확인합니다.  
누락된 모듈이 있으면 바로 `ModuleNotFoundError` 이름을 알 수 있습니다.

```bash
cd ~/D-PoSE

# 이미지가 있어야 함 (없으면 먼저 docker compose build --no-cache hsmr)
./scripts/verify_hsmr_container.sh
```

- **성공**: `OK: 모든 import 성공` → 파이프라인 실행 가능
- **실패**: 출력된 모듈 이름을 Dockerfile의 `pip install ... rich colorlog wis3d` 뒤에 추가한 뒤 **이미지 재빌드**

---

## 2) 코드 기준으로 누락 후보 나열 (빌드 전 점검)

HSMR 전체 `.py`에서 `import` / `from ... import`를 수집해,  
`requirements-hsmr.txt` + Dockerfile 추가 패키지(rich, colorlog, wis3d)와 비교해 **누락될 수 있는 패키지**를 출력합니다.

```bash
cd ~/D-PoSE

# HSMR 경로가 ../HSMR 또는 ./HSMR 가정
python3 scripts/check_hsmr_imports.py

# HSMR 경로 직접 지정
python3 scripts/check_hsmr_imports.py --path /home/geonwoo/HSMR
```

- 표준 라이브러리, 로컬 패키지(`lib`, `exp`, `detectron2` 등), 선택적/개발용 패키지는 제외됩니다.
- 나온 이름이 꼭 모두 필요한 것은 아니므로, **실제로 run_demo 실행 시 누락 오류가 나는 것만** Dockerfile에 추가하면 됩니다.

---

## 권장 순서

1. **빌드 전** (선택): `python3 scripts/check_hsmr_imports.py` 로 누락 후보 확인
2. **빌드 후**: `./scripts/verify_hsmr_container.sh` 로 실제 import 성공 여부 확인
3. `verify_hsmr_container.sh` 에서 누락 오류가 나오면 → 해당 모듈을 Dockerfile에 추가 후 **이미지 재빌드** → 다시 2번 실행

이렇게 하면 **한 번에** 누락 모듈을 확인·보완할 수 있습니다.
