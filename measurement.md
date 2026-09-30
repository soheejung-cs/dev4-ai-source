# 측정 방법론 (성능 변경 검증 시 필수 — .50·.51·.52 3자 검증)

- 컨테이너 ps/top은 컨테이너 시야, /proc/stat·loadavg만 호스트. 측정 전 게이트 필수(동일 빌드 17% 흔들림 실증).
- 질의당 min-of-N은 run 오염 못 잡음 → run 반복 median + rep별 host_idle 기록.
- 판정 임계는 range 아닌 MAD(range는 n↑시 임계 확대 — median-of-10이 5보다 둔감해짐, 판정 1건 뒤집힘 검산).
- 전 질의 "무변화"여도 부호검정 + 순서 반전 필수 — CBRD-27284의 9/9 p=0.0039이 순서 효과였음.

**[.51 — 범위·난수 일반]**
- `drand48()*N`을 인덱스로 캐스팅하면 [0,N-1]이지만 **경계 포함 의도라면 off-by-one** — 샘플링 코드 리뷰 시 범위
  의도(포함/배제)를 주석과 대조. (PR #7463 리뷰에서 실제 지적)

**[vimkim 들여옴 — 바이너리 배치 민감도·빌드 비용, imports/vimkim/build-perf/]**
- **소스 로직과 무관한 16B 함수 이동만으로 짧은 질의 성능이 흔들린다** (CBRD-26382): PR#6636 의 `std::function`→lambda 로 recovery cold code 가 7B 줄자 링크 정렬 도미노로 hot 함수들이
  16B 이동, QA +10.56%(재현 +1.46%). 5회 Top-down 은 front-end bound 가 아니라 **execution core bound 증가**로 분류 — "DSB miss 가 전부" 가 아니다. 7B padding 으로 주소 phase 와 성능이 함께
  복원됨을 확인. 함의: **±수 % 회귀를 소스 변경 탓으로 돌리기 전에 `nm`/`objdump` 로 hot 함수 주소 phase 를 대조**하고, 전 함수 큰 정렬은 해법이 아니다(입증된 함수만 `aligned(32)` 좁게).
  PGO 실험(빌드 비용·배치 증거·성능)은 `CBRD-26382-pgo-experiment_95b79e7ed.md`. — vimkim 2026-09-30
- 클린 빌드 gcc 78.8s vs clang 50.9s 의 차이는 링커/LTO 가 아니라 GCC 컴파일 단계(플래그·PCH 실험 포함) — `debug-gcc-vs-clang-clean-build-analysis_2026-08-13.md`. 규칙집 20장 PHYS 와 같은 축. — vimkim 2026-09-30
