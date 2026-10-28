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

### logtb_find_current_wait_msecs / logtb_set_thread_wait_msecs (log_tran_table.c:2657/:2631) — 대기 시간 조회 (CBRD-27486 `9699a883c`)

- **락·래치 대기 시간은 "스레드 override 가 있으면 그것, 없으면 `tdes->wait_msecs`" 다** (.52, PR#8034 head `db66b7879` 2026-10-01 → 머지 `9699a883c` 2026-10-06 ·
  develop `2d925cb86` 재확인): override 는 `THREAD_ENTRY::wait_msecs_override`(thread_entry.hpp:266, 기본 `LK_WAIT_NOT_OVERRIDDEN`)이고 `logtb_set_thread_wait_msecs ()`
  가 세우며 이전 값을 돌려줘 복원하게 한다. 락 요청 6경로(lock_manager.c:6340·6499·6721·6861·6955·10302)가 `logtb_find_current_wait_msecs ()` 를 읽고, pgbuf 는 같은
  규칙의 inline 사본 `pgbuf_find_current_wait_msecs ()` 를 읽는다(복제·설치 지점 8곳은 src-storage §2 「스레드 스코프 wait override」). TDES 를 바꾸는
  `xlogtb_reset_wait_msecs ()` 는 override 가 서 있는 스레드에서 부르면 debug assert 다(log_tran_table.c:2566). — 정소희(.50) 2026-10-28
- **TDES 에 일부러 남긴 자리 — 다른 트랜잭션·교착 탐지기·lockdb 가 봐야 하는 값** (.52, 2026-10-01 · develop `2d925cb86` 재확인): 문장 `LOCK_TIMEOUT` 힌트
  (query_executor.c:16955~17094·17840), 온라인 인덱스의 최종 락 승격(`xbtree_load_online_index`, btree_load.c:7576), compactdb(`lock_object_wait_msecs`
  lock_manager.c:6795 — 호출 compactdb_sr.c:566·627, locator_sr.c:11986), lockdb(`xlock_dump` :9029), composite lock 의 대기 시간 스냅샷(`lock_initialize_composite_lock`
  :9132 — 수명이 마무리까지 가서 트랜잭션 값을 쓴다, 머지 커밋 메시지). override 는 워커에 물려지지 않는다(src-thread §2). `lock_object_wait_msecs` 의 인자가 override
  창 안에서 가려지는 잠재 구멍은 §3. — 정소희(.50) 2026-10-28

### lock_select_deadlock_victim / lock_detect_local_deadlock (lock_manager.c:5086/:8221) — 교착 희생자

- **데드락 희생자는 lock timeout 이 유한하면 abort 되지 않는다 — 그 대기만 −966 으로 끝난다** (.51, `959314906`, 2026-10-21~23 · develop `2d925cb86` 재확인):
  `lock_select_deadlock_victim` 은 timeout 가능한 트랜잭션을 먼저 고르고(:5357 "Prefer a transaction with a closer timeout", 같으면 더 젊은 쪽),
  `lock_detect_local_deadlock` 이 `can_timeout` 이면 `lock_wakeup_deadlock_victim_timeout ()`(:2558, `LOCK_RESUMED_DEADLOCK_TIMEOUT` →
  `ER_LK_OBJECT_DL_TIMEOUT_SIMPLE_MSG` −966)로 그 대기만 끝낸다(:8524-8533) — 락은 유지되고 앞선 쓰기는 커밋할 수 있다(문장 단위 실패). 무한(−1)이면
  `lock_wakeup_deadlock_victim_aborted ()`(:2614 → `ER_LK_UNILATERALLY_ABORTED` −72, 트랜잭션 abort). RR 의 −1158(`ER_MVCC_SERIALIZABLE_CONFLICT`)도 문장만
  실패한다. — 정소희(.50) 2026-10-28
  - ✅ **리뷰 체크포인트**: 동시성 재현의 기대값을 "데드락이면 롤백된다" 로 쓰지 않는다 — `lock_timeout` 이 유한하면 희생자 트랜잭션은 살아 있고 이후 문장이 커밋될 수 있다.
