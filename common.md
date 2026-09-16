# 공통

루트 AGENTS.md에서 전 모듈에 걸치는 규칙만 추림. CUBRID 11.5.x, C/C++17 RDBMS + Java PL 엔진, Apache 2.0.
`.c` 파일도 C++17로 컴파일된다(`c_to_cpp.sh`).

## 서버/클라이언트 이중 컴파일 (SERVER_MODE / SA_MODE / CS_MODE)

- 동일 소스가 전처리 가드로 3개 바이너리로 컴파일된다:
  - `SERVER_MODE` → `cub_server` (CMake 타깃 `cubrid/`) — 서버 프로세스
  - `SA_MODE` → `cubridsa` 라이브러리 (`sa/`) — 클라이언트+서버 in-process 독립 실행
  - `CS_MODE` → `cubridcs` 라이브러리 (`cs/`) — 서버 접속 클라이언트
- 파서/옵티마이저는 **클라이언트 측** 코드: `#if !defined(SERVER_MODE)` 가드. 서버에서 돌지 않는다.
- 모듈별 CMakeLists.txt는 없다. 소스 파일 추가는 최상위 `cubrid/CMakeLists.txt`, `cs/CMakeLists.txt`,
  `sa/CMakeLists.txt`에서 한다 (src/AGENTS.md).
- 파일 접미 관례: `_sr` = 서버(SERVER/SA), `_cl` = 클라이언트(CS/SA).

## 에러 처리 관습

- 에러 코드는 `src/base/error_code.h`에 음수 `#define`, `NO_ERROR = 0`.
- `er_set (ER_ERROR_SEVERITY, ARG_FILE_LINE, ER_CODE, ...)` 사용, `error != NO_ERROR`로 체크.
- **새 에러 코드는 6곳 갱신 필수**:
  1. `src/base/error_code.h` 2. `src/compat/dbi_compat.h` 3. `msg/en_US.utf8/cubrid.msg`
  4. `msg/ko_KR.utf8/cubrid.msg` 5. `ER_LAST_ERROR` 상수 6. 클라이언트 노출 시 CCI `base_error_code.h`
- 엔진 코드에 **C++ 예외 금지** — `er_set` + 반환 코드의 C 에러 모델로 통일.

## 메모리 관습

- **`free()` 직접 사용 금지** — `free_and_init(ptr)`로 널리파이.
- 서버 측 할당: `db_private_alloc(thread_p, size)`. 파서 수명 할당: `parser_alloc(parser, len)`.
- 엔진 C 코드에서 **메모리용 RAII 금지** — `db_private_alloc`/`malloc` + 명시적 `free_and_init()`.
- `memory_wrapper.hpp`는 **반드시 마지막 include**여야 하고, 바로 위에
  `// XXX: SHOULD BE THE LAST INCLUDE HEADER` 주석 필수 (CI 검사).

## 코드 스타일 중 실수 잦은 것 (CI 강제)

- 들여쓰기 2칸, 탭 금지. 줄 폭 120자. C/H는 `indent -l120 -lc120`, C++/HPP는 `astyle --style=gnu`,
  Java는 `google-java-format`.
- GNU 브레이스 스타일 — 여는 중괄호를 새 줄에, 본문 수준으로 들여씀. 함수 중괄호는 0열.
- 포인터 별표는 변수에 붙임: `PT_NODE *node`. 함수 호출 시 `(` 앞에 공백.
- 헤더 가드 `_FILENAME_H_` — `#pragma once` 금지.
- C 파일은 `/* ... */` 주석만. `.c` 파일은 `config.h`를 첫 include로.
- C 함수 이름 `module_action_object` (예: `pt_make_flat_name_list`). C++ 네임스페이스는 짧은 소문자.
- PR 제목은 `^\[[A-Z]+-\d+\]\s.+` 형식 (예: `[CBRD-12345] ...`).

## 안티패턴 목록 (루트 AGENTS.md 원문)

- `free()` 직접 사용 금지 → `free_and_init()`.
- `#pragma once` 금지 → `#ifndef _FILENAME_H_` 가드.
- `memory_wrapper.hpp`를 다른 include 앞에 두지 말 것 — 반드시 마지막.
- `memory_wrapper.hpp` 위 `// XXX: SHOULD BE THE LAST INCLUDE HEADER` 주석 생략 금지.
- `src/heaplayers/` 파일을 cppcheck에 포함 금지 — 3rd-party.
- 승인 없이 인라인 주석으로 cppcheck 에러 억제 금지.
- `lea_heap.c` 수정 회피 — 3rd-party 코드 (181KB malloc 구현).
- 엔진 코드에 C++ 예외 금지.
- 엔진 C 코드에 메모리 RAII 금지.
- 대형 파일(10K+ 라인) 분할 금지 — 의도된 구조이지 기술 부채가 아님.

## 전 모듈 공통 함정

- `src/broker/`(구현)와 최상위 `broker/`(CMake 타깃)는 다른 것.
- LOB은 횡단 관심사: 로케이터는 `src/object/lob_locator.cpp`, 외부 저장 백엔드는 `src/storage/es.c`.
- 리포에 백업 파일(`.c~`, `.cpp.orig`)이 존재 — 무시할 것.
- 유닛 테스트 모듈 `LOCKFREE`, `LOADDB`, `MEMORY_MONITOR`는 컴파일 문제로 비활성.
