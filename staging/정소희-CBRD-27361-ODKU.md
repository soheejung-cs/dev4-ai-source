# 정소희 — CBRD-27361 후속: INSERT … SELECT 집계 … ON DUPLICATE KEY UPDATE 의 숨은 컬럼 (환류 대기)

작성: 정소희 (.51) · 기준 develop `1684945ed`(#8196 머지 `309265e6d` 포함), 비교 `ad7a255c5`(#8196 직전) · 2026-11-02
상태: 수정 PR 미발행 — 로컬 브랜치 `odku-bv-fix` `66652e424`. 제보 개발 3팀(CBRD-27336 shell TC `cbrd_27336_forms` 칸 13).
재현: `INSERT INTO t (id) SELECT MAX(s.g) + 1 FROM s s WHERE s.g = 2 ON DUPLICATE KEY UPDATE c = s.c` — 중복 키 행의 c 가 `ad7a255c5` 'g2', develop NULL.

- **[src-parser §2] ODKU 가 읽는 소스 컬럼은 SELECT 목록의 숨은 컬럼이 된다** — `pt_to_insert_xasl ()` 이 aptr XASL 을 만들기 전에 `pt_append_assignment_references ()` 로 붙인다
  (trace rewritten query `select max(s.g)+1, s.c from … where s.g=?`). 사용자가 쓰면 "not single valued" 로 거절되는 "집계 옆 비집계 컬럼" 이 여기서만 생긴다.
- **[src-query §2] BUILDVALUE 의 출력 목록은 스캔이 닫힌 뒤 val_list 슬롯을 읽는다** — `qexec_execute_mainblock_internal ()` 이 블록의 스캔을 모두
  `qexec_end_scan ()`·`qexec_close_scan ()` 한 다음 `qexec_end_mainblock_iterations ()` → `qexec_end_buildvalueblock_iterations ()` 가 출력을 계산한다.
  숨은 컬럼 값 = 행 루프가 마지막으로 필터를 통과한 행에서 읽어 둔 값(WHERE·GROUP BY 없음: 마지막 행). GROUP BY 가 있으면 그룹의 첫 행.
- **[src-query §3] 이 값을 채우지 않는 경로 셋** —
  ① 페이지 배치(`qexec_batch_eligible ()` → `eb_build_aggs ()`): 집계 피연산자만 벡터로 디코드, val_list 를 안 채움 → NULL(#8196 회귀).
  ② 병렬 `gather: buildvalue`(ACCESS_SPEC_FLAG_BUILDVALUE_OPT): 워커 클론이 집계만 누적, 리더 val_list 비어 있음 → NULL(#8196 전부터, 소스 ≥ parallel_scan_page_threshold).
  ③ 병렬 `gather: row by row`(XASL_SNAPSHOT): 리더가 워커 리스트를 `qfile_scan_list_next (…, PEEK)` + `qfile_tuple_walk_read_value (…, copy=false)` 로 읽어 슬롯이
  리스트 페이지·튜플 버퍼를 가리킨다 → 스캔이 닫히면 해제된 메모리. 실측: STDDEV 마무리 할당이 덮어 VARCHAR 'g2' 가 길이만 남은 `'  '`.
- **[src-query §3] fixed 힙 스캔의 val_list 값은 페이지 프레임을 가리킨다** — `scan_next_heap_scan ()` 의 `is_peeking = scan_id->fixed`. 출력이 스캔 뒤 읽는 숨은 컬럼은
  unfix 된 프레임을 읽는 셈(그 사이 프레임이 다른 페이지로 바뀌면 틀린 값 — 잠재, 재현 안 됨, #8196 전부터).
- **[src-query §1] 병렬 스캔 검사기는 클라이언트에서 돈다** — `scan_check_parallel_scan_possible ()`(px_scan_checker.cpp)은 cs·sa 라이브러리에 들어가고 xasl_generation.c 가 부른다.
  서버 전용 `query_executor.h` 를 넣으면 CS 빌드가 `#error Belongs to server module` 로 깨진다. 검사기와 실행기가 같은 판정을 써야 하면 XASL 플래그로 넘긴다
  (`XASL_NO_FIXED_SCAN` 선례; 이번 수정은 `XASL_OUTPUT_READS_SCAN` 비트 29 — `pt_to_buildvalue_proc ()` 이 세우고, 배치 자격과 검사기의 CANNOT_PARALLEL_SCAN 이 읽는다).
