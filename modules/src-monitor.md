# src/monitor

> 기준: upstream/develop 95b79e7ed (2026-08-27)

## 1. 소스 목적 및 사용처 (함수별)

성능 통계의 중앙 수집·내보내기(`cubmonitor` 네임스페이스). 통계 프리미티브(accumulator, gauge,
max/min — `monitor_statistic.hpp`), 트랜잭션별 시트(`monitor_transaction.cpp`의
`transaction_sheet_manager`), 전역 레지스트리(`monitor_registration.cpp`), 서버 전용 VACUUM
오버플로 페이지 임계 모니터(`monitor_vacuum_ovfp_threshold.cpp`).

| 함수 | 파일 | 목적 | 주요 사용처(호출자) |
|---|---|---|---|
| `get_global_monitor` | `monitor_registration.cpp:159` | 전역 `monitor` 인스턴스 반환 | 통계 등록/조회 지점 전반 |
| `monitor::register_statistics` | `monitor_registration.cpp:138` | 이름 붙은 통계 등록(count + fetch_function + names) | 새 통계 추가 지점, `unit_tests/monitor` |
| `monitor::fetch_global_statistics` | `monitor_registration.cpp:103` | 등록된 전체 통계 스냅샷 | 통계 덤프 경로, `unit_tests/monitor/test_monitor_main.cpp:433~` |
| `monitor::fetch_transaction_statistics` / `fetch_statistics` | `monitor_registration.hpp:97/:99` | 트랜잭션 시트/모드 지정 스냅샷 | 트랜잭션별 통계 조회 |
| `monitor::allocate_statistics_buffer` | `monitor_registration.hpp:93` | 등록 통계 수에 맞는 버퍼 할당 | fetch 호출부(`test_monitor_main.cpp:409` 등) |
| `transaction_sheet_manager::start_watch` / `end_watch` | `monitor_transaction.hpp:62/:66` | 현재 트랜잭션 시트 감시 시작/종료 | 트랜잭션별 통계 수집 구간 |
| `transaction_sheet_manager::get_sheet` | `monitor_transaction.hpp:70` | 현재 트랜잭션 시트 조회 | `transaction_statistic<S>` 내부(:201/:230/:262) |
| `counter_timer_statistic` (류) | `monitor_collect.hpp:132` | 카운터+타이머 묶음 통계(autotimer 포함) | `src/base/lockfree_hashmap.hpp:114`(`atomic_counter_timer_stat`) |
| `ovfp_threshold_mgr` | `monitor_vacuum_ovfp_threshold.hpp:112` | VACUUM 오버플로 페이지 임계 감시(서버 전용) | `src/query/vacuum.c:665`(전역 `g_ovfp_threshold_mgr`), `:1259`(init), `:3532~`(수집), `:1168`(dump) |

## 2. 분석 내용 (함수별)

> 항목은 함수 단위로 기술한다 — 각 항목의 제목/선두가 함수·파일명이다. 새 분석도 함수명을 앞세워 추가할 것.
> (아래 주의점·리뷰 체크포인트의 원본: src/monitor/AGENTS.md 증류)

### 모듈 일반

- 빌드 포함이 다름: 코어 파일은 Server·SA 빌드만(CS 빌드 제외 — `cs/CMakeLists.txt`에 없음),
  `monitor_vacuum_ovfp_threshold.*`는 서버 전용(`#if defined(SERVER_MODE)` 가드).
- `statistic_value`(uint64)가 범용 wire 타입. `fetch_mode`는 `FETCH_GLOBAL` 또는
  `FETCH_TRANSACTION_SHEET`.
- 멤버 필드 `m_` 접두사, snake_case.
- ✅ **리뷰 체크포인트**: 서버 전용 코드가 SERVER_MODE 가드/서버 빌드에만 들어가는가?

### monitor::register_statistics (monitor_registration.cpp)

- `fetch_function` 시그니처: `std::function<void(statistic_value*, fetch_mode)>`.
- 새 통계는 통계 객체 생성 후 `register_statistics()`로 등록. 버퍼는
  `allocate_statistics_buffer()`로 크기 맞춰 할당.
- ✅ **리뷰 체크포인트**: 새 통계가 레지스트리에 등록되고 fetch 루프·버퍼 크기와 정합하는가?

### transaction_sheet_manager::start_watch / end_watch (monitor_transaction.cpp)

- ✅ **리뷰 체크포인트**: 트랜잭션별 통계가 `start_watch()`/`end_watch()` 시트 수명주기를 따르는가?

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
