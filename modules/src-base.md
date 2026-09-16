# src/base

> 기준: upstream/develop 95b79e7ed (2026-08-27)

## 1. 소스 목적 및 사용처 (함수별)

전 모듈이 쓰는 기반층: 메모리 관리(`memory_alloc.c`), 에러 처리(`error_code.h` ~1700개 코드,
`error_manager.c`), 락프리 자료구조(`lock_free.c` 레거시 / `lockfree_hashmap.hpp` 현대),
시스템 설정(`system_parameter.c` — base 최대 파일, ~400개 `PRM_ID_*`, cubrid.conf),
직렬화(`packer.hpp`, `object_representation.h`), i18n/타임존, 성능 모니터링, fault injection.

| 함수 | 파일 | 목적 | 주요 사용처(호출자) |
|---|---|---|---|
| `er_set` | error_manager.c:1229 | 스레드별 에러 스택에 에러 세팅+로깅 | 전 모듈(storage, transaction, broker …) |
| `er_errid` | error_manager.c:1826 | 현재 스레드의 마지막 에러 코드 조회 | 전 모듈 — 실패 반환 후 원인 확인 |
| `er_clear` / `er_has_error` | error_manager.c:1202/1918 | 에러 상태 초기화/존재 검사 | 재시도 경로, ASSERT_ERROR 계열 |
| `db_private_alloc` / `db_private_free` | memory_alloc.h 매크로 → memory_alloc.c:420~ | 스레드 사설 힙 할당/해제(NDEBUG 여부로 debug/release 구현 분기) | 서버 측 전 모듈 |
| `free_and_init` / `db_private_free_and_init` | memory_alloc.h:132/124(디버그)·154/148(릴리스) | 해제 후 포인터 NULL 세팅 매크로 | 전 모듈 관용구 |
| `prm_get_integer_value` / `prm_get_bool_value` | system_parameter.c:12358/12373 | `PRM_ID_*` 파라미터 값 조회 | 전 모듈 |
| `sysprm_load_and_init` | system_parameter.c:6471 | cubrid.conf 로드·파라미터 초기화 | boot 경로, broker/broker.c, network_sr.c |
| `fi_test` (`FI_TEST` 매크로) | fault_injection.c / fault_injection.h:37 | 지정 지점에서 fault 주입 실행 | storage/btree.c, 로그·디스크 관리 경로 |
| `fi_handler_random_exit` | fault_injection.c:44(선언)/414(정의) | 확률적 abort/_exit 핸들러 (FI 복구 테스트용) | fi_Handlers 테이블(L59~) 경유 |
| `lf_hash_find` | lock_free.c:2024 | 레거시 락프리 해시 조회 | storage/heap_file.c, transaction/log_tran_table.c |
| `mht_get` / `mht_put` | memory_hash.c:1443/1842 | 범용 체이닝 해시(MHT_TABLE) | object/work_space.c, trigger_manager.c, parser/name_resolution.c |
| `intl_identifier_casecmp` | intl_support.c:2863 | 식별자 대소문자 무시 비교 | parser 전역, 스키마 이름 비교 |
| `restrack_assert` | resource_tracker.hpp:446 | 디버그 자원(페이지 fix·락·메모리) 불균형 assert | resource_tracker 내부 — 디버그 빌드 한정 |

## 2. 분석 내용 (함수별)

> 항목은 함수 단위로 기술한다. 새 분석도 함수명을 앞세워 추가할 것.

### 모듈 일반

- `memory_wrapper.hpp`는 **헤더 파일에 include 금지**, .c/.cpp의 마지막 include만 허용(CI 강제).
  반면 `memory_cwrapper.h`는 헤더에 넣어도 안전(SERVER_MODE에서 malloc/free를 추적 함수로 재정의).
- 새 에러 코드는 6곳 갱신 세트(루트 AGENTS.md 절차).
- 레거시(`lock_free.c`, `perf_monitor.c`)와 현대(C++ hpp — `lockfree_hashmap.hpp`, `perf.hpp`) 계열이
  공존 — 수정 대상이 어느 계열인지 먼저 확인.
- ✅ **리뷰 체크포인트**: 헤더에 `memory_wrapper.hpp`를 include하지 않았는가? .c/.cpp에서는 마지막
  include + 주석인가?
- ✅ **리뷰 체크포인트**: 새 에러 코드가 6곳 모두 갱신됐는가?
- ✅ **리뷰 체크포인트**: 레거시/현대 어느 계열에 맞춰야 하는지 확인했는가?

### er_set / er_errid (error_manager.c)

- `er_set()` 2번째 인자는 항상 `ARG_FILE_LINE` (`__FILE__, __LINE__`로 확장).
- 심각도 순서: `ER_FATAL_ERROR_SEVERITY` > `ER_ERROR_SEVERITY` > `ER_SYNTAX_ERROR_SEVERITY` >
  `ER_WARNING_SEVERITY` > `ER_NOTIFICATION_SEVERITY`.
