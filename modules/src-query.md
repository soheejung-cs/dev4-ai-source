# src/query

> 기준: upstream/develop 95b79e7ed (2026-08-27)

## 1. 소스 목적 및 사용처 (함수별)

서버 측. 역직렬화된 XASL 플랜 실행. 핵심: `query_executor.c`(~27K, XASL 트리 워커),
`scan_manager.c`(힙·인덱스·리스트·셋·메서드 스캔), `fetch.c`(REGU_VARIABLE 평가),
`string_opfunc.c`(~28K)·`arithmetic.c`·`query_opfunc.c`(함수·집계 구현),
`xasl_to_stream.c`(클라: 직렬화)/`stream_to_xasl.c`(서버: 역직렬화), `list_file.c`(중간 결과 임시 파일),
`xasl_cache.c`(XASL 캐시), `vacuum.c`(MVCC GC). `parallel/` 하위에 병렬 실행(px 스캔·해시조인·쿼리실행·정렬,
코어는 `px_parallel.hpp`·`px_worker_manager.hpp`).

| 함수 | 파일 | 목적 | 주요 사용처(호출자) |
|---|---|---|---|
| `qexec_execute_query` | query_executor.c:17097 | 쿼리 실행 최상위 진입점 — XASL 트리 + 호스트변수 → 결과 리스트 파일 | query_manager.c:1232 |
| `qexec_execute_mainblock` | query_executor.c:15664 | XASL 트리 워커 — PROC 타입별(BUILDLIST/BUILDVALUE/UNION/SCAN…) 디스패치 | qexec_execute_query, px_query_task.cpp:136, xasl.h:588 매크로 |
| `qexec_execute_scan` | query_executor.c:8483 | 현재 spec의 스캔을 1스텝 진행하고 조인/술어 판정 | query_executor.c:8456(qexec_next_scan_block 계열), 조인 루프 재귀 |
| `scan_open_heap_scan` / `scan_open_index_scan` | scan_manager.c:3242 / :3457 | 힙/인덱스 스캔 오픈(SCAN_ID 초기화) | query_executor.c:7528·:7553, px_scan_task.cpp:201·:224 |
| `scan_next_scan` | scan_manager.c:7833 | 스캔 커서 전진(타입별 next 디스패치) | query_executor.c:8522·:9416·:10473 등 |
| `eval_pred` | query_evaluator.c:1666 | PRED_EXPR 제네릭 재귀 평가 | query_executor.c(after_join_pred :8589 / if_pred :8604), fetch.c:2584, px_scan_task.cpp:671·:691 |
| `eval_fnc` | query_evaluator.c:2590 | 술어 형태별 특수화 커널(PR_EVAL_FNC) 선택 | scan_manager.c:3283·:3342·:3633 등(호출부 전부 scan_manager 계열) |
| `eval_data_filter` | query_evaluator.c:2907 | 힙 행 데이터 필터 평가(attr 읽기+술어) | scan_manager.c, px_scan_slot_iterator.cpp:121 |
| `fetch_peek_dbval` | fetch.h:56(inline)/fetch.c | REGU_VARIABLE 값 페치(빌린 포인터 반환) | 실행기 전 경로 |
| `fetch_peek_arith` | fetch.c:85 | 산술식 REGU 평가 — T_* 434-case 스위치, 행마다 재귀 | fetch_peek_dbval 경유 전 실행 경로 |
| `qdata_add_dbval` | query_opfunc.c:2438 | 덧셈/SUM 누산(타입쌍 스위치) | query_aggregate.cpp, fetch.c |
| `qdata_generate_tuple_desc_for_valptr_list` | query_opfunc.c:625 | 출력 리스트용 튜플 디스크립터 생성 | query_executor.c:976, px_scan_result_handler.cpp:883 |
| `qdata_copy_db_value_to_tuple_value` | query_opfunc.c:356 | DB_VALUE → 튜플 값 기록 | list_file.c:1705·:3291, query_executor.c:3882 |
| `qfile_open_list` | list_file.c:1207 | 리스트 파일(중간 결과) 생성 | 호출부 41곳 — query_executor, px_hash_join.cpp:333, px_scan_result_handler.cpp:246 등 |
| `qfile_generate_tuple_into_list` | list_file.c:1852 | 튜플 디스크립터 내용으로 리스트 파일에 튜플 생성 | query_executor.c:1237, query_aggregate.cpp:2541, px_scan_result_handler.cpp:961 |
| `mht_get_hash_number` | base/memory_hash.c:2339 (모듈 외부지만 query 해시 경로 핵심) | DB_VALUE 해시값 계산 | memoize.cpp:673, query_aggregate.cpp:2316, query_hash_scan.c:297, subquery_cache.c:236, partition.c:1254 |
| `xcache_find_xasl_id_for_execute` | xasl_cache.c:969 | 실행 시 XASL_ID로 캐시 엔트리+클론 확보 | query_manager.c:1380, px_scan_task.cpp:579 |
| `xcache_insert` | xasl_cache.c:1465 | prepare 결과 스트림을 캐시에 등록 | query_manager.c:1116 |
| `hjoin_merge_tuple` / `hjoin_merge_tuple_to_list_id` | query_hash_join.c:4313 / :4247 | 해시조인 outer+inner 튜플 병합 후 결과 리스트에 기록 | query_hash_join.c, px_hash_join_task_manager.cpp:1129·:1384·:1505·:1563 |
| `parallel_query::compute_parallel_degree` | parallel/px_parallel.cpp:36 | 페이지 수/타입 기반 병렬도 결정 | query_executor.c:16249, px_scan.cpp:418·:883, optimizer/histogram/histogram_sampler_sr.cpp:1031 |
| `parallel_query::worker_manager::try_reserve_workers` | parallel/px_worker_manager.cpp | 워커 풀 예약(실패 시 nullptr → 직렬 폴백) | query_executor.c:16260, px_scan.cpp:427·:892·:1415 |
| `parallel_query::make_parallel_query_executor_recursively` | parallel/px_query_execute/px_query_executor.cpp | 서브쿼리 병렬 실행기 구성 | query_executor.c:16261 부근 |
| `new_memoize_storage` | memoize.cpp:1044 | XASL 노드에 memoize 스토리지 부착 | px_scan_task.cpp:364 |

## 2. 분석 내용 (함수별)

> 항목은 함수 단위로 기술한다 — 각 항목의 제목/선두가 함수·파일명이다. 새 분석도 함수명을 앞세워 추가할 것.

### 모듈 일반

- XASL 직렬화는 클라이언트/서버 간 **정확히 일치**해야 함 — 버전 불일치는 크래시.
  XASL 구조 변경 시 `xasl_to_stream.c`와 `stream_to_xasl.c`가 대칭으로 수정됐는지 볼 것.
- 리스트 파일 I/O가 주요 병목이 될 수 있음 — 큰 결과는 임시 파일이 디스크를 친다.
- 새 함수 추가는 `string_opfunc.c` 또는 `arithmetic.c` 구현 + `fetch.c` 배선.
- `THREAD_ENTRY *thread_p` 첫 파라미터, 접두사 `qexec_`/`scan_`/`qfile_`.
- 함수 구현은 `DB_VALUE *` 인자를 받아 `DB_VALUE *`에 결과를 쓴다. 집계 상태는 XASL 노드의
  `AGGREGATE_TYPE` 연결 리스트.
- ✅ **리뷰 체크포인트**: 스캔 open/next/close가 짝을 이루고 에러 경로에서도 close되는가?
- ✅ **리뷰 체크포인트**: 함수 결과 `DB_VALUE`의 정리(need_clear) 책임이 명확한가?
- ✅ **리뷰 체크포인트**: 대량 결과 경로에서 불필요한 리스트 파일 materialize를 만들지 않는가?

(원본: src/query/AGENTS.md)

- 구현 불필요 판정 2건: order by 식의 컴파일은 이미 발화함을 `;trace`로 확인해 불필요 판정,
  리스트 간 프로그램 공유는 XASL position 공유와 tuple descriptor의 `pr_share_value`(develop
  query_executor.c:4672·:4781, fetch.c:4922)가 이미 존재해 중복 평가가 발생하지 않아 불필요 판정.
- ✅ **리뷰 체크포인트**: '식이 두 번 평가된다'는 의심이 들면 XASL position 공유 / tpldesc `pr_share_value`가 이미 처리하는 경우인지부터 `;trace`로 확인할 것.

### qexec_execute_mainblock (query_executor.c:15664)

- 진입 직후 `static int max_recursion_sql_depth = prm_get_integer_value(...)`(:15673) —
  PRM_USER_CHANGE 파라미터를 프로세스 수명 동안 캐시(경미). `eval_pred`(query_evaluator.c:1676)와
  동일 패턴이고, scan_manager.c:4968·:6626도 같은 static-PRM 캐시 관용구다(그쪽은
  PRM_ID_MAX_PAGES_IN_TEMP_FILE_CACHE — develop 확인).
- ✅ **리뷰 체크포인트**: 재귀 평가 경로에 깊이 제한/스택 고려가 있는가?

### qexec_execute_scan (query_executor.c:8483)

- 플랜상수 XASL 필드 11개(6캐시라인, 1320B)를 행마다 재로드 — PLT 호출이 CSE를 차단(디스어셈블 확인).
- after_join_pred(:8589)·if_pred(:8604)는 행마다 **제네릭 `eval_pred`**를 탄다(실측 2.84%,
  특수화 커널 적용 시 프로파일은 부재) — 아래 eval_fnc 절 참조.

### eval_pred / eval_fnc (query_evaluator.c:1666 / :2590)

- eval_pred 특수화 미적용: `eval_fnc()`가 고르는 특수화 커널(PR_EVAL_FNC)의 호출부 17개는 전부
  scan_manager 계열 — query_executor.c의 after_join_pred/if_pred는 행마다 제네릭 `eval_pred`
  (실측 2.84%, 특수화 커널은 프로파일 부재).
- eval_pred :1676: `static int max_recursion_sql_depth` — PRM_USER_CHANGE 파라미터를 프로세스
  수명 캐시(경미). scan_manager.c:4968·:6626 동일 패턴.
- `REGU_VARIABLE`/PRED_EXPR 평가는 재귀 — 깊은 식은 스택 오버플로 가능.

### fetch_peek_dbval / fetch_peek_arith (fetch.c)

- 행당 식 평가 병목의 실체 ①: `fetch_peek_arith()`(fetch.c:85)가 T_* 케이스 434개짜리 스위치를
  **행마다 재귀적으로** 타는 구조. TPC-H Q1 30.9s 중 ~27s가 집계·식 평가였고 스캔 자체는 q6 기준
  3.3s — 즉 스캔이 아니라 식 평가가 지배한다. (설계문서 `/home/cubrid/dev/expr-compile-design.md`)
