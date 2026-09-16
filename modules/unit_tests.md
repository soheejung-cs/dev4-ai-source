# unit_tests

> 기준: upstream/develop 95b79e7ed (2026-08-27)

## 1. 소스 목적 및 사용처 (함수별)

Catch2 v2.11.3 기반 C/C++ 엔진 유닛 테스트. `unit_tests/CMakeLists.txt`(마스터 — Catch2 fetch,
모듈별 `option(UNIT_TEST_<MODULE>)` 게이트), `common/`(공유 유틸), 모듈별 `<module>/CMakeLists.txt`
+ `test_*.cpp`. 활성화: `cmake -DUNIT_TESTS=ON` 또는 개별 `-DUNIT_TEST_<MODULE>=ON`, 실행은 `ctest`.

| 진입점/구성 | 파일 | 목적 | 주요 사용처(호출자) |
|---|---|---|---|
| 마스터 CMakeLists | `unit_tests/CMakeLists.txt` | Catch2 `ExternalProject_Add` fetch + 모듈 게이트(`UNIT_TESTS OR UNIT_TEST_*`, :64~) | 최상위 CMake(`-DUNIT_TESTS=ON`) |
| 비활성 블록 `#[[ ... ]]` | `unit_tests/CMakeLists.txt:74~` | `lockfree`(:76)·`loaddb`·`memory_monitor` 모듈 주석 처리 | (컴파일 실패로 비활성) |
| `test_monitor_main.cpp` | `unit_tests/monitor/` | monitor 레지스트리/fetch 검증(`allocate_statistics_buffer` :409, `fetch_global_statistics` :433~) | `ctest`(`test_monitor`) |
| `test_main.cpp` / `test_manager.cpp` | `unit_tests/thread/` | 스레드 매니저 테스트 | `ctest`(`test_thread`) |
| `test_double_write_buffer.cpp` | `unit_tests/double_write_buffer/` | DWB 테스트(AGENTS.md 모듈 표에는 없는 디렉터리 — 실존 확인됨) | `ctest` |
| `test_output.cpp/.hpp` | `unit_tests/common/` | 공유 출력 유틸 | 각 테스트 모듈 |
| `test_perf_compare.cpp/.hpp` | `unit_tests/common/` | 성능 비교 픽스처 | 성능성 테스트 모듈 |
| `test_string_collection.cpp/.hpp`, `test_debug.hpp`, `test_timers.hpp` | `unit_tests/common/` | 문자열 컬렉션/디버그/타이머 공유 유틸 | 각 테스트 모듈 |

## 2. 분석 내용 (함수별)

> 항목은 함수 단위로 기술한다 — 각 항목의 제목/선두가 함수·파일명이다. 새 분석도 함수명을 앞세워 추가할 것.
> (아래 주의점·리뷰 체크포인트의 원본: unit_tests/AGENTS.md 증류)

### 모듈 일반

- **Catch2 v2 (v3 아님)** — `#include "catch2/catch.hpp"` 사용, `catch2/catch_all.hpp` 금지.
- 테스트는 엔진 라이브러리에 링크 — include 경로·링크 의존성 문제가 흔함.
- 테스트 바이너리 이름 `test_<module>`, 태그 `[module_name]`, GNU 브레이스 스타일 유지.
- ✅ **리뷰 체크포인트**: v2 API/헤더를 쓰는가(v3 문법 혼입 없음)?
- ✅ **리뷰 체크포인트**: 공유 픽스처는 `common/`에 두었는가? 프로덕션과 같은 GNU 브레이스 스타일인가?

### 마스터 CMakeLists (unit_tests/CMakeLists.txt)

- 비활성 모듈: `lockfree/`, `loaddb/`, `memory_monitor/` (컴파일 실패) — 마스터 CMakeLists에서
  `#[[ ... ]]`로 주석 처리돼 있음(플래그만이 아님).
- Catch2는 CMake 시점에 `ExternalProject_Add`로 fetch — 첫 빌드에 네트워크 필요.
- 새 모듈 추가 절차: 디렉터리 생성 + `option(UNIT_TEST_<MODULE>)` + `add_subdirectory` 등록.
- ✅ **리뷰 체크포인트**: 새 테스트 모듈이 마스터 CMakeLists의 option + add_subdirectory에 등록됐는가?

## 3. 예비 이슈 사항

> 미수정 버그·의심·문서 정정 후보·구조적 한계. 해소되면 삭제가 아니라 "해소됨(커밋/PR)"로 갱신.

- (현재 등록된 예비 이슈 없음)

## 4. 진행중인 작업

> 각 컨테이너가 자기 소절을 직접 관리한다. 완료되면 지우지 말고 "완료(PR/커밋)"로 갱신.

### .50
- (해당 없음 또는 미기입)

### .51
- (해당 없음 또는 미기입)

### .52
- (해당 없음 또는 미기입)