- **교착 탐지기는 TDES 만 본다 — override 로 대기 중인 요청의 실제 대기 시간은 보지 않는다** (.52, 2026-10-01 · develop `2d925cb86` 재확인): 희생자 선정의
  `can_timeout` 은 `LK_CAN_TIMEOUT (logtb_find_wait_msecs (t))`(:5249·5325). override 는 페이지 fix 를 감쌀 뿐이라 이것으로 충분하다 — 예외인 `log_rollback` 의
  override 는 두 호출자(`log_sysop_abort` log_manager.c:4143→4147, `log_abort_local` :5360→5371)가 먼저 `tdes->state = TRAN_UNACTIVE_ABORTED` 로 만든 뒤에 서고,
  탐지기는 비활성 트랜잭션을 희생자로 고르지 않는다(`logtb_is_active (…) == false` 를 건너뜀 :5233·5309). 원 메모가 든 세 번째 자리 :8634 는
  `#if 0 /* NOT_USED */` 안의 `lk_global_deadlock_detection` 이다. — 정소희(.50) 2026-10-28

### lock_set_error_for_timeout / lock_describe_resource (lock_manager.c:2130/:2037) — 락 타임아웃 메시지의 자원 표기

- **타임아웃 메시지의 자원 문구는 "자원 종류마다 msgcat 문구 하나 + case 하나" 이고, 클래스 이름을 못 구하면 OID 문구로 떨어진다** (.51, PR#7900 `a910e8e6e` 리뷰
  2026-09-17 · develop `2d925cb86` 재확인): `lock_set_error_for_timeout`(:2130) → `lock_describe_resource`(:2037). `heap_get_class_name` 이 실패하면 `er_clear ()` 후
  `MSGCAT_LK_RES_DESC_OBJECT`(`v|p|slot`)로 떨어지고 타임아웃 에러는 정상 설정된다. `LOCK_RESOURCE_TRANSACTION` 은 inserter MVCCID 를 그대로 찍는다(CBRD-27155
  `64f02ef62`). 함수 머리 주석이 확장 규약을 적는다 — 새 자원 종류는 msgcat 문구 + case 하나, 종류별 타임아웃 에러 코드는 만들지 않는다(ER_IS_LOCK_TIMEOUT_ERROR·
  LA_RETRY_ON_ERROR·qexec_execute_selupd_list 전부에 넣어야 하고 하나라도 빠지면 동작이 조용히 바뀐다). `LK_UNCOND_LOCK` 의 대기 시간은 위 「대기 시간 조회」 규칙.
  — 정소희(.50) 2026-10-28

### lock_dump_resource (lock_manager.c:5612) — lockdb 에 보이는 self-lock 대기

- **미커밋 유니크 키 대기는 lockdb 에 `Transaction self-lock (inserter MVCCID = N)` 자원 + 대기자 `Blocked_mode = S_LOCK` 으로 보인다** (.50, 2026-09-18 동적 ·
  develop `2d925cb86` 재확인): `lock_dump_resource` 의 `LOCK_RESOURCE_TRANSACTION` case(:5748-5750)가 그 줄을 찍고, 대기자는 `btree_wait_for_inserter_end`
  (btree.c:27215)의 S 요청이다. 행 X 대기만 찾으면(`Blocked_mode = X_LOCK` grep) **유니크 삽입 경쟁(예: 첫 통계 수집 경쟁)의 대기를 놓친다** — TC 의 대기 검출을
  그렇게 짰다가 오판했다. — 정소희(.50) 2026-10-28
  - ✅ **리뷰 체크포인트**: 동시성 TC 가 lockdb 로 "대기 중" 을 판정하면 행 X 대기와 self-lock S 대기를 둘 다 본다.

### mvcc_satisfies_snapshot (mvcc.c)

- MVCC ID는 64비트 단조 증가 — **절대 재사용되지 않는다**. `tran_index`는 활성 트랜잭션 식별자이지
  MVCC ID가 아니다 — 혼동 금지.
