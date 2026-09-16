# src/loaddb

> 기준: upstream/develop 5f3a30d09 (2026-09-02)

## 1. 소스 목적 및 사용처 (함수별)

bison/flex 문법 기반 대량 적재기. `load_grammar.yy` + `load_lexer.l`(입력 포맷 파싱),
`load_driver.cpp`(오케스트레이션), `load_session.cpp`(배치), `load_worker_manager.cpp`(병렬 워커),
`load_server_loader.cpp`(서버 측 직접 힙/인덱스 삽입), `load_sa_loader.cpp`(SA 모드 클라이언트 로더),
`load_db_value_converter.cpp`(문자열→DB_VALUE), `load_db.c`(유틸 진입점).

| 함수 | 파일 | 목적 | 주요 사용처(호출자) |
|---|---|---|---|
| `loaddb_dba` / `loaddb_user` | `load_db.c:953` / `:966` | `loaddb` 유틸 진입점(DBA/일반) | `src/executables/util_admin.c:989`(`ua_Utility_Map[]` 등록) |
| `ldr_sa_load` | `load_sa_loader.cpp` (`load_sa_loader.hpp:62`) | SA 모드 적재 본체 | `load_db.c`(SA 경로) |
| `cubload::driver::parse` | `load_driver.cpp:85` | 입력 스트림 파싱 구동(lexer+grammar) | 서버 로더·SA 로더의 배치 파싱 |
| `cubload::session::install_class` | `load_session.cpp:541` | `%class` 배치 처리(대상 클래스 설치) | `sloaddb_install_class`(`network_interface_sr.cpp:10866`) |
| `cubload::session::load_batch` | `load_session.cpp:582` | 데이터 배치 적재(워커에 태스크 분배) | `sloaddb_load_batch`(`network_interface_sr.cpp:10922`) |
| `cubload::worker_manager_try_task` | `load_worker_manager.cpp` (`load_worker_manager.hpp:38`) | 로드 태스크를 워커 풀에 제출 | `load_session.cpp` |
| `cubload::worker_manager_register_session` / `_unregister_session` | `load_worker_manager.cpp` (`load_worker_manager.hpp:41-42`) | 세션의 워커 풀 등록/해제 | `load_session.cpp` 세션 수명주기 |
| `cubload::server_object_loader::process_line` | `load_server_loader.cpp:633` | 파싱된 한 행을 힙/인덱스에 직접 삽입 | grammar 액션 → 로더 콜백 |
| `cubload::get_conv_func` | `load_db_value_converter.cpp:195` | (ldr_type, DB_TYPE)별 문자열→DB_VALUE 변환 함수 선택 | `load_server_loader.cpp:906/:948`, SA 로더 |
| `ldr_update_statistics` | `load_sa_loader.cpp:6654` | SA 적재 마지막 커밋 뒤 로드된 클래스마다 통계 갱신 (CBRD-26230 이후 `do_update_class_statistics()` — 통계+히스토그램) | `ldr_sa_load` 종료부(:6545), 성공 시 caller 가 커밋 |
| `loaddb_update_stats` | `src/communication/network_interface_cl.c:11114` | CS 적재 후: 서버(`sloaddb_update_stats`)가 준 로드 클래스 OID 목록마다 통계 갱신 (CBRD-26230 이후 `do_update_class_statistics()`) | `ldr_server_load`(`load_db.c:1471`) |
| `do_update_class_statistics` | `src/query/execute_schema.c` (helper 바로 뒤) | **한 클래스의 통계+히스토그램을 단일 힙 스캔으로 갱신하는 공용 진입점** — `UPDATE STATISTICS ON t`(`do_update_stats`)·loaddb SA·loaddb CS 가 공유. `no_histogram`/히스토그램 불가(`ER_OBJ_INVALID_ARGUMENTS`)면 `sm_update_statistics` 폴백 | PR#7855(.52, 7df4dbc1a) — develop 미머지 |
| `sloaddb_init` 등 서버 핸들러 | `src/communication/network_interface_sr.cpp:10842~` | CS 모드 loaddb 네트워크 요청 처리(`sloaddb_install_class`/`_load_batch`/`_fetch_status`/`_destroy`/`_interrupt`/`_update_stats`) | `net_Requests[]` 디스패치 |

