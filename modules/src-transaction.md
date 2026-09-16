# src/transaction

> 기준: upstream/develop 95b79e7ed (2026-08-27)

## 1. 소스 목적 및 사용처 (함수별)

MVCC, WAL, 락, 리커버리, 부트를 담당하는 서버 측 최대 모듈. 핵심 파일: `lock_manager.c`(락 획득·
에스컬레이션·데드락, ~15K+)와 `wait_for_graph.c`, `mvcc.c`, `log_manager.c`/`log_append.cpp`(WAL),
`log_recovery.c`(ARIES, ~15K+), `log_page_buffer.c`(로그 페이지 I/O·체크포인트), `boot_sr.c`/`boot_cl.c`,
`log_tran_table.c`(트랜잭션 테이블), `transaction_sr.c`/`transaction_cl.c`(commit/abort/savepoint).

| 함수 | 파일 | 목적 | 주요 사용처(호출자) |
|---|---|---|---|
| `lock_object` | `lock_manager.c:6253` | 오브젝트(행/클래스) 락 획득 공개 진입점 | `src/query/query_executor.c`, `src/query/scan_manager.c`, `src/storage/btree.c` |
| `lock_internal_perform_lock_object` | `lock_manager.c:3497` | 락 획득 내부 구현(대기·충돌 처리) | `lock_object` 계열 내부 |
| `lock_unlock_all` | `lock_manager.c:7377` | 트랜잭션의 전체 락 해제 | `log_manager.c`(커밋/어보트 완료 경로, :5266/:5294/:5348 등) |
| `mvcc_satisfies_snapshot` | `mvcc.c:156` | 스냅샷 대비 레코드 가시성 판정 | `snapshot_fnc`로 등록: `mvcc_table.cpp:332`, `src/storage/btree.c:17735` |
| `log_append_undoredo_data` | `log_manager.c:1933` | undo+redo WAL 레코드 기록 | `src/storage/btree.c`, `file_manager.c`, `disk_manager.c`, `src/query/vacuum.c` |
| `log_append_undo_data` / `log_append_redo_data` | `log_manager.c:2013` / `:2075` | undo 전용 / redo 전용 WAL 레코드 기록 | 저장 계층 전반(heap/btree/file) |
| `log_commit` / `log_abort` | `log_manager.c:5392` / `:5501` | 커밋/어보트의 로그 측 처리 | `xtran_server_commit`/`xtran_server_abort` |
| `xtran_server_commit` / `xtran_server_abort` | `transaction_sr.c:71` / `:127` | 서버 측 커밋/어보트 진입점 | `network_interface_sr.cpp:168`(stran_* 핸들러), `src/loaddb/load_session.cpp` |
| `tran_commit` / `tran_abort` | `transaction_cl.c:272` / `:417` | 클라이언트 측 트랜잭션 종료 | `src/compat/db_admin.c`, `src/query/execute_statement.c` |
| `logtb_assign_tran_index` | `log_tran_table.c:816` | 트랜잭션 테이블 슬롯 할당 | `src/loaddb/load_session.cpp`, `src/query/dblink_2pc_daemon.c` |
| `logtb_get_current_mvccid` | `log_tran_table.c:4125` | 현재 트랜잭션의 MVCCID 획득(없으면 할당) | MVCC 삽입/삭제 경로(heap 등); 조회 전용은 `logtb_find_current_mvccid`(:4022) |
| `logpb_checkpoint` | `log_page_buffer.c:6901` | 체크포인트 수행 | `log_manager.c`(:1857, :3841 등 체크포인트 트리거), `boot_sr.c:5140` |
| `log_recovery` | `log_recovery.c:746` | ARIES 리커버리(analysis→redo→undo) | `log_manager.c:1400`(log_initialize 경로) |
| `boot_restart_server` | `boot_sr.c:1974` | 서버 부트/재시작 시퀀스 | `src/communication/network_sr.c`(net_server_start 경로) |

## 2. 분석 내용 (함수별)

> 항목은 함수 단위로 기술한다 — 각 항목의 제목/선두가 함수·파일명이다. 새 분석도 함수명을 앞세워 추가할 것.
> (아래 주의점·리뷰 체크포인트의 원본: src/transaction/AGENTS.md 증류)

### 모듈 일반

- `THREAD_ENTRY *thread_p`가 모든 함수의 첫 파라미터.
- vacuum은 데몬으로 동시 실행 — 활성 트랜잭션과의 경쟁을 처리해야 함. vacuum 코드는 이 디렉터리가
  아니라 `src/query/vacuum.c`에 있다.
- ✅ **리뷰 체크포인트**: vacuum 데몬과 동시 실행되는 경로에서 경쟁 조건을 고려했는가?

### lock_object (lock_manager.c)