- 에러를 세팅해야 하는 연산 뒤에는 `ASSERT_ERROR()` / `ASSERT_ERROR_AND_SET(error_code)`.
- ✅ **리뷰 체크포인트**: `er_set()` 호출에 `ARG_FILE_LINE`이 빠지지 않았는가? 실패 경로마다 에러가
  실제로 세팅되는가?

### db_private_alloc / free_and_init (memory_alloc.c/h)

- 실제 백엔드는 모드별로 다름: SERVER는 스레드별 LEA 힙, CS는 `db_ws_alloc` 워크스페이스, SA는 조건부.
- 매크로가 NDEBUG 여부로 `db_private_alloc_debug`(caller file/line 추적) /
  `db_private_alloc_release`로 분기(memory_alloc.c:420~438).

### prm_get_integer_value / sysprm_load_and_init (system_parameter.c)

- 시스템 파라미터 추가는 `PRM_ID_*` 추가 + `prm_Def` 엔트리 + `PRM_LAST_ID` 갱신 세트.
- ✅ **리뷰 체크포인트**: 새 `PRM_ID_*`가 `prm_Def`와 `PRM_LAST_ID`까지 함께 갱신됐는가?

### lf_hash_find (lock_free.c) — 락프리 공통 규칙

- 접근 전 반드시 트랜잭션 시작, 끝나면 종료. retire된 노드는 모든 동시 리더가 retirement ID를
  지나야 회수된다. 현대 구조는 `lockfree::tran::system`, 레거시는 `LF_TRAN_SYSTEM`/`LF_TRAN_ENTRY` —
  같은 개념의 C API.
- ✅ **리뷰 체크포인트**: 락프리 자료구조 접근이 트랜잭션 시작/종료로 감싸져 있는가?

### fi_handler_random_exit / fi_test (fault_injection.c)

- `fi_handler_random_exit`: fault_injection.c:44 선언, L414 정의. `rand () % mod_factor`(인자 없으면
  기본 20000)가 0이면 `er_print_callstack ("FAULT INJECTION: RANDOM EXIT")` 후
  `PRM_ID_FAULT_INJECTION_ACTION_PREFER_ABORT_TO_EXIT`가 켜져 있으면 `abort ()`, 아니면 `_exit (0)`.
- `fault_injection_test` 파라미터는 system_parameter.c에 실재(`PRM_NAME_FAULT_INJECTION_TEST` L645,
  `PRM_ID_FAULT_INJECTION_TEST` prm_Def L4008).
- `FI_TEST`/`FI_TEST_ARG` 매크로는 릴리스(NDEBUG) 빌드에서 `(NO_ERROR)` no-op(fault_injection.h:37/43).
- **코어 판정 예외**: FI 복구 시나리오가 켜진 테스트에서 나온 abort/코어는 **고의 주입**이다 —
  크래시 조사 시 fault injection 활성 여부(`fault_injection_test` 등)를 먼저 확인하고, 해당 코어는
  제품 버그 판정에서 예외로 취급할 것.

### restrack_assert (resource_tracker.hpp) — 릴리스 벤치마크 결과는 자원 수명 변경의 증거가 될 수 없다 (PR#7658)

- `restrack_assert`는 resource_tracker.hpp:446에 정의되어 있고 본문 전체가 `#if !defined (NDEBUG)` ~
  `#endif`(같은 파일 448~457행)로 감싸여 있어 릴리스 빌드에서는 호출부가 통째로 no-op이 된다.
  (원 메모의 `:455` 참조는 부정확했고, 95b79e7ed에서 재검증 — 정의 :446, 가드 448~457행.
  원 기준: CBRD-27094 @ faf5a3b2a.)
- 귀결: 릴리스 빌드에서 돌린 벤치마크는 페이지 fix 누락이나 `db_private_alloc` 해제 누락을 원리상
  한 건도 검출하지 못한다. 실제로 PR#7658은 릴리스 TPC-H에서 22/22 질의 결과 바이트가 동일했는데도
  디버그 CI에서 abort가 쏟아졌다. 이 계열 버그의 재현·검증은 반드시 디버그 빌드 + CTP로 해야 하며,
  릴리스 성능·정합성 수치는 반증이 되지 않는다.
- 디버그 빌드의 resource tracker는 `push_track()`/`pop_track()` 쌍으로 페이지 fix/락 불균형을 pop
  시점에 검출한다.
- ✅ **리뷰 체크포인트**: 자원(페이지 fix, private 메모리) 획득/해제 경로를 건드린 변경에 "릴리스에서
  정상 동작하고 성능도 동일하다"만 근거로 달려 있으면 불충분하다고 지적하고 디버그 빌드 CTP 결과를
  요구할 것.

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