## 2. 분석 내용 (함수별)

> 항목은 함수 단위로 기술한다 — 각 항목의 제목/선두가 함수·파일명이다. 새 분석도 함수명을 앞세워 추가할 것.
> (아래 주의점·리뷰 체크포인트의 원본: src/loaddb/AGENTS.md 증류)

### 모듈 일반

- 두 모드: SA_MODE(직접 파일 접근, 단일 프로세스) vs CS_MODE(네트워크 전송, 병렬 워커).
- 유닛 테스트 `LOADDB` 모듈은 컴파일 문제로 비활성.
- 접두사 `load_`/`ldr_`, C++는 `cubload` 네임스페이스. 행은 배치로 모아 벌크 삽입.
- ✅ **리뷰 체크포인트**: SA와 CS 두 경로 모두에서 동작이 검증됐는가?

### server_object_loader::process_line (load_server_loader.cpp)

- 서버 측 로더는 일반 INSERT 경로를 **우회**하고 힙/인덱스를 직접 조작한다.
- ✅ **리뷰 체크포인트**: 서버 측 직접 삽입 경로가 인덱스/힙 일관성(일반 INSERT가 보장하던 것)을 유지하는가?

### driver::parse (load_driver.cpp) / load_grammar.yy

- `load_grammar.yy` 수정은 bison 재생성 필요.
- ✅ **리뷰 체크포인트**: 문법 변경 시 bison 재생성 산출물까지 반영됐는가?

### session::load_batch / worker_manager_* (load_session.cpp, load_worker_manager.cpp)

- ✅ **리뷰 체크포인트**: 병렬 워커 수 관련 변경이 배치 처리와 정합하는가?

### ldr_update_statistics / loaddb_update_stats — 적재 후 통계 갱신 경로 (.52, develop 5f3a30d09 기준)

- **develop 은 loaddb 적재 후 클래스 통계만 갱신하고 히스토그램은 만들지 않는다** — SA `sm_update_statistics(class, STATS_WITH_SAMPLING)`,
  CS `stats_update_statistics(classop, STATS_WITH_SAMPLING)`. `UPDATE STATISTICS ON t`/`ON ALL CLASSES`/`optimizedb`(전체)는 모두
  히스토그램을 함께 만든다. `unloaddb` 는 `_db_histogram` 을 덤프 대상에서 제외(`unload_object.c:142`)하므로 이관 직후 DB 는 히스토그램 0개.
  → CBRD-26230(.52) 에서 두 경로를 `do_update_class_statistics()` 로 통일 + `--no-histogram` 추가 (develop 미머지 상태면 §4 참조).
- **CS 경로는 통계 실패 반환값을 버린다**(develop `network_interface_cl.c` `stats_update_statistics (...)` 반환 미검사) — 통계 실패가 exit status 에
  안 잡힌다. CBRD-26230 에서 전파로 수정.
- **CS 경로의 커밋**: `ldr_server_load` 는 통계 갱신 뒤 명시 커밋이 없고 `db_shutdown()` 은 `commit_on_shutdown`(기본 false)일 때만 커밋한다
  (`boot_cl.c` `tran_is_active_and_has_updated` 분기). 히스토그램은 클라이언트 객체 계층으로 `_db_histogram` 을 쓰므로(`smt_add_histogram`)
  명시 커밋이 필요 — CBRD-26230 에서 `db_commit_transaction()` 추가. 실측(.52 2026-09-02): 추가 후 CS 도 SA 와 동일하게 53 행 저장.
- **히스토그램 빌드는 클라이언트 오케스트레이션**이다(사전설계문서 1.2): `update_or_drop_histogram_helper` → `analyze_classes_multi_by_reservoir`
  (서버 sampler 요청 1회) → `sm_update_statistics(obj, fullscan, &ndv)` → `store_collected_histograms`. 서버측 `sloaddb_update_stats` 안에서는
  만들 수 없다 — CS 모드에서도 cub_admin(loaddb) 프로세스가 수행한다.