- ✅ **리뷰 체크포인트**: MVCC ID와 `tran_index`를 혼용하지 않는가? 스냅샷 가시성 판단이 `mvcc_satisfies_snapshot()` 경유인가?

### mvcc_satisfies_committed (mvcc.c:639) — 스냅샷 없는 "마지막 커밋 버전"

- **`mvcc_satisfies_committed` 는 자기 트랜잭션의 미커밋 삽입을 보여 주고, 자기 미커밋 삭제는 숨긴다** (.50, `bc988f0ab` 코드 확인 2026-09-17 · develop `2d925cb86`
  재확인): 첫 분기가 `!MVCC_IS_REC_INSERTED_BY_ME (…) && MVCC_IS_REC_INSERTER_ACTIVE (…)` 일 때만 TOO_NEW 이므로(:643-648) 내가 넣은 미커밋 행은 "committed (or own)
  insert" 로 SNAPSHOT_SATISFIED(:650-657), 내가 지운 행은 TOO_OLD(:659-662), 남이 지우는 중(미커밋)인 행은 아직 마지막 커밋 버전이라 SATISFIED(:664-668).
  `mvcc_satisfies_dirty` 에서 다른 트랜잭션의 미커밋 버전만 뺀 것이고 트랜잭션 스냅샷을 만들지 않는다 — CBRD-27369 `0d0809963` 이 `_db_histogram` 의 컴파일 시점 조회에
  쓰려고 넣었다. 그래서 committed 무잠금 조회를 **존재 확인**에 써도 같은 트랜잭션 안의 재호출이 중복 생성을 하지 않는다(오토커밋 OFF 연속 `UPDATE STATISTICS`).
  현재 계약 — 함수 주석이 "새 트랜잭션이 볼 것" 을 원하는 호출자는 자기 dirty 객체를 스스로 빼라고 적는다. — 정소희(.50) 2026-10-28

### log_append_undoredo_data / log_append_undo_data / log_append_redo_data (log_manager.c)

- WAL 규칙: 데이터 페이지 플러시 전에 로그 레코드가 먼저 기록돼야 한다. 레코드는 `LOG_LSN`
  (page + offset)으로 식별, 대상은 `LOG_DATA_ADDR`(페이지+오프셋).
- ✅ **리뷰 체크포인트**: 페이지 수정 로그가 페이지 플러시보다 먼저 기록되는가(WAL 순서)?

### log_recovery (log_recovery.c)

- 리커버리는 CLR(보상 레코드)로 중첩 리커버리 시 반복 undo를 방지. 부분 기록된 로그 페이지
  (torn write)를 처리해야 한다.
- ✅ **리뷰 체크포인트**: 새/변경 로그 레코드에 대응하는 redo/undo(및 필요 시 CLR) 처리가 `log_recovery.c`에 있는가?

### logpb_compute_page_checksum (log_page_buffer.c:455) / log_recovery_analysis (log_recovery.c:2609) — 로그 페이지 체크섬과 로그 끝

- **로그 페이지 체크섬은 페이지 전체가 아니라 4KB 블록마다 앞뒤 16바이트 표본의 CRC-32 다** (.51, `959314906`, 2026-10-21~23 · develop `2d925cb86` 재확인):
  `logpb_compute_page_checksum` 이 `LOG_PAGESIZE / 4096` 블록마다 첫·끝 16B 를 모아 `crypt_crc32` 한다(:458-488) — 블록 가운데만 바뀐 손상은 체크섬으로 드러나지
  않는다. 복구 analysis 는 활성 로그 페이지의 체크섬 불일치(`logpb_page_check_corruption`, :2782)를 부분 flush 로 보고 그 페이지의 첫 NULL 블록 위치
  (`logpb_page_get_first_null_block_lsa`, :2798·2840)를 로그 끝으로 삼는다. 오프라인 검산 스크립트 `~/dev/tests/mvcc/scripts/logcheck.py`(.51). — 정소희(.50) 2026-10-28

### boot_restart_server (boot_sr.c)

