# 페이지 래치 순서 — 쥔 채 식을 평가하는 자리 (CBRD-28421 → CBRD-28426)
.50, develop 3f4816831, SERVER. 미수정(수정은 CBRD-28426 진행 중). 모델: dev4 tla/storage/btree_latch_order.

- 병합 첫 시도는 부모를 `nonleaf_latch_mode`(READ)로 쥔 채 자식 리프 W, 오른쪽 이웃 W 를 무조건 fix 한 뒤 부모를 `PGBUF_PROMOTE_ONLY_READER` 로 승격한다(실패하면 W 로 재시작) — 그래서 루트를 READ 로 쥔 스캔과 공존하며 리프끼리 순환할 수 있다. btree.c:37032, :37105, `btree_merge_node_and_advance ()`.
- 힙 스캔이 data filter 평가 동안 힙 페이지를 쥐는 것은 fixed 스캔일 때만(`heap_scancache_start (..., cache_last_fix_page = scan_id->fixed)` scan_manager.c:4313, heap_next 의 unfix 조건 heap_file.c:8306). 평가 앞뒤 LSA 재확인 scan_manager.c:6116·6131 은 data filter 둘레에만 있다.
- `XASL_NO_FIXED_SCAN` 은 serial(xasl_generation.c:12969)·index_cardinality/estimated_*(:13204~13240)에만 붙고 저장 함수(TYPE_SP)에는 붙지 않는다. 안쪽 블록 dptr 검사는 인덱스 스캔 갈래에만(query_executor.c:23303).
- `qexec_covered_visit_scan ()`(query_executor.c:29441)은 dptr·LINK_TO_REGU aptr·serial 은 막지만 TYPE_SP 는 보지 않아, `qexec_covered_visit ()`(:29482)가 리프를 쥔 채 select 목록의 저장 함수를 부를 수 있다(btree.c:22323).
- `locator_lock_and_get_object_with_evaluation ()`(locator_sr.c:15958)은 힙 페이지를 쥔 채 range/key/data filter 를 재평가한다(:16651·:16667·:16679, 놓는 곳 :16095).
- loaddb `locator_multi_insert_force ()` 는 새 힙 페이지를 W 로 쥔 채(`cache_last_fix_page = true` + home_hint, locator_sr.c:16832, heap_file.c:26874) 인덱스에 삽입한다 — 힙 W → 리프 W 순서. 호출은 load_server_loader.cpp:1056 하나.
- batch 스캔 consumer 는 fixed 스캔에서만 붙는다(scan_manager.c:8122 assert) — 행 경로로 넘긴 페이지를 쥐는 것도 fixed 조건을 따른다.
