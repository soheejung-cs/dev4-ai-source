# 정소희 — imports/vimkim 에서 아직 develop 과 대조하지 않은 주장 (환류 대기)

작성: 정소희 (.51) · 원문 기준 리비전은 각 파일 머리 · 들여온 날 2026-09-30 · develop 대조 기준 `0d0809963`
상태: **환류 대기** — 항목을 대조해 `modules/<모듈>.md` §2·§3 로 옮기면 여기서 지운다. 전부 **미확인**(원문 주장) 이다.

대조가 끝난 것(D1·D3·D7·P1·P5, CBRD-27400·27093·26176·27151·26500)은 `imports/vimkim/README.md` §2 표와 `modules/src-storage.md`·`src-transaction.md` 에 이미 반영했다.

## pgbuf (원문 `imports/vimkim/pgbuf/defects-report_5cd4f860e.md`, `09-issue-proposals.md`)
- **[storage §3] D2/P7-①** `pgbuf_initialize` 의 `memset(&pgbuf_Pool.direct_victims, 0, sizeof (PGBUF_VICTIM_CANDIDATE_LIST))` — 대상은 24B `PGBUF_DIRECT_VICTIM` 인데 16B 타입 크기 사용 → `waiter_threads_low_priority` 미초기화(static 이라 첫 초기화는 우연히 0). **미확인**
- **[storage §3] D4** `big_private_lrus_with_victims` 큐에 외부 생산자가 없어(유일한 produce 는 consume 후 되넣기) over-quota 스레드의 2단계 victim 탐색이 항상 NULL. **미확인**
- **[storage §3] D5** `double_write_buffer_size=2M` 처럼 크기 접미사를 쓰면 서버 부팅 실패(ER -839), `data_buffer_size=16M` 은 됨 — 비일관. **미확인**
- **[storage §2] D6** 관측 카운터 의미 불일치 4건: DWB 이중 집계, `Num_data_page_flushed` 는 victim flusher 만(체크포인트 0), SHOW 의 `Victim_candidate_pages`(zone3∧dirty) 와 내부 `count_vict_cand`(zone3∧non-dirty) 정의 상충, NEW_PAGE fix 가 `num_hit` 에 집계. **미확인**
- **[storage §3] P4** `pgbuf_dump` 가 atomic-latch 리팩터링 이전 필드(`bufptr->fcnt`, `->zone`)를 참조해 `CUBRID_DEBUG` 빌드 불가. **미확인** (`-DCUBRID_DEBUG` 빌드로 즉시 검증 가능)
- **[storage §3] P6** `pgbuf_rv_dealloc_undo_compensate` 가 미초기화 `VPID vpid` 를 TDE 디버그 로그에 출력. **미확인**
- **[storage §3] P7-②③** `Aout_mutex` 이중 `pthread_mutex_destroy`(init 실패 경로 + finalize), quota 비활성 시 `malloc(0)` 반환값 의존. **미확인**
- **[storage §2] P8** `pgbuf_is_temporary_volume` 이 `LOG_ISRESTARTED()` 이전(복구 중)엔 항상 false → 복구 중 temp 페이지가 temp 특수 처리를 못 받음 — 의도된 보수 동작일 가능성, 주석 필요. **미확인**
- **[storage §2] P9** 죽은 코드: `monitor.victim_rich` 소비처 없음(주석은 재시도 조건으로 설명), `UINT16MAX` 미사용, `buf_LRU_list` 주석의 "garbage LRU" 구획 부재, `goto copy_unflushed_lsa` 가 바로 다음 줄. **미확인**
- **[storage §3] P3 부속** `pgbuf_panic_assign_direct_victims_from_lru` 호출부가 직전에 NULL 이 된 `prev_BCB` 를 넘겨 즉시 0 반환. **미확인**
- **[storage §2]** `pgbuf_claim_bcb_for_fix` 의 `dwb_read_page` 실패 경로가 BCB mutex 를 든 채 반환 (P2 부수). **미확인**

## transaction (원문 `imports/vimkim/transaction/`)
- **[transaction §2]** `sysop-explained` §2~§5 의 TDES topops 스택·`LOG_SYSOP_END` 종류·abort 시 undo 범위 — 함수·줄 대조 필요. **미확인**
- **[transaction §2]** `lock-manager-source-trace-packet` §Claim candidates (자원·모드·에스컬레이션·데드락·MVCCID self-lock·unique/FK S recheck) — 항목별 `lock_manager.c:줄` 대조 필요. **미확인**
- **[transaction §3]** CDC × HA failover 원인 후보(`cdc-ha-*`): master 재승격 후 CDC 세션/로그 위치 복원 경로 — 재현 로그 없는 정적 분석. **미확인**
- **[transaction §2]** 로그 매니저 동적 분석 §6 "정적 문서 대비 정정/보강" 5건 — 현행 develop 에 그대로인지 대조. **미확인**

## storage 기타
- **[storage §2]** 볼륨 파서 문서의 온디스크 프레이밍(`FILEIO_PAGE` 헤더·LSA 워터마크·TDE 가시 범위) — `file_io.h`/`disk_manager.c` 줄 대조. **미확인**
- **[storage §2]** backupdb 조사의 `-t` 스레드 수 cap(`NUM_NORMAL_TRANS`, CPU 수)·temp 볼륨은 시스템 페이지만 백업·SA 는 항상 1스레드 — `util_cs.c`/`file_io.c` 대조. **미확인**
- **[storage §2]** prefetch 조사의 `parallel_heap_scan_page_threshold` 기본 2048, `data_file_os_advise` 1회 hint — 대조. **미확인**
