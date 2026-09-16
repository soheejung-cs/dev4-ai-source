# src/thread

> 기준: upstream/develop 95b79e7ed (2026-08-27)

## 1. 소스 목적 및 사용처 (함수별)

현대 C++17 스레딩 인프라(`cubthread` 네임스페이스): 워커 풀·데몬 생성/파괴(`thread_manager`),
`cubthread::worker_pool<Context>`, `cubthread::daemon`+`looper`, `THREAD_ENTRY`(스레드별 컨텍스트),
레거시 named 크리티컬 섹션(`critical_section.c`).

| 함수 | 파일 | 목적 | 주요 사용처(호출자) |
|---|---|---|---|
| `cubthread::get_entry` | thread_manager.cpp:438 | 현재 스레드의 entry(THREAD_ENTRY) 참조 반환 | base/error_context.cpp, base/memory_private_allocator.cpp, loaddb |
| `thread_get_thread_entry_info` | thread_manager.hpp:545 | C 호환 래퍼 — `&get_entry()` 포인터 반환 | 레거시 C 코드 전반 |
| `cubthread::get_manager` | thread_manager.cpp:415 | 전역 manager 싱글턴 | 데몬/워커풀 생성부 전역 |
| `manager::create_worker_pool` / `thread_create_worker_pool` | thread_manager.hpp:137/522 | 워커 풀 생성(크기·코어 수·이름) | query/parallel/px_worker_manager_global.cpp:69, storage/btree_load.c, transaction/log_page_buffer.c |
| `manager::push_task` / `push_task_on_core` | thread_manager.cpp:157/180 | 풀에 entry_task 제출 | 워커 풀 사용처 전반 |
| `manager::create_daemon` | thread_manager.cpp:126 | looper+entry_task로 데몬 생성 | storage/page_buffer.c(pgbuf-* 데몬), double_write_buffer.cpp, session/session.c |
| `manager::claim_entry` / `retire_entry` | thread_manager.cpp:234/242 | 스레드 시작/종료 시 entry 배정·회수(tl_Entry_p 세팅) | 워커풀·데몬 entry_manager 경유 |
| `cubthread::looper` | thread_looper.hpp:81 | 데몬 수면/기상 패턴(무한/주기/delta) | create_daemon 인자 |
| `cubthread::daemon` | thread_daemon.hpp:87 | 백그라운드 데몬 스레드 본체 | vacuum·checkpoint·flush 등 |
| `csect_enter` / `csect_enter_as_reader` / `csect_exit` | critical_section.c:674/891/1504 | 레거시 named 크리티컬 섹션 진입/탈출 | storage/heap_file.c, disk_manager.c, transaction 전반 |

## 2. 분석 내용 (함수별)

> 항목은 함수 단위로 기술한다. 새 분석도 함수명을 앞세워 추가할 것.

### 모듈 일반

- `THREAD_ENTRY`는 코드베이스에서 가장 많이 전달되는 파라미터 — **레이아웃 변경은 전체에 영향**.
  스레드 로컬 할당자, 트랜잭션 인덱스, 에러 컨텍스트, 락/래치 추적, 인터럽트 플래그를 담는다.
- 워커 풀 크기는 성능에 직결 — 너무 적으면 경합, 너무 많으면 오버헤드.
- 크리티컬 섹션은 이름이 있음(named) — CS 트래커(`critical_section_tracker.hpp`)가 획득 순서 기반으로
  잠재 데드락을 검출.
- 레거시 코드는 `critical_section.c`, **새 코드는 C++ 뮤텍스** 사용.
- 새 데몬은 `cubthread::daemon`(looper 지정) + `thread_manager` 등록; 풀 작업은
  `cubthread::entry_task` 서브클래스. 데몬 looper 패턴: `INFINITE_LOOPER`(상시 활성), periodic, delta 기반.
- ✅ **리뷰 체크포인트**: `THREAD_ENTRY` 필드 추가/변경의 전역 파급을 검토했는가?
- ✅ **리뷰 체크포인트**: 새 동기화 코드가 레거시 CS 대신 C++ 뮤텍스를 쓰는가?
- ✅ **리뷰 체크포인트**: CS 획득 순서가 기존 순서 규약과 충돌하지 않는가(트래커 경고)?
- ✅ **리뷰 체크포인트**: 데몬의 looper 패턴이 작업 특성(주기/상시)에 맞는가?

### cubthread::get_entry (thread_manager.cpp)

- `thread_local entry *tl_Entry_p`(L54)를 assert 후 역참조해 반환(L438~447). `claim_entry`/
  `retire_entry`(L234/242)가 스레드 시작/종료 시 이 TLS 포인터를 세팅/해제.
- **TLS general-dynamic 비용(실측)**: 공유 라이브러리의 thread_local 접근이라 함수 전체가 사실상
  `__tls_get_addr` 호출 하나로 컴파일된다 — 행 단위 hot path에서 반복 호출하면 그 호출 비용이
  그대로 곱해진다. 진입 시 1회 받아 `thread_p`로 전달하는 기존 관례를 지킬 것.
  (병렬 실행 경로의 get_entry×4/행 실측 사례는 src-query.md memoize 항목 참조.)

### thread_create_worker_pool / worker_pool 스레드 이름 (thread_manager.hpp / thread_worker_pool_impl.hpp)

- 워커 스레드는 기동 시 `thread_worker_pool_impl.hpp:1391`의
  `pthread_setname_np (pthread_self (), m_parent_core->get_parent_pool ()->get_name ().c_str ())`로
  풀 이름을 그대로 OS 스레드 이름에 박는다. 병렬 질의 풀은
  `px_worker_manager_global.cpp:69`에서 `thread_create_worker_pool (pool_size, 1, "parallel-query", ...)`로 생성.
- 귀결: abort 시 커널 코어 패턴의 `%e` 자리에 `cub_server`가 아니라 스레드 이름이 들어가
  `core.parallel-query.*` 형태의 파일이 생성되며, 생성 위치는 cub_server의 CWD인 `$CUBRID` 디렉터리다
  (2026-07-03 코어 덤프 조사 기록).
- 데몬 경로(`thread_daemon.cpp:215`)는 `TASK_COMM_LEN - 1`로 잘라 넣지만 워커 풀 경로는 자르지
  않으므로, 풀 이름이 15자를 넘으면 이름 설정 자체가 실패해 코어 파일명 규칙도 달라질 수 있다.
- 행번호는 원 기준 CBRD-27094 @ faf5a3b2a에서 기록, 95b79e7ed에서 재검증됨(세 곳 모두 일치).
  이후 커밋으로 어긋날 수 있으니 인용 전 현재 소스와 대조할 것.
- ✅ **리뷰 체크포인트**: 병렬 질의 크래시 조사 시 `cub_server` 이름의 코어만 찾지 말고
  `$CUBRID/core.parallel-query.*`를 함께 확인할 것.

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