- 부트 시퀀스는 서브시스템 초기화 순서가 엄격 — 순서 변경 주의.
- ✅ **리뷰 체크포인트**: 부트 순서에 영향을 주는 초기화 변경이 아닌가?

### 로그 매니저 전체 — vimkim 들여옴 (imports/vimkim/transaction/log-manager-*.md, 기준 4cfc8370e)

- append 경로는 **워커가 `prior_lsa_mutex` 아래 prior list(메모리 목록)에 노드를 달고 → LOG_CS 에서 로그 페이지 버퍼로 드레인 → `fileio_write`+fsync → 활성 로그(_lgat, 링) → 아카이브** 순이며,
  그룹 커밋은 로그 플러시 데몬(LFT) 의 브로드캐스트다. 16장 구성(LSA 좌표계, 온디스크 구조, 레코드 종류, 체크포인트, 아카이브 삭제 정책, 복구 analysis→redo→undo, Vacuum/HA/CDC 소비자,
  파라미터, 파일 지도)은 `log-manager-overview_4cfc837.md`; printf 트레이스 8곳 실측과 **정적 문서 정정 사항(§6)** 은 `log-manager-append-flush-dynamic-analysis_4cfc837.md`.
  WAL 을 만지는 리뷰는 overview §5(append)·§6(페이지 버퍼/flush)·§8(데이터 버퍼 연동)부터. — vimkim(원문 imports/vimkim/transaction/) 2026-09-30
  - overview §11 체크포인트·§12 아카이브 삭제 정책 develop 대조(`2d925cb86`, 정소희(.50) 2026-10-28): §11 흐름은 그대로이고 줄만 옮겨졌다 — `logpb_checkpoint`
    log_page_buffer.c:7326, `LOG_START_CHKPT` :7413, `pgbuf_flush_checkpoint` :7436, `fileio_synchronize_all` :7443, TR_TABLE_CS + `prior_lsa_mutex` 아래 트랜잭션
    스냅샷 :7468~, `LOG_END_CHKPT` :7599, 볼륨 헤더 `disk_set_checkpoint` :7689(`checkpoint_info.cpp` 는 develop 에도 없다). §12.2 의 "4중 보류" 는 develop
    `logpb_remove_archive_logs_exceed_limit`(:6248)에서 다섯이다 — vacuum(:6275·6285), `cdc_find_lsa_in_progress`(:6289, supplemental_log 블록 밖이라 flashback 스캔도
    막는다), HA 복사(:6305), 시스템 크래시 복구(:6348-6350), 그리고 supplemental_log 일 때 CDC 최소 페이지(:6371)와 **재시작 뒤에도 남는 CDC 보존 아카이브 번호**
    (로그 헤더 `LOG_HDR_CDC_ARV_NUM`, `logpb_get_cdc_arv_num_to_keep` :5270 — CBRD-27179 `69c3094f1`). 같은 보류가 `logpb_remove_archive_logs`(:6513)에도 있다.

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
  crash 안전성·비용은 `imports/vimkim/transaction/sysop-explained_977cf18a4.md` §1~§9 (§6·§11·§12 의 예시는 feat/oos). `log_sysop_start` (:3667) 는 디스크 I/O·WAL 레코드 없이
  `tdes->topops.stack[last].lastparent_lsa = tail_lsa` 만 밀어 넣고(O(1), `lock_topop` 1회), 종료는 `LOG_SYSOP_END` 한 종류에 `LOG_SYSOP_END_TYPE` 이 `COMMIT / ABORT / LOGICAL_UNDO / LOGICAL_COMPENSATE / LOGICAL_RUN_POSTPONE`
  (log_record.hpp:67~, 진입 `log_sysop_commit` :3984, `log_sysop_end_logical_undo` :4009, `_compensate` :4052, `_run_postpone` :4071). — vimkim 2026-09-30; .51 대조 develop 0d0809963

### lock_manager.c — end-to-end 추적 패킷 (imports/vimkim/transaction/lock-manager-*.md, 기준 f30f1c260)