- **`PRM_ID_UPDATE_STATISTICS_UPDATE_HISTOGRAM`(`update_statistics_update_histogram`)은 `PRM_DEPRECATED` 이고 소비자가 없다** — 새 코드에서 쓰지 말 것.
- ✅ **리뷰 체크포인트**: 적재 후 통계 경로를 바꾸면 SA·CS 두 모드에서 `_db_histogram` 행 수와 플랜 card 를 같이 확인할 것
  (demodb `athlete.gender='M'`: 히스토그램 4087 / NDV 균등 3338 / 통계 없음 0).
- 적재 시간 영향(.52 실측 2026-09-02, 5M행×5컬럼 231MB `loaddb -S`, release): 히스토그램 포함 vs `--no-histogram` 차이는 측정 결과표
  `projects/CBRD-26230/설계문서.md` 참조.

### 동시 DDL/DML 과 CS 적재 후 통계의 락 타이밍 (.52, CBRD-26230 PR#7855 aa6ec813e 기준)

- **CS 적재 후 통계 API 교체가 동시성 테스트의 인터리빙을 바꾼다.** develop 은 `loaddb_update_stats` 에서 경량
  `stats_update_statistics()`(요청만 전송)을 쓰지만, CBRD-26230 은 `do_update_class_statistics()`→`sm_update_statistics()`
  (`locator_flush_all_instances` + 스키마매니저 SCH 락) + 명시적 `db_commit_transaction()` 으로 바꾼다. 적재 후 단계의
  소요·락 타이밍이 달라져, `with_dml_1/2`·`with_ddl_2`(loaddb -C 백그라운드 + 고정 +2초 시점 동시 DML/DDL)에서
  동시 DML 이 develop 에선 데드락 희생자로 abort(답지)되지만 PR 에선 정상 인터리브·커밋된다(999,999행, 서버 err 에
  deadlock/abort 없음, 정합성 정상). **답지가 develop 의 인터리빙을 봉인한 타이밍 의존 테스트**이며 코드 결함이 아니다.
  1M행 로드가 ≈2.6초로 빨라 DML 발사 시점(+2초)이 적재 종료 직전에 걸리는 것이 관건.
- **CS 통계 실패는 best-effort 여야 한다**(aa6ec813e): 통계는 객체·인덱스·트리거 커밋 뒤 부가 작업이므로 실패 시
  `exit_status=3` 로 적재 전체를 실패 처리하면 안 된다(일시적 SCH 락 경합 NOTIFICATION 포함). 로그 + 통계 txn 롤백 후
  계속(SA `ldr_update_statistics` 와 동일). 통계 단계(`ldr_server_load` 끝)는 인덱스/트리거(같은 함수 앞부분) 뒤라 스킵 없음.
- ✅ **리뷰 체크포인트**: loaddb 적재 후 통계 경로를 바꾸면 (1) 동시 DDL/DML 테스트(_35_cherry with_dml/with_ddl)의
  답지가 락 타이밍에 의존함을 인지하고 재기준 판단은 소유자에게, (2) 통계 실패가 적재 exit code 를 오염시키지 않는지 확인.

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
- **CBRD-26230** loaddb 적재 후 통계 갱신에 히스토그램 통합(SA/CS) + `--no-histogram` — **PR#7855** (커밋 7df4dbc1a → 257ed59ae 뷰 제외 게이트 → aa6ec813e CS best-effort). 2026-09-08 CI 실패 53건 전수 분석 완료(뷰가 적재 목록에 들어 sampler → 인덱스 적재 생략; 동시성 3건은 타이밍 답지 이슈). 미결: CI 재실행 확인, 동시성 3건 답지 재기준(TC 소유자), 매뉴얼 PR(cubrid-manual `CBRD-26230` cec6f2b, **로컬만, 미push**), shell TC PR. 세션 01ACsuD7 종료.
