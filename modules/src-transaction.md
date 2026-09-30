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

### 로그 매니저 전체 — vimkim 들여옴 (imports/vimkim/transaction/log-manager-*.md, 기준 4cfc8370e)

- append 경로는 **워커가 `prior_lsa_mutex` 아래 prior list(메모리 목록)에 노드를 달고 → LOG_CS 에서 로그 페이지 버퍼로 드레인 → `fileio_write`+fsync → 활성 로그(_lgat, 링) → 아카이브** 순이며,
  그룹 커밋은 로그 플러시 데몬(LFT) 의 브로드캐스트다. 16장 구성(LSA 좌표계, 온디스크 구조, 레코드 종류, 체크포인트, 아카이브 삭제 정책, 복구 analysis→redo→undo, Vacuum/HA/CDC 소비자,
  파라미터, 파일 지도)은 `log-manager-overview_4cfc837.md`; printf 트레이스 8곳 실측과 **정적 문서 정정 사항(§6)** 은 `log-manager-append-flush-dynamic-analysis_4cfc837.md`.
  WAL 을 만지는 리뷰는 overview §5(append)·§6(페이지 버퍼/flush)·§8(데이터 버퍼 연동)부터. — vimkim(원문 imports/vimkim/transaction/) 2026-09-30

### log_Gl.hdr.append_lsa — whole-word atomic (CBRD-27320, #7875 `b319ce1ab`)