- 자원·모드·계층·변환·에스컬레이션 / 대기·데드락·타임아웃·기상·해제·재시작 / MVCC SELECT·FOR UPDATE·DML 의 클래스-행 정책 / **MVCCID X self-lock 과 unique·FK 의 S wait→recheck** 네 추적과
  claim 후보·negative search·안 한 실험 목록. 서버측 loaddb 의 `BU_LOCK` 과 트랜잭션 MVCCID self-lock 은 자원·소유자가 다른 두 락이라는 정리는 `imports/vimkim/loaddb/CBRD-27157-*.md`
  (수정 PR#7588 은 feat/oos 에만). lock 을 건드리는 리뷰는 위 `lock_object` 항목 다음에 이 패킷의 trace 2·4 를 연다. — vimkim 2026-09-30
- **락 자원 종류는 넷이다 — `LOCK_RESOURCE_INSTANCE / CLASS / ROOT_CLASS / TRANSACTION`** (lock_manager.h:139-142). `TRANSACTION` 은 **inserter 의 MVCCID 를 키로 하는 self-lock**: 트랜잭션이 자기 MVCCID 에 X 를 잡고
  (`lock_transaction_mvccid` :6468, 키 `lock_create_mvccid_search_key` :739, 해제 `lock_unlock_transaction_mvccid` :6521, 조회 `lock_has_lock_on_transaction_mvccid` :6584), MVCC INSERT 가 새 행마다 row X 를 잡는 대신 이 X 로
  `INSERT_IN_PROGRESS` 수명을 대표한다. unique/FK 검사에서 그 MVCCID 를 만난 다른 트랜잭션은 같은 자원에 S 를 요청해(X 와 비호환) commit/abort/서브트랜잭션 완료까지 기다린 뒤 **인덱스를 root 부터 다시 탐색**한다.
  class hierarchy·escalation 은 이 자원에 적용되지 않는다. **도입: CBRD-26942 #7266 `741734a8f`(2026-07-25)** — 그 전엔 INSERT 가 새 행마다 row X 를 잡았고(MVCC 와 중복, 고정 크기 락 해시맵 체인을 늘려 전 트랜잭션을 느리게 함; 재현 미커밋 INSERT 600만 = X 600만),
  unique/FK 대기는 행 OID 의 X 에 S 를 거는 식이었다. 폐기 enum `LOCK_RESOURCE_OBJECT` 자리를 이 타입이 대체. inserter X 는 `log_tran_table.c:4086`, observer S 는 `btree.c:27365`. (원문 C030~C037 요지; 자원 종류·API 는 .51 대조, btree 쪽 wait/recheck 줄 범위는 아래 하위 항목에서 대조) — vimkim(원문 imports/vimkim/transaction/lock-manager-source-trace-packet_f30f1c2.md) 2026-09-30; .51 대조 develop 0d0809963
  - btree·heap 쪽 줄 대조(원문 C031~C038, develop `2d925cb86`): unique 검사는 `btree_key_wait_for_insert_mvccid`(btree.c:27259)가 잡아 둔 객체 락과 leaf/overflow
    래치를 먼저 놓고 `btree_wait_for_inserter_end`(:27215 — inserter MVCCID self-lock 에 S 를 걸었다 바로 푼다)로 기다린 뒤 `*restart = true` 로 **root 부터 다시
    읽게** 한다. FK 는 `btree_fk_object_does_exist`(:30428)가 같은 대기 함수를 부른다(:30477). heap 쪽은 `heap_get_insert_location_with_lock`(heap_file.c:21416)이
    MVCC 클래스면 새 행 row X 대신 `logtb_ensure_mvccid_self_lock`((서브)트랜잭션당 한 번, :21611-21625)을 잡는다. 원문의 줄 범위(btree.c 23679~24013·6362~,
    heap 20524~)는 f30f1c260 기준이라 지금과 다르다. — vimkim(원문 같은 패킷) · 정소희(.50) develop 대조 2026-10-28
  - 카탈로그 디렉터리 합성 OID 의 표기 (.51, PR#7900 리뷰 2026-09-16 · develop `2d925cb86` 재확인): 카탈로그 접근은 bit 15(`VIRTUAL_CLASS_DIR_OID_MASK`, oid.h:37)
    합성 OID 에 락을 걸고, 락 매니저가 `OID_IS_VIRTUAL_CLASS_OF_DIR_OID ()` 로 알아봐 lockdb 덤프(`lock_dump_resource`, lock_manager.c:5648·5682)·이벤트 로그
    (`lock_event_log_lock_info` :10158·10185)·타임아웃 문구(`lock_describe_resource` :2081)에서 실제 클래스로 풀어 표시한다(msg 15~18·43·45) — 합성 OID 자원을 lockdb
    에 이름 붙이는 선례. 영구 페이지 래치를 쥔 채 락 대기(`lock_suspend`)에 들어가도 되는 것도 이 합성 OID 락뿐이다(:2331 assert,
    `lock_is_safe_lock_with_page` :10318). — 정소희(.50) 2026-10-28
  - ✅ **리뷰 체크포인트**: "self-lock 을 건너뛴다"(CBRD-27157 류) 는 unique/FK observer 의 대기 상대를 없애는 변경이다 — 그 경로가 정말 unique/FK 검사 대상이 아닌지 먼저 본다.
- **commit 은 로그 flush 를 기다리고 abort 는 기다리지 않는다; ABORT 레코드는 후속 flush 에 편승하고, 그룹 커밋의 fsync 병합은 ≈1s 지연 특성을 가진다** — vimkim 의 printf 트레이스 실측(4cfc8370e, CS 모드, debug). `imports/vimkim/transaction/log-manager-append-flush-dynamic-analysis_4cfc837.md` §5~§6. 수치는 원문 조건 한정. — vimkim 2026-09-30

### locator_lock / locator_can_skip_fetch_from_server (locator_cl.c:602/:6739) — 클라이언트의 fetch 버전 강제

- **클라이언트 `locator_lock` 은 MOP 에 이미 락이 있으면 호출자의 fetch 버전을 덮어쓴다 — 인스턴스는 DIRTY, 클래스는 CURRENT** (.51, PR#7900 리뷰 2026-09-09·
  `a910e8e6e` 2026-09-17 · develop `2d925cb86` 재확인): locator_cl.c:667-677. 락 결정은 `locator_fetch_mode_to_lock (DB_FETCH_READ, LC_INSTANCE, *)` 가 DIRTY 일 때만
  S_LOCK, 그 밖(MVCC·COMMITTED)은 NULL_LOCK(:2057~). NULL_LOCK 요청은 `locator_can_skip_fetch_from_server`(:6739)가 `ws_is_mop_fetched_with_current_snapshot` 으로
  재fetch 를 정하는데(:6767), 워크스페이스 스냅샷 버전은 RC 에서만 문장마다(`db_invalidate_mvcc_snapshot_before_statement`, db_vdb.c:5531), 그리고 commit·abort 때
  (transaction_cl.c:373·499) 오른다. fetch 가 성공하면 `locator_cache_have_object` 가 fetch 타입과 무관하게 `ws_set_mop_fetched_with_current_snapshot` 을 찍으므로
  (:3689) 같은 스냅샷 버전 안의 NULL_LOCK 재요청은 서버에 가지 않는다. 서버 `xlocator_fetch` 는 초기 버전 타입이 MVCC **또는 COMMITTED** 면 "NULL_LOCK 인스턴스
  fetch 는 락 보유 필수" 디버그 assert 를 건너뛴다(locator_sr.c:2406-2411, COMMITTED 는 CBRD-27369 `0d0809963` 에서 추가). — 정소희(.50) 2026-10-28
  - ✅ **리뷰 체크포인트**: 클라이언트에서 커밋 버전 읽기를 fetch 버전으로 요청해도 그 MOP 에 락이 이미 있으면 DIRTY 로 바뀐다 — 같은 트랜잭션이 앞에서 그 객체를
    잠갔는지 먼저 본다.

### heap_get_visible_version_from_log — 구버전 읽기 경로 개선 제안 (미계측 초안)

- 스냅샷보다 새 버전을 만나면 `prev_version_lsa` 를 따라 undo 로그에서 옛 버전을 읽는 경로의 비용 진단과 제안. **원문 스스로 "계측 선행 필요, 구현 착수 비권장"** 이라 적었다 —
  측정 없이 최적화 제안하지 않는 우리 규칙과 같은 위치. `imports/vimkim/transaction/mvcc-version-read-path-improvement-proposal_f30f1c2.md`. — vimkim 2026-09-30

### CDC × HA failover (log_manager.c CDC 부, 기준 4cfc8370e)

- master → standby → master 전환 뒤 CDC 가 멈추는 원인 후보의 정적 분석 두 판(claude/codex)이 `imports/vimkim/transaction/cdc-ha-*.md`. 재현 로그 없이 쓴 원인 후보라 **미확인** 표기로 둔다. — vimkim 2026-09-30
  - 상태(정소희(.50) 2026-10-28): master 재승격 뒤 CDC 세션·로그 위치 복원 경로라는 원인 후보는 여전히 **미확인(재확인 못 함)** — 재현 로그가 없다. 그 사이 develop 에
    CDC 가 넘겨받은 아카이브를 재시작 뒤에도 지키는 CBRD-27179 `69c3094f1` 이 들어왔다(위 「로그 매니저 전체」 §12 대조) — 원인 후보와의 관계는 미대조.

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
- **[미수정 — FK `ON DELETE CASCADE`·`ON DELETE SET NULL`·`ON UPDATE SET NULL` 은 삭제(갱신)하는 트랜잭션의 스냅샷에 보이는 자식만 처리한다 → 부모 없는 자식 행]**
  (.51, `959314906`, 2026-10-21 · develop `2d925cb86` 재확인 2026-10-28): `locator_check_primary_key_delete ()`(locator_sr.c:4207)는 RESTRICT/NO ACTION 이면
  `btree_find_foreign_key ()` 로 최신 상태를 보지만(:4251), CASCADE/SET NULL 은 `scan_init_index_scan (…, mvcc_snapshot)` + `btree_range_scan (…,
  btree_range_scan_select_visible_oids)` 로 자식 OID 를 모은다(:4313·4349). `locator_check_primary_key_update ()`(:4572)도 같은 구조다(:4678·4712). 재현: A 가 자식
  INSERT(미커밋) → B 가 부모 DELETE(대기) → A commit → B 성공, 자식이 남는다(RC·RR 모두, 파티션 자식도). CBRD-27464 PR#8026(2팀) 열림 — update 경로 포함.
  — 정소희(.50) 2026-10-28
- **[미수정(잠재) — `lock_object_wait_msecs` 의 인자는 스레드 override 창 안에서 가려진다]** (.52, PR#8034 리뷰 2026-10-01 · develop `2d925cb86` 재확인 2026-10-28):
  `lock_object_wait_msecs`(lock_manager.c:6795)는 인자를 TDES 에 잠시 넣고(:6802 `xlogtb_reset_wait_msecs`) 락을 요청하는데, 락 경로는 override 를 먼저 읽으므로
  override 창 안에서 불리면 인자가 무시된다. 지금은 호출자(compactdb_sr.c:566·627, locator_sr.c:11986)가 모두 창 밖이라 도달 경로가 없고, debug 는
  `xlogtb_reset_wait_msecs` 의 override 부재 assert(log_tran_table.c:2566, `9699a883c`)가 잡는다 — release 에서는 조용히 가려진다. §2 「대기 시간 조회」.
  — 정소희(.50) 2026-10-28

## 4. 진행중인 작업

> 각 컨테이너가 자기 소절을 직접 관리한다. 완료되면 지우지 말고 "완료(PR/커밋)"로 갱신.

### .50
- (해당 없음 또는 미기입)

### .51
- (해당 없음 또는 미기입)

### .52
- (해당 없음 또는 미기입)
