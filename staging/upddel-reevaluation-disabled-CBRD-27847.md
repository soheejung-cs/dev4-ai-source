# UPDATE·DELETE 의 MVCC 재평가는 XASL 생성에서 꺼져 있다 (CBRD-27847 리뷰 대응에서 확인)

- 컨테이너 .52, 기준 리비전 develop `226352283`(PR#8378 head `f3bac6bdc` 의 merge-base), 2026-11-05 확인. **미수정**(현재 동작 기록).
- 대상 모듈: parser(`xasl_generation.c`) · transaction(`locator_sr.c`) · query(`query_executor.c`).

## 사실
1. `pt_to_update_xasl ()`(`xasl_generation.c` ~26377)과 `pt_to_delete_xasl ()`(~25624)는 "These two lines disable reevaluation on UPDATE. To activate it just remove them" 아래에서 `PT_SELECT_INFO_SET_FLAG (aptr_statement, PT_SELECT_INFO_MVCC_LOCK_NEEDED)` 와 `abort_reevaluation = true` 를 **무조건** 실행한다 → 모든 spec 의 `PT_SPEC_FLAG_MVCC_COND_REEV`·`PT_SPEC_FLAG_MVCC_ASSIGN_REEV` 가 지워지고, 갱신 대상 spec 에 FOR UPDATE 플래그가 붙어 행이 **select 단계에서 잠긴다**.
2. 그래서 `locator_mvcc_reev_cond_assigns ()`·`locator_mvcc_reeval_scan_filters ()`(`locator_sr.c`) — force 단계에서 조건을 다시 평가하고 대입을 다시 계산하는 경로 — 는 UPDATE·DELETE 에서 타지 않는다. MERGE 의 갱신 질의(`pt_to_merge_update_query ()`)도 `PT_SELECT_INFO_MVCC_LOCK_NEEDED` + GROUP BY 로 select 단계에서 잠근다.
3. 동적 확인: debug 빌드에 gdb 로 두 함수 입구 중단점을 걸고, 세션 A 가 행을 갱신·미커밋으로 쥔 동안 세션 B 가 `update t1, t3, t2 set …`(두 클래스 갱신)·`update t1, t2 set …`(한 클래스)로 그 잠금을 기다리게 한 뒤 A 를 커밋 → 0회.
4. 그 경로가 살아난다면(위 두 줄 제거) 주의: `locator_mvcc_reeval_scan_filters ()` 는 갱신 대상이 아닌 클래스의 레코드를 지역 scan cache 로 **PEEK** 하고 함수 끝에서 `heap_scancache_end ()` 로 놓는다 — 속성 캐시 값(`heap_attrinfo_read_dbvalues` → `data_readval (..., copy=false)`)이 놓인 페이지를 가리킨 채 대입(`fetch_peek_dbval` → `heap_attrinfo_set_converted ()`)에 쓰인다. 문자열을 빌리는 쪽(CBRD-27847)은 이 값을 복사해 넘겨야 한다.

## 출처
- PR#8378 리뷰 스레드(chatgpt-codex-connector, `heap_file.c:12977`)와 답글 `discussion_r4476596452`, 재현 claude-workspace `projects/CBRD-27847/repro/reeval-codex-T0/`(비공개).