- 락 계층: Database → Table (SCH-S/SCH-M/IX/IS/S/X) → Row (S/X). 행 락 전에 테이블 인텐트 락(IX/IS).
  다수 행 락은 테이블 락으로 에스컬레이션.
- ✅ **리뷰 체크포인트**: 행 락 획득 전 상위 인텐트 락이 잡히는가? 데드락 그래프에 새 대기 관계가 반영되는가?

### mvcc_satisfies_snapshot (mvcc.c)

- MVCC ID는 64비트 단조 증가 — **절대 재사용되지 않는다**. `tran_index`는 활성 트랜잭션 식별자이지
  MVCC ID가 아니다 — 혼동 금지.
- ✅ **리뷰 체크포인트**: MVCC ID와 `tran_index`를 혼용하지 않는가? 스냅샷 가시성 판단이 `mvcc_satisfies_snapshot()` 경유인가?

### log_append_undoredo_data / log_append_undo_data / log_append_redo_data (log_manager.c)

- WAL 규칙: 데이터 페이지 플러시 전에 로그 레코드가 먼저 기록돼야 한다. 레코드는 `LOG_LSN`
  (page + offset)으로 식별, 대상은 `LOG_DATA_ADDR`(페이지+오프셋).
- ✅ **리뷰 체크포인트**: 페이지 수정 로그가 페이지 플러시보다 먼저 기록되는가(WAL 순서)?

### log_recovery (log_recovery.c)

- 리커버리는 CLR(보상 레코드)로 중첩 리커버리 시 반복 undo를 방지. 부분 기록된 로그 페이지
  (torn write)를 처리해야 한다.
- ✅ **리뷰 체크포인트**: 새/변경 로그 레코드에 대응하는 redo/undo(및 필요 시 CLR) 처리가 `log_recovery.c`에 있는가?

### boot_restart_server (boot_sr.c)

- 부트 시퀀스는 서브시스템 초기화 순서가 엄격 — 순서 변경 주의.
- ✅ **리뷰 체크포인트**: 부트 순서에 영향을 주는 초기화 변경이 아닌가?

## 3. 예비 이슈 사항

> 미수정 버그·의심·문서 정정 후보·구조적 한계. 해소되면 삭제가 아니라 "해소됨(커밋/PR)"로 갱신.

- **[미수정 버그 — CBRD-27367, .50 2026-09-02]** `tdes->log_upd_stats`(트랜잭션-로컬 unique 통계:
  청크 할당자 + 일반 `MHT_TABLE unique_stats_hash`, log_tran_table.c)는 **단일 스레드 트랜잭션
  전제**로 무동기화 설계인데, 병렬 질의(px 워커)가 같은 tran_index를 공유한 채 동시에 접근한다.
  CBRD-27292(상수 출력 스캔의 병렬성 유지)로 `COUNT(*) UNION ALL` 각 팔이 px 워커에서 돌게 되며
  발화. **3 발현형 전부 실측**(재현: cubrid-testcases `sql/_36_guava/cbrd_26571`, Case 13/14):
  ① SEGV(`logtb_tran_create_btid_unique_stats` :3506, `BTID_COPY`) — 두 스레드가
  `qexec_evaluate_aggregates_optimize`(query_executor.c:26967/26976)의 두 경로(COUNT(*) 최적화 직행 /
  `logtb_get_mvcc_snapshot→build_mvcc_info→logtb_load_global_statistics_to_tran` 경유)로 동시 진입.
  ② COUNT(*) 응답이 **-1** — 신규 엔트리 초기화값(:3515~, `global_stats.num_*=-1`)이 레이스로 채워지지
  않고 그대로 노출. ③ 커밋 무한 행 — 동시 `mht_put`이 버킷 체인을 원형으로 오염,
  `logtb_tran_clear_update_stats`(:3416)의 `mht_clear`(memory_hash.c:1279)가 영원히 안 끝남.
  귀속: 순수 develop@45aa81034(CBRD-27292 직후, 다른 커밋 0개) debug 빌드에서 1회차부터 행 발화 —
  **develop 결함**, PR#7658 무관. CBRD-27183(tdes->wait_msecs)·CBRD-27308(find_nth 캐시)과 같은
  "px 워커 간 TDES 공유 상태 무동기화" 계열. 코어 수가 많을수록 발화율 상승(64코어 debug 4회 중
  3회) — CI(코어 적음)에서는 드물게 발화하므로 **어느 PR CI에서 실패해도 그 PR 원인이 아닐 수
  있다**. 수정 방향 후보: px 워커별 THREAD 스코프 로컬 수집 후 부모로 병합(27183/27308과 동일 패턴).

## 4. 진행중인 작업

> 각 컨테이너가 자기 소절을 직접 관리한다. 완료되면 지우지 말고 "완료(PR/커밋)"로 갱신.

### .50
- (해당 없음 또는 미기입)

### .51
- (해당 없음 또는 미기입)

### .52
- (해당 없음 또는 미기입)