- **해소된 경합의 기록**: 이전엔 `logpb_next_append_page` 가 `append_lsa.pageid++` / `.offset = 0` 두 store 로 페이지를 넘겼고, 락 없이 읽는 `log_get_undo_record`
  (`oldest_prior_lsa = *log_get_append_lsa()`) 가 최적화 빌드에서 pageid·offset 을 두 load 로 읽어 `(옛 P, 새 페이지의 어린 offset)` 이라는 존재한 적 없는 주소를 조합 → `LSA_LT` 거짓 → assert.
  40 스레드 JDBC 갱신·조회(`bug_bts_4633`) optdebug 에서 재현, release 는 찢어진 값이 조용히 판단에 쓰였다(2016년 `63378ed15c` 부터 잠복). 현행 develop 은 `log_Gl.hdr.append_lsa.load()/.store(LOG_LSA(...))`
  (log_page_buffer.c) 로 한 워드 atomic. 해설은 `imports/vimkim/transaction/CBRD-27400-append-lsa-torn-read_a590292.md` (PR#7904 는 27320 에 흡수되어 close). — vimkim 2026-09-30; .51 대조 0d0809963
  - ✅ **리뷰 체크포인트**: 두 필드로 된 LSA/좌표를 락 없이 읽는 곳이 새로 생기면 "쓰는 쪽이 두 store 인가" 를 본다 — x86 store 순서만으로는 못 막는다.

### 체크포인트는 DWB 가 꺼져 있어도 데이터 볼륨을 fsync 해야 한다 (CBRD-27093, 해소 `60f3b5a96` #7521)

- 체크포인트 계약은 "chkpt_lsa 이전 변경은 전부 **디스크에** 있다 → 그 이전 아카이브를 버려도 된다" 다. DWB(기본 on)가 볼륨 fsync 를 대신하던 구조라 `double_write_buffer_size=0` 이면
  flush(OS 페이지 캐시) 만 하고 sync 없이 chkpt_lsa 를 전진·아카이브를 삭제해 **정전 시 커밋 데이터가 조용히 유실**될 수 있었다(10.2~11.4 전부). 프로세스 crash 만으로는 안 보이고 OS crash 에서만 드러나
  오래 잠복. 배경·시나리오·수정 설계는 `imports/vimkim/transaction/CBRD-27093-*.md`. 11.0/11.3/11.4 백포트 머지. — vimkim 2026-09-30; .51 대조 git log
  - ✅ **리뷰 체크포인트**: 내구성 경로(체크포인트·백업·복구)를 만지면 "DWB off" 조합을 따로 본다 — DWB 가 fsync 를 숨긴다.

### log_sysop_start / log_sysop_commit / log_sysop_abort (log_manager.c)

- TDES 의 topops 스택으로 중첩되는 시스템 오퍼레이션. abort 는 그 sysop 안의 로그만 undo 하고(부분 실패가 상위 트랜잭션을 깨지 않는 이유), commit 은 상위에 흡수되거나 `LOG_SYSOP_END` 로 독립 커밋.
  crash 안전성·비용·다른 DBMS 의 대응 개념은 `imports/vimkim/transaction/sysop-explained_977cf18a4.md` §1~§10 (§6·§11·§12 의 예시는 feat/oos). `log_sysop_start` (:3667) 는 디스크 I/O·WAL 레코드 없이
  `tdes->topops.stack[last].lastparent_lsa = tail_lsa` 만 밀어 넣고(O(1), `lock_topop` 1회), 종료는 `LOG_SYSOP_END` 한 종류에 `LOG_SYSOP_END_TYPE` 이 `COMMIT / ABORT / LOGICAL_UNDO / LOGICAL_COMPENSATE / LOGICAL_RUN_POSTPONE`
  (log_record.hpp:67~, 진입 `log_sysop_commit` :3984, `log_sysop_end_logical_undo` :4009, `_compensate` :4052, `_run_postpone` :4071). — vimkim 2026-09-30; .51 대조 develop 0d0809963

### lock_manager.c — end-to-end 추적 패킷 (imports/vimkim/transaction/lock-manager-*.md, 기준 f30f1c260)

- 자원·모드·계층·변환·에스컬레이션 / 대기·데드락·타임아웃·기상·해제·재시작 / MVCC SELECT·FOR UPDATE·DML 의 클래스-행 정책 / **MVCCID X self-lock 과 unique·FK 의 S wait→recheck** 네 추적과
  claim 후보·negative search·안 한 실험 목록. 서버측 loaddb 의 `BU_LOCK` 과 트랜잭션 MVCCID self-lock 은 자원·소유자가 다른 두 락이라는 정리는 `imports/vimkim/loaddb/CBRD-27157-*.md`
  (수정 PR#7588 은 feat/oos 에만). lock 을 건드리는 리뷰는 위 `lock_object` 항목 다음에 이 패킷의 trace 2·4 를 연다. — vimkim 2026-09-30
- **락 자원 종류는 넷이다 — `LOCK_RESOURCE_INSTANCE / CLASS / ROOT_CLASS / TRANSACTION`** (lock_manager.h:139-142). `TRANSACTION` 은 **inserter 의 MVCCID 를 키로 하는 self-lock**: 트랜잭션이 자기 MVCCID 에 X 를 잡고
  (`lock_transaction_mvccid` :6468, 키 `lock_create_mvccid_search_key` :739, 해제 `lock_unlock_transaction_mvccid` :6521, 조회 `lock_has_lock_on_transaction_mvccid` :6584), MVCC INSERT 가 새 행마다 row X 를 잡는 대신 이 X 로
  `INSERT_IN_PROGRESS` 수명을 대표한다. unique/FK 검사에서 그 MVCCID 를 만난 다른 트랜잭션은 같은 자원에 S 를 요청해(X 와 비호환) commit/abort/서브트랜잭션 완료까지 기다린 뒤 **인덱스를 root 부터 다시 탐색**한다.
  class hierarchy·escalation 은 이 자원에 적용되지 않는다. (원문 C030~C037 요지; 자원 종류·API 는 .51 대조, btree 쪽 wait/recheck 줄 범위는 미대조) — vimkim(원문 imports/vimkim/transaction/lock-manager-source-trace-packet_f30f1c2.md) 2026-09-30; .51 대조 develop 0d0809963
  - ✅ **리뷰 체크포인트**: "self-lock 을 건너뛴다"(CBRD-27157 류) 는 unique/FK observer 의 대기 상대를 없애는 변경이다 — 그 경로가 정말 unique/FK 검사 대상이 아닌지 먼저 본다.
- **commit 은 로그 flush 를 기다리고 abort 는 기다리지 않는다; ABORT 레코드는 후속 flush 에 편승하고, 그룹 커밋의 fsync 병합은 ≈1s 지연 특성을 가진다** — vimkim 의 printf 트레이스 실측(4cfc8370e, CS 모드, debug). `imports/vimkim/transaction/log-manager-append-flush-dynamic-analysis_4cfc837.md` §5~§6. 수치는 원문 조건 한정. — vimkim 2026-09-30

### heap_get_visible_version_from_log — 구버전 읽기 경로 개선 제안 (미계측 초안)

- 스냅샷보다 새 버전을 만나면 `prev_version_lsa` 를 따라 undo 로그에서 옛 버전을 읽는 경로의 비용 진단과 제안. **원문 스스로 "계측 선행 필요, 구현 착수 비권장"** 이라 적었다 —
  측정 없이 최적화 제안하지 않는 우리 규칙과 같은 위치. `imports/vimkim/transaction/mvcc-version-read-path-improvement-proposal_f30f1c2.md`. — vimkim 2026-09-30

### CDC × HA failover (log_manager.c CDC 부, 기준 4cfc8370e)

- master → standby → master 전환 뒤 CDC 가 멈추는 원인 후보의 정적 분석 두 판(claude/codex)이 `imports/vimkim/transaction/cdc-ha-*.md`. 재현 로그 없이 쓴 원인 후보라 **미확인** 표기로 둔다. — vimkim 2026-09-30

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
