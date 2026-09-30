# 정소희 — imports/vimkim 에서 아직 develop 과 대조하지 않은 주장 (환류 대기)

작성: 정소희 (.51) · 들여온 날 2026-09-30 · develop 대조 기준 `0d0809963`. 상태: **환류 대기** — 대조해 모듈로 옮기면 여기서 지운다. 전부 **미확인**(원문 주장).
1차 대조 완료분(D1~D7·P1~P9 대부분, sysop·락 자원·BU_LOCK·backupdb·볼륨 프레이밍)은 `imports/vimkim/README.md` §2 표와 모듈 §2·§3 에 있다.

- **[storage §3]** `pgbuf_claim_bcb_for_fix` 의 `dwb_read_page` 실패 경로(`assert (false); return NULL;`)가 **BCB mutex 를 든 채** 반환한다는 원문 주장(P2 부수) — 호출 문맥의 LOCK/UNLOCK 짝 미대조. **미확인**
- **[storage §2]** 내부 `count_vict_cand` 의 증가 조건이 "zone3 ∧ non-dirty" 인지(`pgbuf_lru_add_victim_candidate` :15627 의 호출 조건) — SHOW 쪽(dirty)만 대조했다. **미확인**
- **[storage §3]** quota 비활성 시 `PGBUF_PRIVATE_LRU_COUNT == 0` 이 되어 :13929 가 `malloc(0)` 이 되는지 — 카운트 산출식 미대조. **미확인**
- **[transaction §2]** lock 패킷 C031~C038 의 btree/heap 줄 범위(unique 검사의 S wait→root 재탐색 `btree.c` 23679~24013, FK `btree_find_foreign_key` 6362~, heap insert row-X skip 20524~) — 자원·API 만 대조했고 btree 쪽은 미대조. **미확인**
- **[transaction §3]** CDC × HA failover 원인 후보(`imports/vimkim/transaction/cdc-ha-*`): master 재승격 후 CDC 세션/로그 위치 복원 경로 — 재현 로그 없는 정적 분석. **미확인**
- **[storage §2]** 볼륨 파서 문서의 볼륨 헤더·섹터 테이블 오프셋·TDE 가시 범위 세부(`disk_manager.c`) — `FILEIO_PAGE_RESERVED` 프레이밍만 대조. **미확인**
- **[transaction §2]** 로그 매니저 overview 16장 중 §11 체크포인트·§12 아카이브 삭제 정책의 함수·줄 — 미대조(§5·§9 는 동적 실측으로 원문이 확인). **미확인**