- 컴파일이 얹힐 수 있는 기존 XASL 지형: `ARITH_TYPE.value`는 노드별 결과 슬롯이 이미 존재하고,
  `original_domain` 필드는 **clone 실행 시 도메인이 재확정된다는 증거**다. regu 트리 순회 워커는
  `regu_variable_node::map_regu()`(regu_var.hpp:213, `map_regu_and_xasl()`은 :215)이고,
  `REGU_VARIABLE_FAST_PEEK`(regu_var.hpp:174 정의 — "inline fetch_peek_dbval () may return its
  value pointer directly", 설정은 fetch.c:4635)는 같은 방향의 선행 흔적이다. (원 메모의
  fetch.c:4597은 행 번호 확인 필요 — 현재 소스와 불일치)
  — `original_domain` 은 develop `be683e04c`([CBRD-27510] #8022, 2026-10-11)가 "clone-domain restoration" 과 함께 없앴다:
  도메인은 이제 실행 전 `qexec_resolve_domains ()` 가 실행당 1회 정한다(아래 「식 컴파일 머지본 재확인」 절). — 정소희(.50) 2026-10-28
- ✅ **리뷰 체크포인트**: regu 트리를 새로 순회·변형하는 코드가 `map_regu()`를 재사용했는지, 결과를 `ARITH_TYPE.value` 외 임시 슬롯에 쓰면서 소유권이 흐려지지 않았는지 확인할 것.
- **리스트 파일 값 읽기(`TYPE_POSITION`)도 peek 다** (.52, `a7a1db84b`, 2026-09-16; develop `2d925cb86` 재확인 2026-10-28):
  `fetch_peek_dbval` 이 `qfile_locate_tuple_value` 뒤 `data_readval(…, false /* Don't copy */)`(fetch.c:4726-4737). develop 은 리스트 파일
  튜플 형식 교체([CBRD-27365] `453da49c8`, 2026-09-29) 뒤 `qfile_slot_read_column_value (…, false /* Don't copy */ …)`(fetch.c:1781-1782
  `fetch_peek_dbval_slow`, :2394-2395 `fetch_peek_dbval_pos`)로 읽지만 peek 인 것은 같다. 행당 강제 복사는 XASL 블록 출력의 튜플 조립
  (`qfile_generate_tuple_into_list`, develop list_file.c:1805) 한 번이다 — `a7a1db84b` 의 형식은 값당 8B 헤더 + 8B 튜플 길이(query_list.h:229-236)
  였고, `453da49c8` 이 도메인 기반 compact 형식(고정폭 값은 정렬해 그대로, 가변 길이는 짧은 길이 헤더, NULL 이 있을 때만 비트맵 —
  `qfile_tuple_layout.h/.c`, 커밋 메시지 기준)으로 바꿨다. — 정소희(.50) 2026-10-28

### qdata_add_dbval (query_opfunc.c:2438)

- 행당 식 평가 병목의 실체 ②: 행마다 타입조회 → ENUM 특례 →
  `prm_get_bool_value(PRM_ID_PLUS_AS_CONCAT)` 파라미터 조회(:2501) → NULL 검사 → 피연산자 순서
  행렬 → cast 준비 → 타입쌍 스위치를 전부 반복하는 구조.
- ✅ **리뷰 체크포인트**: 행당 경로(`fetch_peek_arith` / `qdata_*`)에 파라미터 조회·타입 재판정·cast 준비 같은 '매행 반복 가능한 준비 작업'이 새로 들어가지 않았는지 확인할 것.

### qdata_generate_tuple_desc_for_valptr_list / qdata_copy_db_value_to_tuple_value (query_opfunc.c:625 / :356)

- 튜플 크기 2회 계산(~2.75%): `qdata_generate_tuple_desc_for_valptr_list`(:625)가 계산한 크기를
  버림 → `qdata_copy_db_value_to_tuple_value`(:356)+`pr_data_writeval_disk_size`가 재계산.
  `QFILE_TUPLE_DESCRIPTOR`에 f_size 배열이면 끝.

### mht_get_hash_number (base/memory_hash.c:2339)

- `key % ht_size`가 div 4개. 실측 당시 호출부 10곳이 UINT_MAX(항등)로 호출 — 단 전부는 아님:
  subquery_cache·query_aggregate·partition 쪽은 실제 버킷 수를 넘긴다. JOB 0.40%, TPC-H에서 유의미.
- develop 95b79e7ed 확인: src 전체 호출부 6곳 — UINT_MAX는 memoize.cpp:673 1곳,
  subquery_cache.c:236 · query_aggregate.cpp:2316(`qdata_hash_agg_hkey`, "hash table size (in
  buckets)") · query_hash_scan.c:297(`qdata_hash_scan_key`) · partition.c:1254·:1305는 실제 버킷
  수. (원 메모의 subquery_cache.c:227 · query_aggregate.cpp:2306은 행 번호 확인 필요 — 현재
  소스와 불일치)

### resolve_domains_on_list_scan (scan_manager.c:8216)

- 구조상 행마다 재순회지만 JOB 실측 0.00% — list scan 비임계.

### xcache 계열 — xcache_find_sha1 / xcache_insert (xasl_cache.c:872 / :1465)

- 통계·히스토그램을 갱신해도 **기존 캐시 플랜을 계속 사용** — 플랜 A/B 비교는 서버 재시작 또는
  쿼리 텍스트 변형으로. 주석은 캐시 키에서 정규화로 제거되므로 **주석 변경으로는 캐시를 우회할 수
  없다**(별칭을 바꿔야 함).
  `UPDATE STATISTICS` 를 커밋한 뒤에도 같은 SQL 은 캐시된 구 플랜(iscan card 100)을 그대로 쓰고, `/*+ RECOMPILE */` 또는 서버 재시작
  뒤에만 새 플랜(sscan card 99004)이 나왔다(.51, PR#7900 빌드, 2026-09-09 실측 — develop `620ceaf6a` 이전). develop `2d925cb86` 정적
  재확인 2026-10-28: statistics_sr.c·statistics_cl.c·schema_manager.c 에 XASL 캐시 무효화 호출이 없다. 바뀐 점: `620ceaf6a`(CBRD-27490)부터
  바인드 변형 대상 질의(실클래스 spec 2개 이상·MCV 컬럼·유니크 키 고정 없음인 SELECT·서버측 UPDATE/DELETE — 커밋 메시지 기준)는 바인드
  지문마다 최대 `plan_cache_bind_variants`(기본 5)개 플랜을 각자 별도 엔트리로 두므로, 같은 SQL 텍스트라도 바인드 값에 따라 다른 플랜을 쓸
  수 있다 — A/B 때는 바인드 값도 고정할 것(규칙은 src-compat §2 「do_replan_statement_with_bind_peek …」). — 정소희(.50) 2026-10-28
- **XASL 캐시 키(SHA1) 계산 지점은 5곳이고 `PT_PRINT_DIFFERENT_SYSTEM_PARAMETERS` 는 `do_prepare_select` 에만 있다**
  (.50, `87b25579e`, 2026-09-22; develop `2d925cb86` 재확인 2026-10-28): execute_statement.c 의 `do_prepare_update`(:9954/:9962)·
  `do_prepare_delete`(:11352/:11360)·`do_prepare_insert_internal`(:12029/:12032)·`do_prepare_select`(:15376/:15385)·`do_prepare_merge`
  (:18476/:18478). 출력 플래그는 모두 `CUSTOM_PRINT_4_SHA_COMPUTE | PT_PRINT_LOWER`(:109)이고 select 만 `PT_PRINT_DIFFERENT_SYSTEM_PARAMETERS`
  를 더해, `parser_print_tree` 가 `?` 뒤에 `sysprm_print_parameters_for_qry_string ()` 출력을 붙인다(parse_tree_cl.c:3119-3124). 따라서
  `PRM_FOR_QRY_STRING` 파라미터(`cost_*` — [CBRD-27126] `fa551431b`, `max_hash_list_scan_size`, `memoize_memory_limit` 등)는
  **UPDATE/DELETE/INSERT/MERGE 서버측 플랜의 캐시 키에 반영되지 않는다** → §3. (`87b25579e` 에도 MERGE 포함 5곳 — 처음 기록의 "4곳"은
  MERGE 누락.) develop `620ceaf6a`([CBRD-27490] #8013, 2026-10-21)부터 select·update·delete 는 SHA1 직전에 바인드 변형 키를 해시 텍스트
  뒤에 붙여(`do_append_bind_variant_key ()` :15279, 호출 :9956·:11354·:15379) 변형마다 별도 캐시 엔트리가 된다(insert·merge 는 붙이지 않음;
  지문·변형 규칙은 src-compat §2 「do_replan_statement_with_bind_peek …」). 짝: src-base §2 「sysprm_print_parameters_for_qry_string」 끝 줄
  (출력 플래그를 켜는 곳은 `do_prepare_select` :15376 하나). — 정소희(.50) 2026-10-28

### XASL clone 보관·폐기와 clear 표시 규칙 — 플랜 캐시 세 모양·px 워커 트리·메모리 래퍼·trace·NULL 순서 (xasl_cache.c / query_executor.c / stream_to_xasl.c)

> 출처: .52, 기준 `baa9ba017`(feature/expression-compile) / develop `a0c1b6c41` 머지본, 2026-09-17 — CBRD-27215 작업 중 확인한 엔진 쪽 계약.
> "develop" 이라고 적은 줄 번호·차이는 develop `2d925cb86`(PR#7658 머지 `b8199438e` 이후)로 재확인 2026-10-28. — 정소희(.50) 2026-10-28

#### 메모리 래퍼 — `malloc` 은 SERVER_MODE 에서 추적된다

`src/base/memory_cwrapper.h:186-190`(develop :201-205)이 SERVER_MODE 에서 `malloc`/`calloc`/`realloc`/`strdup` 을
`cub_alloc (…, __FILE__, __LINE__)` 계열로, `free` 를 `cub_free` 로 `#define` 치환한다. 그래서 소스에 raw `malloc` 을 써도
`cubrid memmon` 이 **파일:줄 단위**로 집계한다(통계 이름은 basename 이 아니라 마지막 `/src/` 이후 경로 — `memory_monitor_sr.hpp` 의
`m_target_pos`). 조건: 그 파일이 `memory_wrapper.hpp` 를 **마지막에** include 해야 하고 CI(`.github/workflows/check.yml`)가 이를 강제한다.
**`posix_memalign` 은 치환 목록에 없다** — 정렬 할당은 `cub_aligned_alloc ()`([CBRD-26964] `b646647ec`, `memory_cwrapper.h:202`; develop :208-245)를
써야 추적된다. 추적 밖 블록을 `cub_free` 로 놓아도 오계상은 없다: `memory_monitor_sr.hpp` 의 `sub_stat ()`(develop :267-292)이 metainfo 의
magic number 를 대조해 불일치면 아무것도 빼지 않는다.

#### 플랜 캐시는 세 모양이고 트리 폐기 주체가 서로 다르다

| 설정 | 트리 | 폐기 주체 |
|---|---|---|
| 기본 | clone 을 캐시에 보관·재사용 | `xcache_clone_decache ()` — 플래그 세우고 `qexec_clear_xasl ()` |
| `max_plan_cache_clones=0` | `xcache_uses_clones ()` 가 거짓 → 실행마다 `stx_map_stream_to_xasl (…, use_xasl_clone=false, …)` 로 새 트리 | `xcache_retire_clone ()` 의 꼬리 — 원래 `free_xasl_unpack_info` 만 했다 |
| `max_plan_cache_entries=0` | 캐시 비활성(`xcache_Soft_capacity <= 0` → `xcache_Enabled=false`), 원샷 | `qmgr_process_query ()` |

develop: `xcache_uses_clones ()` = `xcache_Max_clones > 0`(xasl_cache.c:2906), 비활성 판정 :344. PR#7658 머지 뒤로 `xcache_retire_clone ()`
꼬리(:2518-2527)와 `qmgr_process_query ()`(query_manager.c:1270-1281)가 둘 다 `XASL_DECACHE_CLONE` 를 세운 `qexec_clear_xasl ()` 를 한 번 더
돌려 컴파일된 식 프로그램까지 놓는다(아래 clear 규칙의 2패스).

#### clear 루틴은 플래그에 따라 표시를 **반대로** 읽는다

`qexec_clear_regu_var ()` TYPE_CONSTANT(`query_executor.c:1551-1566`; develop :1588-1605) 와 `qexec_clear_agg_list ()`(develop :2328-2361)
— `qexec_clear_access_spec_list ()` 의 `clear_value_at_clone_decache`(develop :1940-1955)도 같은 규칙이다:
- `XASL_DECACHE_CLONE` **있음** → `CLEAR_AT_CLONE_DECACHE` 표시가 **있는** 값만 `pr_clear_value`
- **없음** → 표시가 **없는** 값만

`use_xasl_clone=false` 로 푼 트리는 그 표시가 하나도 없다(`stream_to_xasl.c` 의 `4770`·`5716`·`5736`·`6024`·`6043`·`3633` 이 전부
`use_xasl_clone` 가드 아래; develop :3706·:4873·:5864·:5884·:6171·:6190). 따라서 **표시 없는 트리에 플래그를 세운 단일 패스는 값을 하나도
해제하지 않는다.** 원샷 경로가 2패스(무플래그 최종 clear → 플래그 pass)인 이유가 이것이다.

#### px 워커는 자기 트리를 갖는다

`px_scan_task.cpp` 의 `clone_xasl ()`(develop :631) 이 `m_uses_xasl_clone` 이면 `xcache_find_xasl_id_for_execute ()` 로 자기 clone 을,
아니면 `stx_map_stream_to_xasl ()` 로 자기 트리를 푼다. 이어서 `m_xasl = xasl_find_by_id (…)`, `m_scan_id = &m_xasl->spec_list->s_id`(:675).
따라서 워커 간 `PRED_EXPR` 공유가 없다(`scan_prog` 레이스 없음). develop 은 clone 이 아닌 워커 트리도 `finalize ()` 에서 같은 2패스로
정리한다(px_scan_task.cpp:563-577).

#### trace 포맷 두 갈래

`qdump_print_expr_compile_text ()` 를 부르는 곳은 `qdump_print_stats_text ()` 하나다. JSON 쪽 `qdump_print_stats_json ()` 에는 대응 절이 없다.
CCI 인터페이스는 JSON trace 를 쓰므로 `.answer_cci` 에는 EXPR_COMPILE 줄이 나오지 않는다(CCI 26건 실행으로 확인). develop 에서는 호출처가
하나 늘었다 — px 워커의 `trace_handler::add_expr_compile_dump ()`(px_scan_trace_handler.cpp:120-151, 태그 " [px worker]"). JSON 은 직렬
`qdump_print_stats_json ()`(query_dump.c:3679)에 여전히 절이 없고, 병렬 노드의 `parallel` 객체에만 `expr_compile` 문자열이 붙는다
(px_scan_trace_handler.cpp:550-552) — 병렬 플랜의 CCI 답에 나오는지는 미확인.

#### 산술 커널의 NULL 처리 순서

`EXPR_ARITH_PROLOGUE` 가 두 피연산자의 NULL 을 **타입 가드(`EXPR_ARITH_REQUIRE_TYPE`)보다 먼저** 걸러 `PRIM_SET_NULL (step->out)` 후
반환한다(develop expr_compile.c:338-345 → :358). 커널 선택만 타입으로 하고 실행은 NULL 을 이미 다룬다. 호스트 변수의 타입은
`expr_leaf_type ()` 이 바인딩된 값에서 얻으므로 NULL 바인딩은 `DB_TYPE_NULL` 이 되고 `expr_arith_kernel ()` 에 항목이 없어 거절된다
(→ CBRD-27455). develop 에서는 산술 커널의 타입이 바인딩 값이 아니라 resolve_domains 의 number plan(`expr_arith_number_plan ()` 의
`plan->arith.type`, :5036-5068)에서 오고, (opcode, 타입) 칸이 없으면 거절 대신 `expr_compile_generic ()` 으로 간다; 해석 결과가
'값 없음'(`DB_TYPE_NULL`)인 노드는 거절한다(:2414-2422 머리 주석, :2488). CBRD-27455 키의 커밋은 develop 에 없다.

#### 해석 경로의 NULL 시맨틱·오류 순서 (csql 실측)

산술만 전파: `a*?`·`a+?`·`a/?` → NULL (`a / NULL` 은 0 나누기 오류가 아니다).
비전파: `nvl(?, a)`·`coalesce(?, a)`·`nullif(a, ?)` → a 값, `case when a > ?` → else 분기, `a > ?` → NULL.
오류 순서: `(a / (a-10)) * ?` (?=NULL) → **0 나누기 오류**(왼쪽 먼저 평가) / `? * (a / (a-10))` → **NULL**(왼쪽이 NULL 이라 오른쪽 미평가).

### hjoin_merge_tuple (query_hash_join.c:4313)

- 소스/목적지 비중첩을 암묵 전제로 한다(self-overwrite + realloc UAF). 진입점은
  `hjoin_merge_tuple_to_list_id`(:4247 → :4281). 소스 튜플의 컬럼을 순차로 읽어가며 목적지 버퍼에
  `memcpy`한다(:4398). 소스와 목적지가 같은 메모리면 아직 읽지 않은 소스 컬럼 헤더가 덮여 깨지고
  value 길이 체인 워크가 튜플 끝을 넘어간다(코어 시점: pos_index=3, value_index=4, offset=72).
  게다가 :4387-4390에서 `qfile_reallocate_tuple`로 목적지 버퍼가 realloc되면 소스 포인터가
  dangling되어 use-after-free까지 난다 — 주석은 "overflow_record is managed and cleaned up by the
  caller."로만 적혀 있고 비중첩 요구는 명시돼 있지 않다. (원 메모의 :4229, :4221은 행 번호 확인
  필요 — 현재 소스와 불일치)
- ✅ **리뷰 체크포인트**: 이 계열 호출부는 소스/목적지 버퍼 비중첩을 호출 규약으로 명시·검증하고, realloc 이후 소스 포인터를 재사용하는 코드가 없는지 함께 볼 것.
- 증상 매핑: release 빌드 `ER_TF_BUFFER_OVERFLOW`("Object buffer overflow while writing"), debug
  빌드 그 직전 `assert (false)`로 cub_server abort — 현재 소스 :4371(assert)·:4372(에러 설정),
  주석 `/* impossible case */`(원 메모의 :4202/:4203은 행 번호 확인 필요 — 현재 소스와 불일치).
  실제 원인은 그 지점이 아니라 앞서 손상된 튜플 헤더 때문에 value 길이 워크가 튜플 경계를 넘은 것.
- ✅ **리뷰 체크포인트**: 이 에러가 보고되면 버퍼 크기 계산을 키우는 식으로 덮지 말고 소스 튜플이 이미 손상됐는지(버퍼 앨리어싱)부터 확인할 것.

### px_hash_join probe/merge overflow (parallel/px_hash_join/px_hash_join_task_manager.cpp)

- probe overflow 버퍼 앨리어싱 — 원인과 수정 형태(현재 소스에는 수정 반영됨): probe 태스크가
  overflow 튜플을 조립한 `QFILE_TUPLE_RECORD`를 그대로 merge 결과용 스크래치 버퍼로도 넘겨 merge의
  소스와 목적지가 같은 메모리가 되는 버그(코어 덤프로 확정: `outer_record->tpl ==
  overflow_record.tpl == 0x1338a510`). 수정은 **버퍼 분리** — 현재 소스는
  `probe_overflow_record`(조립용)와 `overflow_record`(merge 스크래치)를 별도 선언한다
  (:898-899·:1193-1194, 조립 :993/:1291, 대입 :1001/:1299, merge 호출 :1129/:1384/:1505/:1563,
  해제 :1176-1183/:1604-1611). 수정 커밋 `5795b1ab6`([CBRD-26900] PR#7269)이 현재 HEAD에 포함.
  (원 메모의 :1104-1119, :1217은 행 번호 확인 필요 — 현재 소스와 불일치)
- ✅ **리뷰 체크포인트**: 해시조인 경로에서 `QFILE_TUPLE_RECORD`를 넘길 때 소스로 쓰이는 레코드와 결과/스크래치로 쓰이는 레코드가 같은 인스턴스가 아닌지 확인할 것.
- overflow 튜플 대입 시 `tuple_record.size`가 0으로 남는 부분 초기화 상태: probe 경로는
  `probe->tuple_record.tpl = probe_overflow_record.tpl`처럼 **`tpl` 포인터만 대입하고 `size`는
  갱신하지 않는다**(:1001, :1299; 비병렬 대응 관용구는 :289). 코어에서 `outer_record.size == 0`이
  정상 경로로 흘러가는 것이 확인됐고, build(inner) 튜플은 size 정상(56B)이었다. 따라서
  `QFILE_TUPLE_RECORD.size`를 버퍼 용량이나 튜플 길이로 신뢰하는 코드는 overflow 경로에서 오동작한다.
- ✅ **리뷰 체크포인트**: `size`를 용량 판단(예: realloc 필요 여부)에 쓰는 코드가 overflow 조립 경로에서 size=0으로 들어올 수 있는지 확인하고, 포인터만 대입하는 관용구가 보이면 size 동기화 누락을 의심할 것.
- 옵티마이저 변경이 새 해시조인 플랜 형태를 만들면 실행기 버그를 밟을 수 있다(JOB 7c 사례):
  `qo_iscan_cost` fanout 수정(`c31d3b2f6` [CBRD-26936])으로 JOB 7c가 "Object buffer overflow
  while writing"으로 **실행 실패**. 트리거는 새 해시조인 플랜 형태(빌드 측 = movie_link, 프로브 측
  = 깊은 NL 체인)였고 옵티마이저 결함이 아니라 위 probe overflow 버퍼 앨리어싱이라는 실행기
  버그였다 — 당시 develop 머지(`5dc7be6f8`) 후에도 7c는 ERR로 남아 있었으며, 근본 수정은 이후
  `5795b1ab6`에서 들어갔다.
- ✅ **리뷰 체크포인트**: 옵티마이저 변경이 새로운 조인 플랜 형태를 만들면 실행 오류(ERR) 쿼리가 늘지 않았는지 반드시 확인하고, 'Object buffer overflow while writing'이 나오면 옵티마이저가 아니라 해시조인 버퍼 취급을 의심할 것.

### px_scan_slot_iterator (parallel/px_scan/px_scan_slot_iterator.cpp)

- **버그(수정됨: `6663cd894` CBRD-27604, 2026-10-15)**: 예전에는 `qualified_rows++`가 `if (ev_res != V_TRUE) continue`
  **앞**에 있어(develop 95b79e7ed :125) 병렬 heap 스캔의 qualified==read가 항상 성립했다 → SET TRACE ON 선택도가 무의미.
  develop `2d925cb86` 에서는 `continue`(:136) 뒤 `if (m_on_trace)` 안(:139-141)으로 옮겨져 직렬(scan_manager.c)·병렬
  LIST 와 같다. — 정소희(.50) 2026-10-28

### result_handler (parallel/px_scan/px_scan_result_handler.hpp / .cpp)

- **의심(작성자 확인 필요)**: `is_list_id_domain_resolved`(hpp:97; 원 메모 :96) — 워커 공유
  플래그가 워커 전용 `tl.writer_result_p` 도메인 보정을 가드(cpp:885-888). A가 뒤집으면 B가 자기
  보정을 건너뜀.
- TLS 폭풍: `result_handler<MERGEABLE_LIST>::write` 행당 TLS init 가드 47 + `__tls_get_addr` 9.
  원인: `thread_local static tls tl`(hpp:81)의 동적 초기화. 진입 시 참조 1회로 47→1.

### memoize::storage::get (memoize.cpp)

- 외부 행마다 `storage::get()`이 get_entry×4 + heap 전환×3 + 키 할당/해제 1쌍(memoize.cpp:812-890).
  per-worker 분리 → 병렬화 시 예산 N배 + 히트율 희석 → 1000프로브 후 히트율<0.5면 영구
  자기비활성(원 메모 L907; develop에서 자기비활성 분기는 :900대 초반으로 확인). 직렬 기준
  캘리브레이션이라 병렬에서 조용히 꺼질 수 있음. TRACE hit/miss로 확인.

### qexec_next_scan_block_renew_memoize (query_executor.c:8600)

- **row memo 는 그것을 채운 scan block 에만 유효하고, 갱신은 chain block 반복기가 *파티션된* inner 를 다음 block 으로 옮길 때만 한다**
  (develop `2d925cb86` 정적 확인 2026-10-28 — .52 PR#8009 head `616c704bd` 리뷰(2026-09-29)의 서술을 머지본 기준으로 고쳐 씀):
  `qexec_next_scan_block_renew_memoize ()`(query_executor.c:8600-8615)가 `qexec_next_scan_block ()` 성공 뒤 `memoize_storage &&
  spec_list->parts != NULL && !XASL_IS_PER_OUTER_ROW (xasl)` 일 때만 `clear_memoize_storage`+`new_memoize_storage` 하고, 이것을 부르는 곳은
  `qexec_next_scan_block_iterations ()`(:8624-8796) 뿐이다. 파티션 안 된 inner 는 block 이 하나라 반복기가 재시작만 하고 memo 를 유지한다
  (갱신하면 outer block 마다 키를 다시 읽고 hit/miss 가 리셋된다 — 머리 주석 :8581-8598). SEMI/ANTI inner 는 반복기가 block 으로 쪼개지
  않는다 — 파티션 순회가 outer 행 하나의 프로브라 match memo 가 전 파티션에 유효하고([CBRD-27465] `64516d22e`), 그 뒤 following join 의
  row memo 도 그 순회 전체에 걸친다([CBRD-27493] `88c88d359`). 행 단위 되감기 `qexec_reset_sa_inner_scan_block ()`(:8813)가 이 둘 전용이다
  (`XASL_IS_PER_OUTER_ROW`, xasl.h:567). PR head 의 "`qexec_next_scan_block ()` 세 지점(되감기·파티션 전진·spec 전진)에서 clear+new" 는
  머지본 [CBRD-27484] `15e7dc8b5` 에 들어가지 않았다(머지 커밋이 #7991 통합 뒤 중복 reset 제거를 명시). — 정소희(.50) 2026-10-28

### px_scan_task (parallel/px_scan/px_scan_task.cpp)

- 인터럽트 검사는 페이지 단위로 올바름(:840). `shared_ptr`는 src/query 전체 0건.
- **`ACCESS_SPEC_TYPE.btid` 는 언팩 때 `indexptr->btid` 를 백업한 컴파일 시점(부모 클래스) BTID 이고, 파티션 프루닝 뒤 `indexptr->btid` 를
  원상 복원하는 원본이다** (.52, PR#8009 head `616c704bd`, 2026-09-29; 머지 [CBRD-27484] `15e7dc8b5`, develop `2d925cb86` 재확인 2026-10-28):
  stream_to_xasl.c:4752 "backup index id"(당시 :4634). 직렬은 `qexec_close_scan ()` 이 `parts != NULL` 일 때 복원하고(query_executor.c:8344-8354,
  당시 :8086), 병렬 워커는 `initialize ()` 에서 `indexptr->btid` 를 파티션 BTID 로 덮어쓴 뒤(px_scan_task.cpp:199-206) `finalize ()` 에서 이
  필드로 **parts 와 무관하게** 복원한다(:535-543). 머지 전에는 `parts != NULL` 일 때만 복원해, 프루닝하지 않은 clone 에 남은 파티션 BTID 가
  XASL cache clone 풀로 새고 그 clone 을 집은 리더가 파티션 BTID 로 프루닝하다 -495(`ER_PT_EXECUTE`) 레이스를 냈다
  (`heap_get_indexinfo_of_btid ()` 가 에러 설정 없이 거절 — 머지본 주석). — 정소희(.50) 2026-10-28
- **병렬 스캔 워커(MERGEABLE_LIST/BUILDVALUE_OPT)가 clone 위에서 연 스캔은 `finalize ()` 의 `qexec_clear_xasl ()` 이 닫는다 — `curr_spec` 이
  NULL 로 남던 구멍은 [CBRD-27485] `f1bd99ed4` 가 막았다** (수정됨: `f1bd99ed4` CBRD-27485 — .52 PR#8009 head `616c704bd` 2026-09-29 의 정적
  의심 "워커 경로에서 `scan_close_scan ()` 을 못 찾았다"를 develop `2d925cb86` 에서 정적 재확인 2026-10-28): 워커가 `scan_close_scan ()` 을
  직접 부르는 것은 XASL_SNAPSHOT 뿐이지만(px_scan_task.cpp:553-559), `finalize ()` 끝의 `qexec_clear_xasl ()`(:574·:577)이 BUILDLIST/
  BUILDVALUE/SCAN_PROC 의 `curr_spec` 을 `scan_end_scan`+`scan_close_scan` 하고(query_executor.c:2563-2567·:2665-2669·:2689-2693) scan_ptr
  체인으로 내려간다(:2466). 비커버링 인덱스 워커가 잡는 oid 버퍼(`scan_alloc_iscan_oid_buf_list ()`, scan_manager.c:3422)와 key_vals·copy_buf 는
  `scan_close_scan ()`(:5242-5269)만 놓고 `qexec_clear_access_spec_list ()` 는 놓지 않으므로, 마지막 파티션을 지나 `curr_spec` 이 NULL 이 된
  파티션 SEMI/ANTI inner 는 닫히지 않던 자리다 — `f1bd99ed4` 가 `finalize ()` 에서 `curr_spec` 을 `spec_list` 로 되돌린다(px_scan_task.cpp:522-528 — 그 뒤 [CBRD-27493] `88c88d359` 가 following join 까지 넓힘).
  — 정소희(.50) 2026-10-28
- **병렬 워커는 부모 트랜잭션의 `tran_index` 를 복사해 쓴다** — CBRD-25447 병렬 힙 스캔(2025-05-21)부터. "트랜잭션 = 스레드 하나" 를
  전제한 TDES 하위 상태(대기 시간·잠금 대기 등)가 여러 스레드에 공유되며 깨진 결함 계열이 CBRD-26571·27308·27198·27183/27486 이다 —
  TDES 필드를 새로 읽고 쓰는 변경은 워커 스레드에서도 불리는지 본다(src-thread §2 「entry_manager::retire_context / recycle_context」,
  src-transaction §2 대기 시간 조회) (.52, PR#8034 리뷰, 2026-10-01). — 정소희(.50) 2026-10-28

### scan_next_heap_scan (scan_manager.c:5683)

- **힙 스캔의 기본은 PEEK 이고 술어 평가 뒤 페이지 LSA 가 바뀌면 COPY 로 재시도한다** (.52, `a7a1db84b`, 2026-09-16; develop `2d925cb86`
  재확인 2026-10-28): `scan_next_heap_scan` 이 `is_peeking = scan_id->fixed`(= `ACCESS_SPEC_TYPE.fixed_scan`, xasl.h:1104 → develop :1131;
  `grouped` 면 PEEK)로 `heap_next` 를 부르고, `eval_data_filter` 뒤 `PGBUF_IS_PAGE_CHANGED (page_watcher.pgptr, &ref_lsa)` 면
  `is_peeking = COPY` 로 같은 OID 를 다시 읽는다(scan_manager.c:5905-5989 → develop :5719·:5796-5802; rest 값·레코드 정보를 읽은 뒤에도 같은
  재시도 :5975-6036). 병렬 슬롯 반복기도 같은 재시도를 따로 갖고 있다(px_scan_slot_iterator.cpp:127-133). 실행기가 pgbuf LSA 를 직접 보는
  자리 — 경계 누수. ✅ 스캔 매니저에 pgbuf/RECDES 타입을 더 노출하는 변경은 이 자리를 넓힌다. — 정소희(.50) 2026-10-28

### scan_next_scan_local — NL semi/anti inner 의 첫 매치 정지 (`QPROC_SINGLE_INNER`, scan_manager.c:7550)

- **`QPROC_SINGLE_INNER` 게이트는 배치를 다 읽은 뒤에야 듣는다 — 그래서 [CBRD-27465] `64516d22e`(PR#7991)가 NL semi/anti inner 인덱스
  스캔에 key limit 1 을 건다** (.51, PR#7991 head, 2026-09-22; 머지 `64516d22e`, develop `2d925cb86` 재확인 2026-10-28): 게이트
  (scan_manager.c:7550-7570)는 `single_fetched` 뒤의 **재진입**만 S_END 로 막는다. 인덱스 접근은 `scan_get_index_oidset ()`(:2430)이 OID
  배치를 채우고 `curr_oidp` 로 훑으므로 `next_scan` 1회가 이미 배치 하나를 읽는다. 머지본은 optimizer 쪽 `add_semi_anti_key_limit ()`
  (optimizer/plan_generation.c:923-939, 주석 "the join-level first-match gate (QPROC_SINGLE_INNER) does not stop the btree: it only stops
  re-entry after the batch is read")를 `mark_access_as_semi_anti_join ()`(:1027)에서 부르되, inner XASL 에 `if_pred`·`after_join_pred`·
  `bptr/dptr/fptr` 가 없고 spec 에 `where_pred` 가 없을 때 ISS·loose scan 이 아닌 `ACCESS_METHOD_INDEX` 에만 건다(:1039-1063).
  — 정소희(.50) 2026-10-28
- **힙(순차) inner 는 게이트만으로 끊긴다** (.51, `CBRD-27251` 로컬 트리, 2026-09-22 — 코드 판독, 실측 재확인 안 함; develop `2d925cb86`
  재확인 2026-10-28): `S_HEAP_SCAN → scan_next_heap_scan ()` 은 자격 행 하나마다 `S_SUCCESS` 를 돌려주므로(scan_manager.c:6043) 배치 초과
  읽기가 없다 — key limit 이 인덱스 접근에만 붙는 것(plan_generation.c:1054-1055)과 일관된다. — 정소희(.50) 2026-10-28
- **key limit 은 outer 행마다 재무장된다** (.51, PR#7991 head, 2026-09-22; develop `2d925cb86` 재확인 2026-10-28): `scan_reset_scan_block ()`
  (scan_manager.c:4683) → `scan_init_index_key_limit ()`(:4764, 당시 :4944). 그래서 상수 1 로 충분하고 조인 결과가 1행으로 잘리지 않는다
  (머지본 `add_semi_anti_key_limit ()` 머리 주석도 같은 근거). `key_limit_reset` 플래그는 **다른 축**이다 — 한 스캔 안에서 range 마다 다시
  줄지 여부(`scan_get_index_oidset ()` :2746·:2779·:2819·:2899). 사용자 KEYLIMIT 이 이미 있으면 LEAST() 로 합치고 `key_limit_reset` 은
  건드리지 않는다(plan_generation.c:935-936 주석). — 정소희(.50) 2026-10-28
- **해시조인 SEMI/ANTI 의 프로브는 첫 매치에서 build 체인 훑기를 멈춘다** (수정됨: [CBRD-27379] `8ea02c8e8`(#8001, 2026-10-16) — .51
  2026-09-22 에 "미확인·미조사"로 남긴 질문을 develop `2d925cb86` 에서 정적 확인 2026-10-28): 직렬 query_hash_join.c:3633-3637(SEMI — 매치
  1건을 결과에 쓴 뒤 `qfile_slot_reset` + break)·:3939-3946(ANTI — during-join 술어를 통과한 매치 1건이면 break, 그 행은 억제), 병렬
  px_hash_join_task_manager.cpp:1085-1087·:1438-1440 이 같은 형태다. NL 경로는 `mark_access_as_semi_anti_join ()` 이 inner scan proc 의 spec
  전부에 `QPROC_SINGLE_INNER` 를 다므로(plan_generation.c:1049-1052) 리스트 inner(해시 리스트 스캔 포함)도 같은 게이트를 지난다(정적 판독,
  실측 미확인). — 정소희(.50) 2026-10-28

### qmgr_get_new_page (query_manager.c:2922)

- **리스트 파일은 `QMGR_TEMP_FILE.membuf` 메모리 페이지를 먼저 쓰고 `membuf_npages` 를 넘으면 임시 볼륨 페이지로 간다** (.52, `a7a1db84b`,
  2026-09-16; develop `2d925cb86` 재확인 2026-10-28): `qmgr_get_new_page`(query_manager.c:2870-2882 → develop :2933-2939, 소진되면 그때
  `file_create_temp` :2941~), 크기 파라미터 `temp_file_memory_size_in_pages`(system_parameter.c:238 → develop :237). 중간 결과는 처음부터
  파일 페이지 형식이다. — 정소희(.50) 2026-10-28

### float_numeric_db_value_sub / float_numeric_normalize_for_hash (numeric_opfunc.c:2820 / :4117)

- **float NUMERIC 의 뺄셈은 scale 을 `MAX (scale1, scale2)` 로 두고 precision 을 결과 자릿수로 다시 세므로, 음수 scale 과 작은 precision 의
  표현 `(계수 1, p1, s−2)` 가 생기고 float NUMERIC 열이 그대로 저장한다** (.50, `89722cf4e`, 2026-10-27 단위 실측; develop `2d925cb86` 까지
  numeric_opfunc.c 변경 없음): numeric_opfunc.c:2857 `result_scale = MAX (scale1, scale2)`, :2927-2929 "check and recalculate precision/scale
  of the subtraction result"(`float_numeric_get_decimal_digit`). 41자리 이상 정수 리터럴은 p40·s<0 으로 들어온다(:5453-5458 Case 1-B).
  42자리 리터럴 두 개의 뺄셈 → (1, p1, s−2), float NUMERIC 열 캐스트가 유지. 같은 값에 `(1,p1,s−2)`·`(100,p3,s0)` 두 표현이 공존하므로
  해시·같음 키는 `float_numeric_normalize_for_hash ()`(:4117)의 정규화 이미지로 만들어야 한다 — 그 함수는 음수 scale 을 계수에
  10^MIN(−s, 40−p) 를 곱해 없앤다(:4175-4190, 남는 scale = s + MIN(−s, 40−p)). — 정소희(.50) 2026-10-28

### do_update_stats / update_or_drop_histogram_helper (execute_statement.c:4815 / execute_schema.c:4399)

- **컬럼 순회가 서버 왕복을 가로질러 `SM_ATTRIBUTE` 를 들고 있으면 부분 롤백의 decache 로 SIGSEGV 가 난다 — 지금은 위치 기반 순회 +
  이름을 지역 버퍼로 복사한다** (.50, 동적 gdb, 2026-09-18; 수정됨: 브랜치 `2d5a35d24` → [CBRD-27369] `0d0809963`(PR#7900), develop
  `2d925cb86` 재확인 2026-10-28): `tran_abort_upto_system_savepoint` 가 클래스를 decache 하면 `db_get_attributes_force` 로 받은 목록이
  해제된다 — 당시 `execute_schema.c:4408 TP_DOMAIN_TYPE (att->domain)` 에서 6세션 중 5 크래시. develop 은 :4495-4517(주석 "Walk the attributes
  by position, re-reading the list each time, and keep the name in a local buffer"). `do_update_stats ()` 도 같은 이유로 `class_mop->object`
  를 직접 읽지 않고 `au_fetch_class_force ()` 로 다시 받는다(execute_statement.c:4930-4939, [CBRD-26959] `532ce4b6d`, 주석의 CI 크래시
  bug_bts_14492). ✅ 이 경로의 순회·참조는 서버 왕복 사이에 스키마 포인터(`SM_ATTRIBUTE`·`SM_CLASS`)를 들면 안 된다. — 정소희(.50) 2026-10-28
- **문장 시작에 잡아 커밋까지 쥐는 클래스 게이트는 전수 스캔까지 직렬화한다** (.50, 동적, 3회 median, 2026-09-18 — PR#7900 의 설계 대안
  실측; 머지본 `0d0809963`·develop `2d925cb86` 에는 게이트가 없다): 같은 폭풍(80워커×20회)이 게이트+수집 생략 26초, **게이트만 291초(11배)**,
  둘 다 없음 28초. 게이트만 남긴 판에서는 분 단위로 깊어진 대기 줄에서 문장이 `ER_LK_OBJECT_DL_TIMEOUT_SIMPLE_MSG`(-966) 로 간헐 실패(3/4800).
  데드락 제거 자체는 `_db_histogram` 행 X-first(속성 순서)만으로 충분하다 — 게이트 없이 폭풍 3회·ALL CLASSES 8×5 모두 0(develop 의 X-first
  경로는 `db_find_multi_unique_for_update ()`, compat/db_obj.c:1252). — 정소희(.50) 2026-10-28

### `;trace`·플랜 덤프 읽는 법 — JOB 측정에서 확인한 카운터 의미 (query_dump.c / optimizer.h)

> 전제 — 측정 계약 `AK-par4`(.52, develop `07480dfd1` release, 2026-09-18): JOB 113질의(DB `joinorder`), `parallelism=4`·`data_buffer_size=16G`·`taskset -c 0-15`, 21테이블 `UPDATE STATISTICS … WITH FULLSCAN, 300 BUCKETS` 뒤 서버 재기동, recompile 없이 warmup 1패스로 XASL 을 채운 정상상태. 카디널리티는 별도 `qref` 레인(직렬 + 전 스텝 `NO_USE_HASH` + `memoize_memory_limit=0`).

- **`SET OPTIMIZATION LEVEL 514` 는 플랜만 찍고 실행을 건너뛴다** (.52, `07480dfd1`, 2026-09-18): `PLAN_DUMP_ENABLED(level) = level >= 0x100`,
  `OPT_LEVEL(level) = level & 0xff`(`optimizer.h:82-84`, develop 같음). 실측 — 무힌트 19.7초짜리 `16b` 가 **0.017초·0 row** 로 끝나고
  `Query plan:` 블록이 나온다. ✅ 플랜 검증·이웃 열거를 **실행 비용 0** 으로 할 수 있다. 단 `SELECT COUNT(*) FROM t`(무술어)는 아예 플랜을
  생성하지 않고 메타데이터로 답한다(0.85ms vs 술어 있으면 110ms) — 항진 술어(`id IS NOT NULL`)도 제거되어 같은 fast path 로 간다.
  — 정소희(.50) 2026-10-28
- **trace 는 병렬 노드의 실제 수치를 본 줄이 아니라 이어지는 줄에 워커별 범위로 준다** (.52, `07480dfd1`, 2026-09-18):
  `SCAN (table: dba.keyword), (heap time: 10600, fetch: 0, ioread: 0, readrows: 0, rows: 0)` 다음 줄에 `(parallel workers: 2, heap time:
  13..10600, readrows: 61257..72913, rows: 61257..72913, gather: buildvalue)`. 본 줄 카운터가 **0** 이므로 이 줄을 안 읽으면 "실제 0행"이라는
  거짓을 쓰게 된다. 워커 2개면 min+max 가 곧 두 워커 값이라 정확하다(61,257+72,913 = 134,170 = `keyword` 전체 행수). ✅ — 정소희(.50) 2026-10-28
- **실현 병렬도가 trace 텍스트에 찍힌다 — 설정값이 아니라 실제로 쓴 스레드 수다** (.52, `07480dfd1`): `query_dump.c:3855`
  `fprintf(fp, ", parallel workers: %d)\n", xasl_p->executed_parallelism)`(develop :4520), 값의 출처는 `query_hash_join.c:197/:215`(develop
  :194/:212)의 `manager.num_parallel_threads`. 조건은 `stats_group.status == HASHJOIN_STATUS_PARALLEL && executed_parallelism > 1`. 병렬 스캔은
  `query_dump.c:3737` 의 `dump_stats_text`. ✅ 병렬도는 힌트로 못 박지 못하지만 **관측해서 리비전 간 달라지면 무효 표시**할 수 있다.
  — 정소희(.50) 2026-10-28
- **해시조인 플랜의 trace 는 구조가 다르다 — HASHJOIN / BUILD / PROBE / SUBQUERY 노드가 있고 중첩 SELECT 가 나온다** (.52, `07480dfd1`):
  `BUILD (time, fetch, ioread, rows, method: memory)` 가 **빌드 측 행수와 방법**을 준다. ⚠ 루트 SELECT 는 **첫 번째**다 — 중첩 SUBQUERY 안에도
  SELECT 가 있어 마지막을 집으면 서브질의 시간을 전체 시간으로 오인한다(`8c` 가 15,885ms 인데 19ms 로 잘못 읽혔다). ✅ — 정소희(.50) 2026-10-28
- **`memoize_memory_limit=0` 이면 MEMOIZE 가 꺼지고, 세션에서 바꿀 수 있다** (.52, `07480dfd1`): `memoize.cpp:1046-1050`
  `if (storage_size == 0) return NO_ERROR;`(develop :1346). 파라미터 플래그는 `PRM_USER_CHANGE | PRM_FOR_CLIENT | PRM_FOR_SERVER |
  PRM_FOR_SESSION | PRM_FOR_QRY_STRING | PRM_SIZE_UNIT`(`system_parameter.c:5418-5419`, 기본 2MB) — `PRM_FOR_QRY_STRING` 이라 세션에서 바꾸면
  SELECT 의 XASL 캐시 키도 달라진다(위 「xcache 계열」). ✅ MEMOIZE 가 켜져 있으면 작은 차원 테이블의 PK 룩업이 히트로 걷혀 스캔의 `rows` 가
  조인 출력보다 작게 나온다(`1a`: hit 145 / miss 2) — 스텝별 카디널리티 오차가 `÷18267`, `×31071` 처럼 허위로 튄다. 카디널리티 검증에는
  반드시 꺼야 한다. — 정소희(.50) 2026-10-28
- **인덱스 스캔 리프의 감소는 4단계이고 각 단계가 다른 trace 카운터로 나온다** (.52, `07480dfd1`): ① 키레인지(조인 술어) = `readkeys`
  ② 키 필터 = `readkeys → filteredkeys` ③ 힙 lookup = `btree rows` ④ 데이터 필터 = `btree rows → lookup rows`. ✅ "필터 선택도가 틀렸다"를
  판정할 때 ②와 ④를 합쳐 보면 안 되고, 조인 선택도를 계산할 때는 ②④를 **모두 나눠 빼야** 한다(안 빼면 그 감소가 조인 오차로 잘못 찍힌다 —
  `16a` `mc` 가 ÷11.72 로 보였지만 빼면 ÷2.65). — 정소희(.50) 2026-10-28
- **이너 리프의 필터 선택도는 무조건부가 아니다** (.52, `07480dfd1`): left-deep 에서 첫 테이블(구동 리프)만 전수 스캔되고 나머지는 조인 키로
  프로브된 행만 읽는다. 따라서 이너 리프의 측정 통과율은 **그 조인 키에 조건부**이고 옵티마이저의 테이블 전체 기준 `sel` 과 같은 것을 재는
  게 아니다. `16a` `t`: 추정 2.70e-02 vs 측정 3.49e-03(÷7.75) — 필터가 진짜 선택적인지 조인이 유별난 부분집합을 데려온 것인지 이 값만으로는
  못 가른다. ✅ — 정소희(.50) 2026-10-28
- **JOB 워크로드는 AK-par4 계약에서 IO bound 가 아니라 CPU·버퍼풀 bound 다** (.52, `07480dfd1`, 2026-09-18): 113질의 중 루트 `ioread > 0` 이
  11개, 스캔 노드 977개 중 26개뿐. 스캔 `fetch`(논리 페이지) 총합은 2억 322만. `data_buffer_size=16G` + warmup 1패스면 작업 집합이 버퍼풀에
  올라간다. ✅ 비용모델의 IO 항이 사실상 무력한 상태에서 CPU 항만으로 비용이 결정된다 — src-optimizer §3 의 행수 의존 항 결함을 해석할 때
  전제. — 정소희(.50) 2026-10-28

### expr_compile 계열 (**develop `b8199438e` 에 머지됨 — PR#7658 squash, 2026-10-16**; 아래 서술은 브랜치 시절 리비전 기준)

> 아래 항목의 심볼(`expr_compile.c`/`.h`, `expr_scan_pred_compile`, `expr_k_fallback`,
> `EXPR_ARG_ENCODE`, 캐리어 필드 `eval_prog`/`operand_prog`/`scan_prog`/`acc_kernel`/`sum_state`,
> `qdata_numeric_sum_flush`, `EXPR_COMPILE` trace 덤프)은 **develop 95b79e7ed에 존재하지 않는다**
> (git grep 0건 확인). PR#7658 / CBRD-27215의 식 컴파일 작업은
> `feature/expression-compile`(당시 head `3dad3ba82`)에만 있다. 행번호·수치는 기준: CBRD-27094
> @ faf5a3b2a(행번호 재검증됨) 또는 해당 브랜치.

#### 브랜치 한정 지형

브랜치 diff는 신규 `src/query/expr_compile.c`(3,006 LOC) + `src/query/expr_compile.h`(243 LOC)에
기존 18파일 수정, 총 20파일 +4,876/−53이며, 부수적으로 `src/storage/heap_file.c`(+417)와
`src/query/numeric_opfunc.c`(+186)까지 건드린다. `expr_compile`는 `cubrid/`(SERVER)와 `sa/`
CMakeLists에만 등록되고 `cs/`에는 없다.
- ✅ **리뷰 체크포인트**: 이 모듈 관련 지적을 받으면 먼저 어느 브랜치 기준인지 확인할 것 — develop 기준 리뷰라면 해당 코드 자체가 없다.

#### 커널은 인터프리트 원본과 **coercion mode**까지 맞춰야 한다 (.50 실측 2026-08-27)

식 컴파일 커널이 인터프리트 경로를 "미러링"할 때, 같은 이름의 함수를 부르는 것만으로는 부족하다.
`tp_value_cast()` / `tp_value_cast_force()`처럼 **모드만 다른 쌍**이 있고, 어느 쪽을 쓰느냐가
결과를 바꾼다.

- `object_domain.c:10081` `tp_value_cast()` = `TP_EXPLICIT_COERCION`
- `object_domain.c:10090` `tp_value_cast_force()` = `TP_FORCE_COERCION`
- 갈리는 지점은 **절단(truncation)** 하나다. `object_domain.c:9097 / :9162 / :9198` 세 곳 모두
  `data_stat == DATA_STATUS_TRUNCATED && coercion_mode != TP_FORCE_COERCION && (…)`
  → `DOMAIN_OVERFLOW` → `object_domain.c:11612`에서 `ER_IT_DATA_OVERFLOW (-427)`.
  FORCE면 조용히 자르고 끝난다.

인터프리트 원본(`fetch.c` T_CAST / T_CAST_WRAP arm)의 규칙:
```c
if (REGU_VARIABLE_IS_FLAGED (regu_var, REGU_VARIABLE_STRICT_TYPE_CAST)
    && arithptr->opcode == T_CAST_WRAP)
  dom_status = tp_value_cast (…);          /* 이 한 조합만 비-force */
else
  dom_status = tp_value_cast_force (…);    /* 사용자가 쓴 명시적 CAST는 항상 이쪽 */
```
즉 **비-force는 `STRICT_TYPE_CAST`가 붙은 `T_CAST_WRAP` 전용**이고, 그 opcode는 애초에 컴파일
대상이 아니다(컴파일러의 T_CAST arm은 `opcode == T_CAST`만 받는다).

실제 사고: `expr_k_cast()`가 `tp_value_cast()`를 불러 **잘리는 CAST 전부**가 -427로 깨졌다.
BIT 한정처럼 보였으나(`cast('00001111' as bit(8))`) 실제로는 축소 VARCHAR/CHAR
(`cast('abcdef' as char(2))`, ENUM→CHAR 절단)도 같이 깨진 광범위한 회귀였다. 안 잘리는
CAST(`bit(64)` 등)는 두 모드가 같은 값을 내 정상으로 보여 증상이 좁아 보였다.

- ✅ **리뷰 체크포인트**: 커널이 인터프리트 경로를 미러링한다고 주장하면, 호출 함수 이름이 같은지가
  아니라 **인터프리트 쪽의 분기 조건 전체**(플래그·opcode)를 옮겼는지 확인할 것. 특히
  `_force` 접미사 쌍은 실패 모드가 "에러 vs 조용한 절단"으로 갈려 정상 케이스 테스트를 통과한다.
- ✅ **리뷰 체크포인트**: "잘리지 않는 입력"만 테스트하면 이 부류는 안 잡힌다. CAST 커널 검증에는
  **타깃 도메인보다 긴 입력**을 반드시 넣을 것.
- ⚠ **같은 arm의 미러링 갭 2건 (미수정, 현재는 결과 동일)**:
  ① `fetch.c`는 `REGU_VARIABLE_APPLY_COLLATION`이 서면 CAST를 **하지 않고** `pr_clone_value()` +
  `db_string_put_cs_and_collation()`만 하는데, 컴파일 쪽은 이 플래그를 검사하지 않는다.
  ② 도메인 출처가 인터프리트는 `arithptr->domain`, 커널은 `regu->domain`이다.

#### 엔진 쪽 훅은 전부 동일한 3-상태 lazy 패턴 (컴파일 실패 = 영구 인터프리터 폴백)

프로그램 상태는 `0 = untried / 1 = active / 2 = disabled`이고, 컴파일에 실패하면 `state = 2`로
두어 이후 영구히 인터프리터로 떨어진다(재시도 없음). 훅 위치는
`query_evaluator.c:2964-2976`(scan filter, `expr_scan_pred_compile`/`expr_scan_pred_eval`),
`query_opfunc.c:493-517`(프로젝션 `qdata_valptr_prog_ensure`), `query_aggregate.cpp:1074-1078`
(집계 operand), `px_scan_result_handler.cpp:1971-1989`(병렬 BUILDVALUE), 해제는
`query_executor.c:1784`(scan_prog)와 `:2303`(operand_prog) 두 곳, 덤프는
`query_dump.c:3761-3821`이다. 단 예외가 하나 있다 — 호스트변수 도메인 시그니처가 어긋나면
(`expr_prog_signature_ok`) `state`를 0으로 되돌려 **1회 재컴파일**한다(`query_opfunc.c:507-513`,
`px_scan_result_handler.cpp:1978-1986`).
- ✅ **리뷰 체크포인트**: 새 훅이 추가되면 실패→state=2 영구 폴백인지, 시그니처 불일치→state=0 1회 재컴파일인지 두 전이를 구분해 보고, `query_executor.c`의 해제 경로가 짝을 이루는지 확인할 것.

#### 컴파일 산출물 캐리어 필드는 전부 `void*`라 XASL 헤더에 의존이 생기지 않는다

`regu_var.hpp`의 `void *eval_prog` / `int *eval_prog_idx` / `int eval_prog_state`,
`xasl_aggregate.hpp`의 `void *operand_prog` / `operand_prog_idx` / `operand_prog_state` /
`operand_prog_base` / `void *acc_kernel` / `void *sum_state`, `xasl_predicate.hpp`의
`void *scan_prog` / `int scan_prog_state`가 모두 `void*`로 선언되어 세 헤더가 `expr_compile.h`를
include하지 않는다. 주석에 "server-side runtime state, never serialized"가 명시돼 있듯 직렬화
대상이 아니다.
- ✅ **리뷰 체크포인트**: 캐리어 필드를 구체 타입으로 바꾸는 변경이 오면 XASL 헤더 3종에 새 헤더 의존이 생기는지, 직렬화(`xasl_to_stream`/`stream_to_xasl`)에 실려 들어가지 않는지 확인할 것.

#### expr_compile.c는 엔진 표준 할당자를 쓰지 않아 restrack 가시성 밖이다

`expr_compile.c`에는 `db_private_alloc` 호출이 0회이고 raw `malloc` 15회, `posix_memalign`
1회(slot 배열 캐시라인 정렬)를 쓴다. 즉 이 모듈의 할당은 엔진 자원 추적기(restrack)가 잡아주지
않으므로 누수·이중해제를 자동 검출에 기댈 수 없다.
develop `2d925cb86`(머지본) 재확인 2026-10-28: `db_private_alloc` 0곳·raw `malloc` 20곳·`posix_memalign` 0곳 — slot 배열은
`cub_aligned_alloc ()`(:5383)로 잡고 `memory_wrapper.hpp` 를 마지막(:59)에 include 하므로, SERVER_MODE 에서는 memmon 이 이 파일의 할당을
파일:줄로 집계한다(래퍼 규칙은 위 「XASL clone 보관·폐기와 clear 표시 규칙」 절의 메모리 래퍼). — 정소희(.50) 2026-10-28
- ✅ **리뷰 체크포인트**: 엔진 코드에서 raw malloc/posix_memalign을 쓰는 신규 모듈은 (a) 왜 `db_private_alloc`이 아닌지 근거, (b) 해제 경로가 전부 짝지어졌는지를 수동으로 대조할 것.

#### 컴파일된 경로는 엔진 인터프리터로 역방향 재진입한다 (단방향 호출이 아님)

`expr_compile.c`는 폴백 스텝과 미커버 술어 항에서 `fetch_peek_dbval`(4곳) /
`fetch_peek_arith`(3곳) / `eval_pred`·`eval_pred_comp0/1/3`(20여 곳, 상당수는 미러링 설명 주석)
계열을 다시 호출한다. 대표 지점은 `expr_compile.c:1012`(comp 리프)과
`:1031-1035`(`expr_k_fallback`)이다. 따라서 컴파일된 경로 안에서도 인터프리터의 peek 수명(빌린
포인터)과 thread/스캔 컨텍스트 전제가 그대로 적용된다.
- ✅ **리뷰 체크포인트**: 재진입 지점마다 peek 반환값을 컴파일 프로그램 슬롯에 저장·재사용하며 수명을 넘기지 않는지 확인할 것.

#### 컴파일 시점과 수명: XASL clone 첫 실행 lazy, decache 시 해제

프로그램은 **XASL clone의 첫 실행 시점에 lazy로** 컴파일된다 — 호스트 변수 타입이 확정된 뒤여야
한다는 게 설계의 핵심 제약이다. 술어 프로그램(`pred_root->scan_prog`)은 클론당 1회 지연 생성되고,
해제는 `qexec_clear_pred()`의 `is_final || XASL_IS_FLAGED (xasl_p, XASL_DECACHE_CLONE)` 분기에서만
한다(브랜치 query_executor.c:1784, 주석: "a clone kept cached keeps its compiled tree"). 캐시에
남는 클론은 컴파일 트리를 유지하는 게 의도된 동작이다. clone 이 아닌 트리(`max_plan_cache_clones=0`·원샷·px 워커)가 프로그램까지
놓는 2패스 규칙은 위 「XASL clone 보관·폐기와 clear 표시 규칙」 절. — 정소희(.50) 2026-10-28
- ✅ **리뷰 체크포인트**: 컴파일 산출물 해제가 clone decache / `qexec_clear_pred(is_final||DECACHE)` 경로에 빠짐없이 걸려 있는지, 호스트변수 타입이 바뀐 재실행에서 옛 프로그램이 재사용되지 않는지 확인할 것.

#### 안전장치는 프로그램 전체 포기가 아니라 노드 단위 폴백(`k_fallback`)

컴파일 화이트리스트 밖 노드는 프로그램을 통째로 버리지 않고 `expr_k_fallback`
(`expr_compile.c:1031`) 스텝이 기존 `fetch_peek_dbval` 경로를 호출한다. 프로젝션에서는 커버되지
않는 컬럼의 `eval_prog_idx` 항목을 −1로 두어 그 컬럼만 인터프리트로 돌린다(`regu_var.hpp` 주석).
술어도 같은 모델로 미커버 항을 interp 리프(`eval_pred_comp0`/`eval_pred`)로 항 단위 폴백한다.
온오프 시스템 파라미터 게이트는 두지 않기로 결정됐다.
- ✅ **리뷰 체크포인트**: 새 노드 타입을 화이트리스트에 넣을 때 폴백 스텝이 여전히 결과 슬롯·도메인 규약을 컴파일 스텝과 동일하게 지키는지 확인할 것.

#### cell-0 인코딩 크래시: `EXPR_ARG_ENCODE`는 1-based여야 한다

커밋1에 잠복해 있던 크래시로, materialize 단계의 NULL 가드가 cell 0을 미변환 상태로 통과시켜
커널이 NULL을 역참조하고 cub_server가 죽었다(재현식 `sum(b+b)`, BUILDVALUE 플랜). 원인은 인자
인코딩이 0을 유효 인덱스와 '미설정' sentinel로 동시에 쓴 것이고, 현재 브랜치 소스는
`#define EXPR_ARG_ENCODE(cell_idx) ((DB_VALUE **) (intptr_t) ((cell_idx) + 1))`
(`expr_compile.c:63`)로 1-based다.
- ✅ **리뷰 체크포인트**: 인덱스 인코딩에 0을 sentinel과 유효값으로 겸용하는 곳이 없는지, materialize/NULL 가드가 모든 cell을 빠짐없이 변환하는지 확인할 것.

#### Codex 봇 P1 2건: 서브쿼리 TYPE_CONSTANT 배선 금지, SA_MODE 집계 필드 미초기화

커밋 `a045e6c88`("review: exclude linked-subquery constants; init SA aggregate fields")이 두 건을
함께 고쳤다. ① 서브쿼리 결과가 담기는 `TYPE_CONSTANT`를 컴파일 타임 wired 상수로 배선하면 실행
시 채워지는 값을 반영하지 못하므로 컴파일 대상에서 제외했다. ② SA_MODE 경로에서 집계 관련 필드가
초기화되지 않은 채 사용되어 `regu_init`을 추가했다.
- ✅ **리뷰 체크포인트**: `TYPE_CONSTANT`를 '값이 고정된 상수'로 취급하는 코드가 서브쿼리/외부 참조 유래 상수까지 삼키지 않는지, 서버 모드에서만 초기화되는 필드가 SA_MODE(csql -S, loaddb)에도 초기화되는지 확인할 것.

#### NUMERIC 중간 도메인은 컴파일 시점 고정 — 정합 기준은 TPC-H 22종 결과 byte 동일

NUMERIC 연산의 중간 도메인(정밀도/스케일)을 컴파일 시점에 확정하는 설계라 인터프리트 경로와 중간
도메인이 어긋나면 결과가 미세하게 달라질 수 있다. 그래서 정합 판정을 '값 근사'가 아니라 **TPC-H
22종 결과 byte 동일**로 잡았고(`/home/cubrid/dev/q22_pass.sh`,
`/home/cubrid/dev/q22_compiled/`·`q22_develop/`), 불일치 패턴이 나오면 그 패턴을 폴백시키는
방침이다. 22/22 byte 동일이 여러 차례 재검증됐다.
- ✅ **리뷰 체크포인트**: NUMERIC이 섞인 식의 중간 도메인 결정 로직을 바꿨다면 22종 byte 동일 재검증 없이는 통과시키지 말 것.

#### P1(식 스텝 엔진)만으로는 이득이 안 난다 — 지배 비용은 operand당 `pr_clone_value`와 행당 `qdata_add_dbval`

커밋1만으로 Q1은 중립(−2.6%)이었고, 게다가 BUILDLIST의 operand가 `TYPE_CONSTANT`라 wired-only
허용이 없어 사실상 no-op 측정이었다. 남는 지배 비용은 ① operand마다 `pr_clone_value`(Q1 기준
7회/행, db_values 벡터로) ② accumulator 가산이 행마다 다시 `qdata_add_dbval`을 타는 것(집계
8개/행)이었다. 그래서 P3(accumulate 타입 커널 + 포인터 직결)가 본게임이었고, acc 커널
4종(generic/sum_bigint/sum_double/sum_numeric) + `acc_kernel` 필드 + resolve + 스플라이스로 Q1
31.87→25.58s(−19.7%, byte 동일)를 얻었다(WIP `8580b0466`).
- ✅ **리뷰 체크포인트**: 집계 경로 변경 시 커널이 붙었는데도 operand 복사(`pr_clone_value`)나 행당 `qdata_add_dbval`이 남아 이득을 상쇄하지 않는지 확인할 것.

#### P1 빠른 개선 2가지: 프롤로그 리터럴 coerce 승격, 에필로그 coerce 스킵

① 리터럴 상수를 프롤로그에서 1회만 coerce한다(예: `1 - l_discount`의 INT 1이 행마다 numeric으로
변환되던 것을 컴파일 타임으로 승격). ② 결과 도메인이 이미 일치하면 에필로그 coerce를 스킵한다 —
INT/BIGINT/DOUBLE은 정적 판정 가능, NUMERIC은 제외. `tp_value_cast`가 동일 타입이면 즉시
리턴한다는 점은 실측 검증됐으므로 스킵 이득은 호출 오버헤드 제거 수준이다.
- ✅ **리뷰 체크포인트**: 상수 피연산자가 행당 변환되는 자리가 남았는지, 에필로그 coerce 스킵 조건이 NUMERIC까지 잘못 포함하지 않는지 확인할 것.

#### 커밋2 범위: CASE/IF 지연 분기, 3치 Kleene 비교, T_PREDICATE, IFNULL/COALESCE

커밋 `04ebb8706`("commit2 WIP: CASE-family and comparison-predicate kernels")에서 CASE/IF의
**지연 분기**(선택되지 않은 분기를 평가하지 않는 가드 패턴), 비교 6종의 3치 Kleene 논리,
T_PREDICATE, IFNULL/COALESCE를 지원했다. 소스에도 규약이 주석으로 남아 있다 —
`expr_compile.c:621`("a NULL side is V_UNKNOWN before any comparison"), `:834`("Kleene AND with
immediate exit on V_FALSE/V_ERROR"), `:927`("V_FALSE and V_UNKNOWN both select the ELSE side, as
in fetch_peek_arith ()"). TPC-H 시간은 예상대로 중립인데 q8/q12의 CASE 식이 스캔으로 이동해
프로젝션 훅 영역에 속하기 때문이다.
- ✅ **리뷰 체크포인트**: CASE/IF 스텝이 미선택 분기를 평가하지 않는지(부작용·에러 발생 차이), 비교의 NULL 처리가 인터프리트 경로와 동일한 3치 논리인지 확인할 것.

#### 스캔 필터 술어 컴파일의 2대 함정: TYPE_POS_VALUE 자동 파라미터화, DATE 리프 부재

커밋 `99cf8d90b`("compile scan-filter predicates once per clone")은 PRED_EXPR → 컴파일 술어
트리를 클론당 1회 생성하고 (타입×연산자) 리프로 디스패치하며, 호스트변수 쪽만 런타임 타입 가드를
둔다. 1차 시도에서 걸린 함정 둘: ① **자동 파라미터화된 리터럴은 `TYPE_POS_VALUE`**라서 이를
제외하면 술어 커버리지가 전멸한다, ② **DATE 리프가 없으면 q12가 +10% 순회귀** — 폴백 오버헤드가
이득을 넘긴다. 미커버 항은 interp 리프(`eval_pred_comp0`/`eval_pred`)로 항 단위 폴백하며, 소스
주석에도 "IS NULL / EXISTS / NULLSAFE / set and list relations keep eval_pred ()"
(`expr_compile.c:1357`), "linked subqueries evaluate through eval_pred_comp3 (); interpreted"
(`:1363`)로 남아 있다.
- ✅ **리뷰 체크포인트**: 술어에 새 타입/연산자를 넣을 때 (타입×연산자) 조합에 구멍이 생겨 자주 쓰이는 술어가 폴백으로 떨어지지 않는지 확인할 것 — 부분 커버리지는 오히려 회귀를 만든다.

#### p2 백로그 4커밋: EXTRACT/NULLIF/DECODE, px BUILDVALUE_OPT 훅, exec-prologue, NUMERIC fixed64

`c009c3c5e`(LIKE) 이후 ff-머지된 4커밋: `05a792536`(EXTRACT over TIME/DATETIME/TIMESTAMP +
NULLIF/DECODE, TORDER 술어 포함), `33687714a`(px BUILDVALUE_OPT 훅 — 병렬 실행 경로의 공백 해소),
`221a3a11e`(**exec-prologue = 호스트변수 관련 준비를 실행당 1회**로), `dcc4c98d2`(NUMERIC 곱셈
single-word/fixed64 경로). 검증은 22/22 byte ×4패스, demodb 벤치 md5 5/5 ×2. TPC-H는 중립이나
demodb 합성벤치(GROUP BY 없는 형태)에서 Q1 −29% / Q2 −15%로 px 공백 해소가 실증됐다.
- ✅ **리뷰 체크포인트**: exec-prologue에 올린 작업이 정말 실행당 불변인지(호스트변수 재바인딩·재실행 시 갱신되는지), NUMERIC fixed64 경로가 오버플로/스케일 경계에서 기존 경로와 결과가 같은지 확인할 것.

#### 감사 잔여분: 죽은 필드 arg3p, `EXPR_BUILD_CTX` 20KB 스택 프레임, px gather alloc 실패

커밋 `3dad3ba82`("audit leftovers: dead step field, oversized stack frame, alloc check")에서 ①
죽은 필드 `arg3p` 제거, ② `EXPR_BUILD_CTX`를 약 20KB 스택 프레임에서 힙으로 이전, ③ px gather
버퍼 alloc 실패 시 size=0으로 자가치유하도록 수정했다. 한편 ALLOC-08(문자열 CAST 결과 슬롯)은
재검토 결과 per-row clear + `prog_free` 시 슬롯 클리어로 인터프리트 경로와 동일한 소유권 모델이라
조치 불요로 판정됐다.
- ✅ **리뷰 체크포인트**: 빌드/컴파일 컨텍스트 구조체를 수 KB 이상 스택에 잡지 말 것, 가변 길이 결과 슬롯은 per-row clear + prog_free 클리어 규약을 지키는지 확인할 것.

#### px 미완 과제 3건 — acc 커널 배선 시 `write_finalize` 앞에 `qdata_numeric_sum_flush`가 선행돼야 한다

남은 병렬 실행 과제: ① acc 커널을 px에 배선하려면 `result_handler<>::write_finalize`(원 메모
px_scan_result_handler.cpp:342; develop에서는 :361 — 행 번호 확인 필요) **앞에**
`qdata_numeric_sum_flush`(브랜치 query_aggregate.cpp:644)가 선행돼야 한다 — NUMERIC 누산기의
지연 캐리를 비워야 부분 결과가 올바르다. ② px가 thread_local을 반복 조회해 ~2.8%를 소모하므로
핸들러에 ctx를 전달하는 구조 개편이 필요하다. ③ px 래치/gather 경합(q21, q18 84s)은 설계 논의가
필요하다.
- ✅ **리뷰 체크포인트**: px 부분 집계 결과를 내보내는 자리에서 NUMERIC 누산기 flush가 선행하는지, thread_local 조회가 행당/호출당 반복되지 않는지 확인할 것.

#### 지연 캐리(`sum_state`)는 value 대신 pending sum을 들고 있다 — 모든 소비자가 flush 후 읽어야 한다

CBRD-27178의 지연 캐리 NUMERIC 누산이 브랜치에 통합돼 `xasl_aggregate.hpp`에 `void *sum_state`가
추가됐고, 주석에 규약이 명시돼 있다 — "While non-NULL it holds the pending sum INSTEAD of value;
every consumer of value materializes it first through `qdata_numeric_sum_flush ()` (finalize,
accumulator merge, hash spill, clear)". 실제로 브랜치 `query_aggregate.cpp:214`(merge),
`:791`/`:832`, `:1803`(finalize), `:2947`/`:3024`(hash spill·clear)에서 flush가 호출된다. 필드가
`curr_cnt` 옆에 배치된 것도 acc 커널이 value/curr_cnt/sum_state를 한 캐시라인에서 읽게 하려는
의도다.
- ✅ **리뷰 체크포인트**: `accumulator.value`를 새로 읽는 코드를 추가하면 그 앞에 `qdata_numeric_sum_flush`가 있는지 반드시 확인할 것.

#### 디버그 빌드 restrack abort — 컴파일된 집계 피연산자의 에러 이탈 경로가 1순위 용의자

PR#7658 head(`dc2a93b4e`, 로컬 미보유)의 `/run all`에서 cub_server가
`src/base/resource_tracker.hpp:455`의 `assert (cond)`(restrack_assert 본체)로 반복 abort했다 —
test_medium 608실패 / test_sql 433실패 / test_shell 199실패 + core 87개. 첫 abort 지점이
`_07_aggregate_functions/_02_var_pop/cases/example.sql` 직전인데 var_pop 계열은 CHAR/BIT 등
비수치 컬럼을 집계해 **타입 에러를 유발**하는 케이스다. 1순위 가설은 컴파일된 집계 피연산자
프로그램이 에러로 이탈할 때 page fix나 추적 할당을 해제하지 않고 빠져나간다는 것이며, 같은 시기
타 PR 기준선은 전부 녹색이라 환경 탓이 아니다.
- ✅ **리뷰 체크포인트**: 식/술어 커널의 **에러 리턴 경로**마다 그 시점까지 잡은 page fix·추적 할당이 해제되는지 한 줄씩 대조할 것 — 정상 경로만 보면 놓친다.

#### 컴파일 여부·폴백 판정은 추측하지 말고 `;trace`의 EXPR_COMPILE 덤프로 확인한다

브랜치의 `query_dump.c`가 `;trace`에 컴파일 상태를 찍는다 — `"EXPR_COMPILE (aggregate operands):
active / interpreted (not covered)"`(`:3765`, `:3769`), `"EXPR_COMPILE (data filter):
active|interpreted"`(`:3793`), 프로젝션은 `"EXPR_COMPILE (%s): active, columns covered %d/%d"`
(`:3819`)로 커버 컬럼 수까지 나온다. 누수 실증도 완료돼 RECOMPILE 400회 반복에서 RSS가 안정이었다.
- ✅ **리뷰 체크포인트**: '이 식이 컴파일됐다/폴백했다'는 주장은 `;trace` 덤프 근거를 요구할 것, 재컴파일 반복에서 RSS 증가가 없는지 회귀 확인할 것.

#### `NULLIF(expr, NULL)` 항등 래핑 A/B 기법은 p2 이후 무효화됐을 수 있다

같은 빌드에서 비컴파일 경로를 강제하려고 `NULLIF(expr, NULL)` 항등 래핑을 A/B 대조군으로
썼는데(래핑 자체 오버헤드가 있어 **상한 대조군**), p2 커밋 `05a792536`이 NULLIF/DECODE를 컴파일
지원 목록에 넣었으므로 이 래핑이 더 이상 인터프리트를 강제하지 못할 수 있다. 순정 대조는 stash +
재빌드가 정확한 방법이다(`/home/cubrid/dev/p3_verify.sh`).
- ✅ **리뷰 체크포인트**: '컴파일 off' 대조군을 만들 때 그 구문이 지금도 화이트리스트 밖인지 `;trace`로 확인할 것 — 화이트리스트가 넓어지면 옛 A/B 트릭이 조용히 무효가 된다.

#### 프로그램 상한·지연 영역·타입 가드 — 2026-09-03 리뷰 대응 후의 컴파일러 계약 (expr_compile.c, 브랜치 `65c0ea90d`)

> **지연 영역 서술은 09-08 `afeda4806`에서 점프 스텝으로 대체됐다** — 아래 "조건부 평가 — 지연 영역에서 점프 스텝으로" 절이 현재 계약. 상한·타입 가드·T_MUL 미러 항목은 유효.

[출처 .50, feature/expression-compile `4aeeae07b`→`65c0ea90d`, PR#7658 HyunukLee 리뷰 5건]

- **스텝/셀 상한 `EXPR_MAX_STEPS`(128)**: 스텝과 셀은 `expr_new_step_with_cell()`로 **함께** 확보한다(셀 먼저, 스텝 실패 시 셀 반납). 루트가
  중간에 거절되면(`expr_compile_node()` < 0) 루트 루프가 `expr_build_rewind()`로 steps/cells/cse/slots를 스냅샷으로 되감고 스텝 소유
  pred를 해제한다 — 이전에는 `cell < 0 || step == NULL` 검사 순서 때문에 커널만 바인드된 반초기화 스텝이 남아 materialize가
  `&cells[-1]`에 쓰고 커널이 NULL 역참조로 죽었다(64+ 표현식 컬럼 SIGSEGV). 상한을 넘은 루트는 fallback 스텝(인터프리트) 또는 프로그램
  전체 포기.
- **지연 영역은 이제 중첩된다**: `EXPR_STEP.region_depth`(0 = 메인 루프, n = n중 영역 안). `expr_run_region(prog,start,n,ctx,depth)`는
  자기 depth의 스텝만 실행하고 안쪽 영역은 그 소유 커널이 돈다. CASE 분기는 `region_depth+1`로 실행.
- **rhs 지연(fetch_peek_arith 단락 미러)**: 이항 산술(ADD/SUB/MUL/DIV)·NULLIF의 rhs는 lhs가 NULL이면, NVL/IFNULL/COALESCE의 rhs는
  lhs가 NULL일 때만 평가된다. 컴파일러는 rhs 서브트리에 **실패 가능 스텝**(`expr_kernel_may_fail()`: leaf_fetch·hostvar·
  coerce_numeric·nvl·extract_* 이외 전부)이 있을 때만 `expr_make_rhs_lazy()`로 그 스텝들을 한 단계 깊은 영역으로 밀고 prologue
  호이스팅을 끄고 CSE 엔트리를 버린 뒤, 노드 커널을 래퍼 `expr_k_lazy_arith / _nullif / _nvl`(영역 [t_start,t_start+t_n) 실행 후
  `step->inner` 호출)로 바꾼다. rhs가 리프/호스트변수/coerce만이면 eager 그대로(결과 동일, 호이스팅 유지) — `a + b`, `n1 * ?` 는 변화 없음,
  `a + b/c`, `l_extendedprice * (1 - l_discount)` 류는 지연. **AND/OR rhs 항**은 피연산자 스텝에 실패 가능 스텝이 있으면 술어 전체를
  거절(인터프리트)한다 — 컴파일된 술어 트리는 피연산자 지연 평가가 없다. 트레이스: `[D n] …` + 노드 줄 `lazy rhs=[a..b)`.
- **T_MUL NUMERIC 미러**: 인터프리트 `qdata_multiply_numeric_to_dbval()`은 SHORT/INT/BIGINT 쪽을 `qdata_multiply_numeric()`(coerce →
  **plain** `numeric_db_value_mul`)으로, NUMERIC×NUMERIC만 `float_numeric_db_value_mul()`로 보낸다(이 함수는 non-NUMERIC 인자를
  `ER_OBJ_INVALID_ARGUMENTS`로 거절). 컴파일러도 혼합이면 coerce 스텝 + `expr_k_mul_numeric_plain`, 순수면 `expr_k_mul_numeric`(fixed64
  fast path 포함). 예전 "곱셈은 모든 조합에서 float, raw 정수 투입" 주석은 틀렸었다(`SUM(n1 * ?)` INT 바인드가 OVERFLOW 에러).
- **타입 드리프트 가드**: 산술 커널의 `EXPR_ARITH_REQUIRE_TYPE`와 같은 검사를 비교 리프(`EXPR_PRED_CMP_LEAF(name,get,op,dbtype)` →
  어긋나면 `expr_pred_cmp_values()` generic), `R_EQ_TORDER` fast path, EXTRACT 커널(`EXPR_EXTRACT_PROLOGUE(src,dbtype)` → 행 단위
  `expr_arith_row_interp`)에 둔다. 근거: 재귀 CTE 앵커/재귀 분기 타입 불일치(`aa82c07d1`).
- **`REGU_VARIABLE_APPLY_COLLATION`** 플래그가 있는 노드는 `expr_compile_node()` 진입에서 거절 — 인터프리트는 cast 대신
  `pr_clone_value` + `db_string_put_cs_and_collation`을 한다(fetch.c T_CAST arm, `fetch_peek_dbval` 후처리).
- ✅ **리뷰 체크포인트**: 새 arm을 추가하면 ① `expr_new_step_with_cell()`만 쓰고 ② rhs가 있으면 lhs→(lhs coerce)→rhs→(rhs coerce)
  순서로 emit해 rhs 범위가 연속되게 하고 `expr_make_rhs_lazy()`를 거치고 ③ 새 커널을 `expr_kernel_may_fail()` 화이트리스트 관점에서
  분류하고 ④ 커널 이름 표(`expr_kernel_name`)에 넣을 것(빠지면 트레이스에 `?`).

### 식 컴파일(expr_compile.c) 리뷰 2차에서 확정된 사실 (.52, PR#7658 be75c0b3a 기준)

- **`TYPE_CONSTANT` 는 plan 상수가 아니다** — 다른 블록 value list 의 `dbvalptr`(fetch.c 에서 `REGU_VARIABLE_FETCH_NOT_CONST`).
  재귀 CTE 는 앵커 도메인(INTEGER) 슬롯을 count() 의 BIGINT 로 다시 채우므로, 타입을 컴파일 시점에 고정하는 코드는
  `TYPE_CONSTANT`/`TYPE_POSITION`/`TYPE_POS_VALUE` 피연산자에 런타임 타입 가드를 둬야 한다. `TYPE_ATTR_ID`·`TYPE_DBVAL` 만 고정.
- **정렬 GROUP BY 는 집계 리스트를 `memcpy` 로 차원별 복사**(`qexec_gby_init_group_dim`) — AGGREGATE_TYPE 에 런타임 소유 포인터를
  추가하면 복사 직후 초기화 + `qexec_gby_clear_group_dim` 해제를 같이 넣어야 한다(해시→정렬 하이브리드는 헤드가 이미 컴파일된 상태로 복사됨).
- **컴파일 산출물 수명은 실행당 1회**: 모든 `qexec_clear_xasl()` 호출자가 `is_final=true` 라 `XASL_DECACHE_CLONE` 조건은 dead.
  준비문 2000회 반복 벤치에서 실행당 컴파일 비용은 측정 한계 이하(1행 형상에서도 PR 이 더 빠름).
- **`eval_pred()` 의 fetch 순서**: 비교 항은 좌항 NULL 이면 우항 미fetch(R_EQ_TORDER·NULLSAFE_EQ 제외), LIKE 는 src NULL 이면 pattern/escape 미fetch,
  AND/OR 는 단락. 컴파일 경로가 이를 미러하려면 우항 스텝이 실패 가능할 때 거절/지연해야 한다.
- **디스크 NUMERIC 헤더 상수 `NUMERIC_HEADER_SIZE`(3)** 는 object_primitive.h 로 export 됨 — heap 디코드 커널과 공유.
- 인터프리터 `qdata_add_int/_bigint`·`qdata_subtract_int/_bigint` 는 wrap-then-check(UB)였고 `OR_ADD/SUB_OVERFLOW` builtin 으로 전환됨.

### 식 컴파일 후속 — 가드 태그 CSE·리터럴 값 CSE·px trace (.52, 2026-09-08, `beedad3e4` 로컬 커밋, PR#7658 미푸시)

- **CSE는 두 곳에서 새고 있었다.** ① 리터럴 CSE 키가 `&regu->value.dbval` 주소라, 플랜에 등장 위치마다 따로 있는
  `TYPE_DBVAL` 노드(`1 - disc`, `1 + tax`의 `1`)가 매번 새 셀이었다 → 그 위에 얹힌 모든 서브식이 CSE 미스.
  ② `expr_build_defer_region()`이 지연 영역의 CSE 엔트리를 `n_cse = cse_mark`로 버렸다.
  TPC-H q1 출력 리스트에서 `ep*(1-disc)`가 두 번(6스텝) 계산된 원인. 수정: 정확 타입 리터럴(SHORT/INT/BIGINT/FLOAT/DOUBLE/
  NUMERIC 동일 p,s/DATE/TIME/TIMESTAMP/DATETIME, NULL 제외)은 `EXPR_CSE_LITERAL`(opcode −3) 엔트리로 **값 비트 비교**
  공유; CSE 엔트리에 `guard` 필드(0 = 무조건 유효, n = `guards[n-1]` = (parent, lhs cell, kind) 트라이 id)를 두고
  `expr_cse_find()`는 `guard == 0 || guard == cur_guard`만 매칭. rhs 컴파일은 `expr_rhs_begin()`/`expr_rhs_end()`로
  감싸고(kind: `EXPR_GUARD_LHS_NOT_NULL` 산술·NULLIF, `EXPR_GUARD_LHS_NULL` NVL), eager로 남은 rhs의 엔트리는
  둘러싼 가드로 재태깅. 결과 q1 4스텝, root[1]의 lhs = root[0]의 결과 셀. 안전 근거: 같은 가드의 영역은 정확히 같은
  행에서 돌고 생산자가 스텝 순서상 앞. CASE 분기는 종전대로 `n_cse` 리셋(분기 간 공유 없음).
- ✅ **리뷰 체크포인트**: CSE 엔트리를 새로 만드는 arm은 `guard`를 넘겨야 한다 — 와이어드 셀(상수·호스트변수)은 0, 스텝 결과는
  `bctx->cur_guard`. 가드 테이블이 가득 차면(`expr_rhs_begin() < 0`) 노드를 거절한다.
- **float NUMERIC `+ - *`는 실질적으로 실패하지 않는다** — `float_numeric_check_overflow_and_adjust_scale()`은 정밀도 > 40이면
  스케일을 줄이고 `scale < DB_MIN_NUMERIC_SCALE(−214)`일 때만 에러, `float_numeric_round_and_pack()`도 같은 조건. 기본
  정밀도(`DB_DEFAULT_NUMERIC_PRECISION`=40) 도메인으로의 coerce는 `numeric_coerce_num_to_num()`이 값을 그대로 둔다.
  38자리 × 38자리 × 38자리도 에러 없이 값(스케일 음수)이 나온다(TC `cbrd_27215_numeric_eager_rhs`). 따라서 lazy 영역의
  실질 효용은 나눗셈·정수 오버플로·CAST 쪽이다. "오버플로 불가 증명으로 eager 전환" 안은 서버측 컬럼 참조가 `TYPE_CONSTANT`
  (드리프트 가능)라 채택하지 않았다.
- **px 실행의 `;trace`에는 EXPR_COMPILE 절이 없었다** — 프로그램은 워커 클론 소유·해제라 코디네이터 XASL은 state 0.
  수정: `px_scan_task.cpp`의 on_trace 블록(`merge_xasl_tree` 직후, `qexec_clear_xasl` 전)에서
  `trace_handler::add_expr_compile_dump(m_xasl)` → `open_memstream` + `qdump_print_expr_compile_text(fp, xasl, 0, " [px worker]")`
  (query_dump.c에서 export, tag 인자 추가) → 첫 워커 것만 보관 → `accumulative_trace_storage::add_stats`가 복사 →
  `dump_stats_text`가 "(parallel workers …)" 줄 아래 같은 indent로 출력, JSON은 `expr_compile` 문자열.
  워커 프로그램 포인터를 코디네이터로 옮기는 방식은 불가 — 셀이 워커 클론 메모리(`dbvalptr`)에 배선돼 있어 클론 해제 후 dangling.
- ✅ **리뷰 체크포인트**: 병렬 플랜의 컴파일 여부 판정은 `[px worker]` 태그 절로 한다. 절이 없으면 워커가 0행이었거나 trace off.

### 스캔 필터 확장 — 피연산자 스텝 컴파일·리터럴 고정·필터→소비자 공유 (.52, 2026-09-08, `f97766b6f`)

- **필터 트리가 프로그램을 소유한다**: `expr_scan_pred_compile(thread, pr, vd)`(vd 인자 추가)가 `EXPR_BUILD_CTX`를 만들어
  `expr_scan_pred_build(bctx, …, shareable)`로 트리를 짓고, 비교 리프의 산술 쪽은 `expr_scan_side_compile()`이
  `expr_compile_node()`로 컴파일한 뒤 `expr_build_defer_region()`으로 **리프별 지연 영역**(가드 `EXPR_GUARD_SCAN_SIDE`,
  키 `-(++scan_side_seq)` → 리프 간 CSE 없음)으로 만든다. `expr_prog_finish(bctx, roots, n_roots, vd, extra_pred)`가
  compile_roots_impl에서 분리돼 루트 0개 프로그램을 만들고 `expr_pred_materialize(pred, prog, remap)`로 리프의
  `lhs/rhs_start`를 remap한다. 평가는 `expr_scan_pred_eval()` → `expr_prog_prepare()`(프롤로그만) → 리프에서
  `expr_scan_side_value()`가 `expr_run_region(depth 1)` 또는 기존 fetch. 해제 `expr_scan_pred_free()`가 prog·share 해제.
- **리터럴 고정(`rhs_pinned`/`pinned_rhs`)**: `t1 != t2`이고 우항이 non-NULL `TYPE_DBVAL`이면 `eval_value_rel_cmp()`의
  상수측 규칙(수치×수치 & `tp_more_general_type(t1,t2) > 0` → `tp_domain_resolve_default(t1)`; 날짜형 vs 문자열 → 좌항 날짜형)을
  컴파일 시 `tp_value_coerce()`로 1회 적용, `fetched2 = &pinned_rhs`. 해석 경로는 첫 행에 리터럴 DB_VALUE를 **in-place**로 바꾸는데
  그 노드는 등장마다 별개라 관측 차이 없음. 좌항이 덜 일반적(INT vs NUMERIC 리터럴)·문자열 vs 수치는 종전대로 해석.
- **공유 레지스트리**: `EXPR_PRED.share[]`(regu, slot) — `expr_scan_pred_share_build()`가 AND/NOT 경로(`shareable` 전파:
  AND 자식·NOT 자식은 유지, OR 자식은 false)의 리프에서 컴파일된 **슬롯 소유 노드**(`bctx->node_cells[]`에 기록, `out != NULL`)만
  등록. 소비자: `expr_prog_compile_roots(…, share_spec)`에 `ACCESS_SPEC_TYPE*`를 넘기면 `expr_share_attach()`가
  `where_pred->scan_prog`(state 1, n_share>0)를 붙이고, `expr_compile_node()` 래퍼가 INARITH 노드마다 `expr_share_find()`
  → `expr_share_same()`(구조 비교; `TYPE_CONSTANT`↔`TYPE_ATTR_ID`는 `expr_share_slot_attr()`이 spec의
  `cls_regu_list_pred/rest`에서 `vfetch_to == dbvalptr`인 ATTR_ID의 id로 대응)로 히트하면 필터 슬롯 주소로 **와이어드 셀**
  (`cell_shared[]`, `prog->n_shared`). `only_compute_roots`의 has_compute와 `qdata_valptr_prog_compile`의 `n_compute==0` 폐기
  조건이 shared를 계산으로 인정.
- **spec 전달**: 캐리어 필드 `valptr_list_node.eval_prog_share_spec`, `aggregate_list_node.operand_prog_share_spec`(헤드).
  `qexec_set_expr_share_spec(xasl, spec)`(query_executor.c, export)이 `xasl->spec_list == spec && spec->next == NULL &&
  scan_ptr == NULL && TARGET_CLASS && where_pred` 일 때 BUILDLIST→`outptr_list`, BUILDVALUE→`agg_list`에 세팅. 호출:
  `qexec_open_scan()` 진입부, px `px_scan_task.cpp` 클론 셋업(`m_scan_id` 직후). **BUILDVALUE의 outptr_list는 제외**(스캔 후
  평가라 마지막 행 값이 됨).
- ✅ **리뷰 체크포인트**: 공유 셀의 유효성은 "통과 행은 AND/NOT 경로 리프를 전부 평가했다"에만 기댄다 — 필터를 우회해 행이 소비자에
  도달하는 경로(예: where_pred가 key filter로 옮겨진 커버링 인덱스)가 생기면 `qexec_set_expr_share_spec` 조건을 다시 봐야 한다.
  검증: 이전 head와 54문장 결과·에러 위치 동일, TPC-H q1/q6/q14/q19 동일(상수는 자동 파라미터화돼 필터 프로그램은 비어 있음).

### 조건부 평가 — 지연 영역에서 점프 스텝으로 (.52, 2026-09-08, `afeda4806`; 09-03 절의 "지연 영역" 서술을 대체)

- **단일 루프 `expr_run_range(prog, start, end, ctx)`**: `steps[i].kernel()`이 `EXPR_JUMPED`(=1)를 돌려주면 `i = ctx->jump`, 아니면 `i++`.
  `expr_prog_eval()`은 `[row_start, n_steps)`를, 스캔 필터 리프는 자기 피연산자 구간을 같은 함수로 돈다. 점프는 **앞으로만** 간다.
- **스텝 필드**: `t_start/t_n/f_start/f_n/deferred/region_depth/inner` 삭제, `jump_to`(구간 경계 인덱스)·`alias_of`(결과 슬롯을 빌려 올
  스텝 인덱스) 추가. `expr_prog_finish()`의 alias 패스가 `steps[i].out = steps[alias_of].out`으로 슬롯을 공유시킨다.
- **점프 커널**: `expr_k_jump_null_arith / _nullif`(lhs NULL → `alias_of` 슬롯을 NULL로 발행, `jump_to`로), `expr_k_jump_notnull_nvl`
  (lhs non-NULL → lhs 발행, rhs 구간 건너뜀), `expr_k_case_branch`(`step->pred` 평가, TRUE 아니면 ELSE 시작으로), `expr_k_jump`(무조건),
  `expr_k_case_pub_select / _cast`(분기 결과를 공통 슬롯으로 발행). trace 표기 `jump_null c0 -> c4 (slot) (slot of [2]) else -> [3]`.
- **끼워 넣기 `expr_build_insert_step(bctx, pos, kernel, cell)`**: 산술 arm은 자식을 다 emit한 뒤 rhs 시작 위치에 검사 스텝을 끼운다.
  기존 스텝의 인덱스가 밀리므로 `jump_to`는 **`> pos`**일 때만 +1(`== pos`는 "끼운 스텝 앞까지" 경계라 끼운 스텝을 포함해야 함),
  `alias_of`는 **`>= pos`**면 +1(밀려난 스텝 자신). 이 둘을 같은 규칙으로 하면 바깥 산술의 NULL 점프가 안쪽 산술의 검사 스텝을 뛰어넘는다
  — `(a*(1-b))*(1+c)`, a NULL 행에서 실측. TC `cbrd_27215_lazy_chain`. P/E/행 재배열 뒤 `jump_to`·`alias_of`를 remap, 배열 끝을 넘는
  `jump_to`는 `n_steps`.
- **CASE 배치**: `case_branch(pred, jump_to=ELSE)` / THEN 스텝 / `case_pub(alias 없음, 슬롯 소유)` / `jump(jump_to=END)` / ELSE 스텝 /
  `case_pub(alias_of=THEN pub)`. 분기 안 CASE 중첩 거절(`in_branch`)은 그대로.
- **가드 CSE와의 관계**: 가드 id 트라이(`parent, lhs cell, kind`)는 그대로다 — 가드는 "이 구간이 도는 조건"이지 실행 방식이 아니므로
  점프 모델에서도 같은 가드 아래 rhs만 재사용한다. `n_compute`는 점프 스텝을 세지 않는다(Q1: `steps: 6 … compute: 4`).
- **검증**: 이전 head 대비 54+12문장 결과·에러 위치 동일, TPC-H q1/q6/q14/q19 동일, CTP `cbrd_27215_*` 14/14 + `lazy_chain`.

### 식 컴파일 머지본 재확인 — 호이스팅 오류 순서·점프 경계·호스트 변수 키·도메인 해석 (.52 2026-09-16 → develop `2d925cb86` 재확인 2026-10-28)

> PR#7658 은 [CBRD-27215] `b8199438e`(2026-10-16)로 머지됐다. 아래 넷은 브랜치(`2628b943d`~`9a13c297d`) 시절 확인한 사실을 develop 에서 다시
> 본 것 — 넷째는 머지본이 다른 방식이라 develop 기준으로 고쳐 썼다.

- **실패 가능 스텝의 호이스팅 조건은 "메인 루프 + 앞에 실패 가능한 행 스텝 없음"** (.52, `9a13c297d`, 2026-09-16; develop expr_compile.c:1812-1853
  재확인): 끌어올린 스텝은 첫 행의 모든 행 스텝보다 먼저 돌므로 `select cast(s as int), 1 / ?`(`'abc'`, 0)에서 두 오류 중 해석 경로가 먼저 내는
  것(cast)을 유지하려면 뒤의 `1/?` 를 행 루프에 남겨야 한다. `expr_step_hoist ()` 가 빌드 순서상 앞 스텝을 `expr_step_is_fallible ()`(:2015)로
  검사하고, 실패 가능 스텝은 가드된 rhs(`cur_guard != 0`)와 CASE 분기 안에서는 끌어올리지 않는다. A/B(develop `519cc1a43` SA 모드) 오류 순서
  프로브 6건 byte 동일, TC `cbrd_27215_hoist_chain` h8~h13. — 정소희(.50) 2026-10-28
- **점프 경계는 `remap[]` 이 아니라 `remap_boundary[]`(그 위치 이후의 첫 행 스텝)로 되메운다** (.52, `2628b943d`, 2026-09-16; develop
  expr_compile.c:5445-5475 재확인): lazy 노드의 NULL 검사 점프가 프롤로그로 올라간 스텝(E 프롤로그의 호스트 변수 읽기)을 가리키면 행 루프가 뒤로
  뛰어 무한 루프 — `a + (? + 1), (? - 1) * n` 은 그 앞 head `68909640f` 에서도 재현된 기존 결함이었다(머지본 주석이 같은 예를 든다).
  — 정소희(.50) 2026-10-28
- **호스트 변수는 위치로 키가 잡힌다 — 값 공유 대상이 아니다** (.52, 2026-09-16 trace 실측; develop `2d925cb86` 재확인): `sum(a*?), sum(a*?)` 는
  셀 두 개 — CSE 키가 `(TYPE_POS_VALUE, 값 인덱스)` 다(expr_compile.c:4559·:4575, 공유 비교 :1719-1720). 리터럴 값 공유(`expr_literal_same ()`,
  :2190)는 NUMERIC 에서 `DB_VALUE_NUMERIC_IS_VALUE_NEGATIVE` 도 비교해야 한다(:2210-2218) — 빠뜨리면 `n * 1.5` 와 `n * -1.5` 가 한 셀(전체 CTP 로
  발견, TC `cbrd_27215_literal_sign`). — 정소희(.50) 2026-10-28
- **호스트 변수가 든 투영·필터의 도메인은 실행 전 resolve_domains 게이트가 정하고, 프로그램은 그 뒤에 lazy 컴파일된다** (develop `2d925cb86`
  정적 확인 2026-10-28 — .52 `2628b943d` 의 브랜치 사실을 머지본 기준으로 고쳐 씀): 컴파일러는 값이 타입을 정하는 노드를 `DB_TYPE_VARIABLE` 로
  두고, `qexec_resolve_domains ()`(query_executor.c:18354-18356, [CBRD-27510] `be683e04c`)가 실행당 1회 main block 전에 해석해 XASL_STATE 에
  넣는다. 프로그램은 그 뒤 첫 행에서 컴파일돼 해석 경로와 같은 해석을 읽고, 게이트가 못 정했거나 '값 없음'(전 행 NULL)으로 정한 노드는 거절한다
  (expr_compile.c:2414-2422 머리 주석, :2488). 브랜치 시절에는 `DB_TYPE_VARIABLE` 도메인이라 호스트 변수가 든 투영·필터가 컴파일되지 않다가
  (D26 이전), 한 행(`EXPR_DOMAIN_DEFER_ROWS`)을 해석 경로에 넘겨 도메인을 받은 뒤 컴파일하고 재실행 때 `qdata_valptr_prog_resolve_domains`·
  `qexec_clear_regu_var` 의 `original_domain` 복원으로 다시 정했다 — 이 세 심볼은 머지본 `b8199438e` 에 없다(git grep 0건).
  — 정소희(.50) 2026-10-28

## 3. 예비 이슈 사항

> 미수정 버그·의심·문서 정정 후보·구조적 한계. 해소되면 삭제가 아니라 "해소됨(커밋/PR)"로 갱신.

- **[해소됨 — 662729b67, .50]** `expr_scan_pred_build()`(expr_compile.c)가 트리 깊이를 세지 않고
  컴파일해, 인터프리트 `eval_pred()`/`fetch_peek_arith()`가 하는 `max_recursion_sql_depth` 카운팅을
  우회했다 — 400 중첩 제한을 거부해야 할 질의가 컴파일 경로에서 그냥 실행됨(shell TC bug_bts_14100
  회귀). 수정: 빌드 중 depth가 한도를 넘으면 컴파일 전체를 거절(NULL) → 인터프리트 폴백으로
  기존 -1137(`ER_MAX_RECURSION_SQL_DEPTH`) 유지. feature/expression-compile 브랜치 한정 결함이었다.
- **[해소됨 — 75ea97b7f, .50]** 컴파일된 정수 나눗셈 커널 `expr_k_div_int`/`expr_k_div_bigint`
  (expr_compile.c)가 0-divide만 검사하고 `INT_MIN / -1`의 오버플로 가드가 없어 기계 나눗셈이
  SIGFPE로 서버를 죽였다(shell TC cbrd_27229 — CBRD-27229가 develop 인터프리트 경로
  `qdata_divide_int/bigint`에 넣은 `OR_CHECK_INT/BIGINT_DIV_OVERFLOW` 가드가 컴파일 커널 신설 시
  누락). 수정: 두 커널에 동일 가드 추가(→ `ER_QPROC_OVERFLOW_DIVISION`). NUMERIC 나눗셈은 develop
  함수 호출이라 원래 안전, DOUBLE 나눗셈은 컴파일 대상이 아님.

- **[해소됨 — 4aeeae07b, .50]** 표현식 컬럼 64개 이상(스텝/셀 128 상한) SELECT·집계에서 반초기화 스텝 잔존으로 cub_server SIGSEGV
  (PR#7658 리뷰). 루트 거절 시 스냅샷 되감기 + 스텝·셀 동시 확보. TC `_13_issues/_26_2h/cbrd_27215_step_limit`.
- **[해소됨 — 4aeeae07b, .50]** `SUM(numeric_col * ?)` 정수 바인드가 "Overflow occurred in multiplication context" — T_MUL만 coerce 생략 +
  float 커널에 raw INTEGER 투입. 혼합은 coerce + plain 커널. TC `cbrd_27215_mul_hostvar`.
- **[해소됨 — 4c71a5c8a, .50]** 컴파일 경로가 인터프리트 단락(산술 lhs NULL·NVL·NULLIF·AND/OR)을 무시해 `a + b/c`가 NULL 대신
  divide-by-zero — rhs 지연 영역 + AND/OR 거절(§2 항목). TC `cbrd_27215_short_circuit`. 남은 갭: AND/OR rhs 피연산자는 지연이 아니라
  거절이라 `CASE WHEN a>0 AND b/c>1 …` 류 술어는 컴파일되지 않는다(성능만 영향).
- **[해소됨 — 4aeeae07b, .50]** 비교 리프·TORDER·EXTRACT 커널의 타입 드리프트 가드 부재(BIGINT를 `db_get_int`로 읽으면 하위 32비트 비교) —
  가드 추가. 실제 드리프트 재현 형상은 재귀 CTE `count()` 케이스만 확인됨.
- **[해소됨 — 4aeeae07b, .50]** `REGU_VARIABLE_APPLY_COLLATION` 미확인 — 거절로 폴백. TC `cbrd_27215_collate`.
- **[수정됨 — `6663cd894` CBRD-27604, 2026-10-15]** `px_scan_slot_iterator.cpp` — `qualified_rows++`가 필터 판정 앞이던
  결함(병렬 heap 스캔의 SET TRACE ON 선택도 무의미). develop `2d925cb86` 에서 `continue` 뒤로 옮겨진 것을 확인했다(§2 같은 항목).
  — 정소희(.50) 2026-10-28
- **[의심 — 작성자 확인 필요]** `px_scan_result_handler.hpp:97`(원 메모 :96)
  `is_list_id_domain_resolved`: 워커 공유 플래그가 워커 전용 도메인 보정을 가드(cpp:885-888).
  develop 95b79e7ed 잔존 확인.
- eval_pred 특수화 커널(eval_fnc)이 query_executor.c의 after_join_pred(:8589)/if_pred(:8604)에
  미적용 — 행마다 제네릭 경로(실측 2.84%). develop 95b79e7ed 잔존 확인.
- 튜플 크기 2회 계산(~2.75%) — `qdata_generate_tuple_desc_for_valptr_list` 계산 후 버림,
  `qdata_copy_db_value_to_tuple_value`+`pr_data_writeval_disk_size` 재계산.
  `QFILE_TUPLE_DESCRIPTOR`에 f_size 배열이면 해소.
- memoize가 직렬 기준 캘리브레이션(1000프로브 후 히트율<0.5 영구 자기비활성)이라 병렬에서 조용히
  자기비활성 가능. develop 95b79e7ed 잔존 확인(memoize.cpp:900대).
- **[미수정 — 결함 후보, 발번 미결]** XASL 캐시 키에 시스템 파라미터 차이를 싣는 것은 `do_prepare_select` 하나다 — `do_prepare_update`/
  `_delete`/`_insert_internal`/`_merge` 의 SHA1 은 `PT_PRINT_DIFFERENT_SYSTEM_PARAMETERS` 없이 계산되므로, `PRM_FOR_QRY_STRING` 파라미터
  (`cost_*`·`max_hash_list_scan_size`·`memoize_memory_limit` 등)를 바꾼 세션도 DML 서버측 플랜은 같은 캐시 엔트리(바인드 변형이면 같은 변형 엔트리 — develop `620ceaf6a`)를 쓴다(근거 §2 「xcache 계열」).
  (.50, `87b25579e`, 2026-09-22; develop `2d925cb86` 재확인 2026-10-28) — 정소희(.50) 2026-10-28
- **[미수정 버그]** `update_or_drop_histogram_helper ()`(execute_schema.c:4399)의 에러 경로가 `error = dump_histogram (…, error, stdout)` 로
  **에러를 덮어써** 세이브포인트 롤백 뒤에도 문장이 `Statistics updated successfully` 로 끝난다 — `dump_histogram ()`
  (optimizer/histogram/histogram_cl.cpp:3905)은 `error != NO_ERROR` 면 메시지만 찍고 `NO_ERROR` 를 돌려준다(:3922-3933). (.50, static + 동적,
  2026-09-18: 동시 첫 수집의 패자 79/1600 이 아무것도 저장하지 않고 성공 보고 — 요청한 `7 BUCKETS` 대신 상대의 283버킷이 남음.)
  [CBRD-27369] `0d0809963`(PR#7900)은 그 트리거만 없앴다 — `sm_add_histogram ()` 이 동시 첫 수집의 `ER_BTREE_UNIQUE_FAILED` 를
  `ER_LC_CLASSNAME_EXIST` 로 번역한다(schema_manager.c:15618-15634). 덮어쓰기 자체는 develop `2d925cb86` 에 그대로다(재확인 2026-10-28):
  `UPDATE STATISTICS` 가 타는 전 컬럼 경로(`target_columns == NULL`, `quiet=true`)는 :4549-4555 에서 `quiet` 와 무관하게 덮어쓰고, 컬럼 지정
  경로는 `!quiet` 일 때만 덮어쓴다(:4718-4729). 그 밖의 `sm_add_histogram ()` 실패(락 타임아웃 등)는 지금도 성공으로 보고된다(정적 판독).
  — 정소희(.50) 2026-10-28

## 4. 진행중인 작업

> 각 컨테이너가 자기 소절을 직접 관리한다. 완료되면 지우지 말고 "완료(PR/커밋)"로 갱신.

### .50
- PR#7658(CBRD-27215) 리뷰 5건 대응 커밋 3개(`4aeeae07b`·`4c71a5c8a`·`65c0ea90d`) — CTP 전체 sql·TPC-H SSOT A/B 후 push 예정 (2026-09-03).

### .51
- PR#7622 검증에서 query 실행 경로 회귀 분류 완료(재블레스 8/보류 19), 후속은 optimizer 쪽 수정 대기.

### .52
- **CBRD-27215 / PR#7658** 식 컴파일 리뷰 대응(.50 → .52 인계): 1차 5건 `0acc72bfb`(09-04), 2차 12건 `be75c0b3a`(09-08) + TC 12건(tc/pr-7658 `a887e6c3e`). 미결: **T6 지연 캐리 NUMERIC SUM 유지 여부 리뷰어 결정** → 확정 후 T7 px BUILDVALUE_OPT sum_state 통일 후속, CI 재실행. 확정 코드 사실은 §2 "식 컴파일 리뷰 2차" 참조. 세션 01ACsuD7 종료.
### .52
- 병렬 스캔(px_*) 계열 분석·버그 제보(qualified_rows, is_list_id_domain_resolved) — 작성자 확인 대기.
