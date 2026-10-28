# src/optimizer

> 기준: upstream/develop 95b79e7ed (2026-08-27)

## 1. 소스 목적 및 사용처 (함수별)

비용 기반 쿼리 플래닝, 클라이언트 측(`#if !defined(SERVER_MODE)`). `query_graph.c`(노드=테이블,
엣지=조인, 서버 통계 로드), `query_planner.c`(QO_ENV→QO_PLAN, 조인 순서 DP·비용 함수·선택도),
`plan_generation.c`(QO_PLAN→XASL 술어 변환), `query_bitset.c`, `histogram/`(HST2 히스토그램
리더·선택도), `rewriter/`(최적화 전 쿼리 재작성). 파이프라인 위치: parser(PT_NODE) →
optimizer(QO_PLAN) → parser/xasl_generation.c(XASL_NODE).

| 함수 | 파일 | 목적 | 주요 사용처(호출자) |
|---|---|---|---|
| `qo_optimize_query` | query_graph.c:365 | 옵티마이저 진입점 — SELECT 하나를 최적화해 QO_PLAN 반환 | parser/xasl_generation.c:1189, :18251 |
| `qo_env_init` | query_graph.c:651 | QO_ENV(노드·세그·term) 초기화 | qo_optimize_query(:386) |
| `qo_analyze_term` | query_graph.c:2013 | term 분류(sarg/join)와 선택도 결정 | qo_add_term(:1775) |
| `qo_get_class_info` | query_graph.c:4894 | 서버에서 클래스/인덱스 통계 로드 | query_graph.c:1295 |
| `qo_get_attr_info` | query_graph.c:5308 | 속성 통계 취득 + PT_NAME 에 히스토그램 blob 주석 | 세그먼트 정보 구성부 |
| `qo_copy_histogram_value` | query_graph.c:5253 | 캐시 소유 히스토그램 blob 의 parser-아레나 복사 | qo_get_attr_info(:5448-5452) |
| `qo_expr_selectivity` | query_planner.c:10126 | 술어 노드별 선택도 디스패치 | qo_analyze_term(query_graph.c:2817), 자기 재귀 |
| `qo_equal_selectivity` | query_planner.c:10572 | `=`/`<=>` 선택도(히스토그램→icard→기본값) | qo_expr_selectivity |
| `qo_between_selectivity` | query_planner.c:11157 | BETWEEN/NOT BETWEEN 선택도(히스토그램 범위) | qo_expr_selectivity(:10203/:10207) |
| `qo_range_selectivity` | query_planner.c:11231 | PT_RANGE(정규화된 범위) 선택도 | qo_expr_selectivity(:10212) |
| `qo_all_some_in_selectivity` | query_planner.c:11431 | IN/ANY/SOME 선택도 | qo_expr_selectivity(:10271/:10276) |
| `qo_like_selectivity` | query_planner.c:10373 | LIKE 선택도(히스토그램→PRM 폴백) | qo_expr_selectivity |
| `qo_index_cardinality` | query_planner.c:11597 | 인덱스 NDV(pkeys) 조회 — 1/icard 폴백의 원천 | qo_equal_selectivity(:10609-10610) 등 |
| `planner_visit_node` | query_planner.c:7564 | 조인 순서 bottom-up DP 의 노드 방문·부착 | planner_permutate(:8561/:8586), 자기 재귀(:8336) |
| `qo_examine_hash_join` | query_planner.c:6818 | 해시 조인 후보 생성·검토 | planner_visit_node(:8262) |
| `qo_join_unit_from_budget` | query_planner.c:9694 | 부분 조인 탐색 폭을 열거 예산으로 결정(CBRD-27142 #7721) | 플래너 탐색 준비부 |
| `qo_plan_compute_cost` | query_planner.c:755 | 플랜 vtbl 의 cost_fn 디스패치 | qo_*_new 계열(:1728, :2110, :2795, :3272, :4022 등) |
| `qo_sscan_cost` | query_planner.c:1742 | 순차 스캔 비용 | 스캔 플랜 vtbl |
| `qo_iscan_cost` | query_planner.c:2249 | 인덱스 스캔 비용(leaf/heap IO 분리) | 스캔 플랜 vtbl |
| `qo_sort_cost` | query_planner.c:2922 | 정렬 비용 | 정렬 플랜 vtbl |
| `qo_nljoin_cost` | query_planner.c:3548 | NL 조인 비용(inner 반복 프로브) | 조인 플랜 vtbl(:6346) |
| `qo_mjoin_cost` | query_planner.c:3705 | 머지 조인 비용 | 조인 플랜 vtbl |
| `qo_hjoin_cost` | query_planner.c:3784 | 해시 조인 비용(빌드/프로브/스필) | 조인 플랜 vtbl(:397-403) |
| `qo_follow_cost` | query_planner.c:4089 | follow(경로식) 비용 | follow 플랜 vtbl |
| `histogram_get_equal_selectivity` | histogram/histogram_cl.cpp:1032 | attr=const 선택도(MCV+버킷) | qo_equal_selectivity(:10634/:10683), histogram_cl.cpp:2653/:2762 |
| `histogram_get_join_selectivity` | histogram/histogram_cl.cpp:1528 | attr=attr 등가조인 선택도 | qo_equal_selectivity(:10602) |
| `histogram_get_like_selectivity` | histogram/histogram_cl.cpp:1824 | LIKE 선택도(MCV+버킷 경계+휴리스틱) | qo_like_selectivity(:10406) |
| `comp_parts` | histogram/histogram_cl.cpp:908 | 범위 비교의 버킷 보간 템플릿 | :1299-1311 에서 int64/double/string_view/uint64 인스턴스화 |
| `HistogramReader::reset` | histogram/histogram_reader.cpp:72 | HST2 blob 파싱·유효성 가드 | histogram_init_reader_from_lhs(histogram_cl.cpp:623), :2977 |
| `qo_extract_or_restrictions` | rewriter/query_rewrite_term.c:4795 | 멀티 spec OR 에서 단일 spec 제약 추출(CBRD-27171 #7613) | rewriter/query_rewrite.c:480 |

`qo_mackert_lohman_pages`(query_planner.c:4292)는 CBRD-27094(#7622, `bacd5d0d2`, 2026-09-11)로 develop 에 들어왔다 — §2 해당 절 참조(develop `2d925cb86` 재확인, 정소희(.50) 2026-10-28).

## 2. 분석 내용 (함수별)

> 항목은 함수 단위로 기술한다 — 각 항목의 제목/선두가 함수·파일명이다. 새 분석도 함수명을 앞세워 추가할 것.
> 행 번호는 develop 95b79e7ed 에서 재확인한 것을 우선 표기했고, develop 에 없는 심볼/코드는
> "(develop 에 없음 — CBRD-27094/PR#7622 계열)" 로 표시했다. 그 계열의 행 번호는 워크트리
> `/home/cubrid/dev/cubrid` 브랜치 `CBRD-27094` @ `faf5a3b2a` 기준이다.
> **2026-10-28 정정**: PR#7622 는 `bacd5d0d2`(2026-09-11)로 develop 에 머지됐다 — 위 "(develop 에 없음 — CBRD-27094/PR#7622 계열)"
> 표기는 그 전(95b79e7ed) 기준이다. develop `2d925cb86` 에는 `qo_mackert_lohman_pages`·`BTREE_DESCENT_PAGE_OVERHEAD`·`iscan_descent_cpu`·
> `QO_EFFECTIVE_CACHE_PAGES`·`SORT_MERGE_FAN_IN` 이 있다. 2026-10-28 환류분은 항목마다 자기 리비전을 단다. — 정소희(.50) 2026-10-28

### 모듈 일반

- 옵티마이저는 클라이언트에서 실행 — 통계만 서버에서 가져오고(`qo_get_class_info()`) 플래닝은 로컬. (AGENTS.md 증류)
- 플랜 열거는 조인 순서에 대한 bottom-up 동적 계획법이고 조인 수에 지수적 — 작지만 복잡도 높은 모듈. 비용 모델은 인덱스 선택도·페이지 I/O·정렬 비용. 함수 접두사 `qo_`. (AGENTS.md 증류)
- 비용 모델 정확도는 최신 통계에 의존 — 오래된 통계 = 나쁜 플랜. (AGENTS.md 증류)
- ✅ **리뷰 체크포인트**: 서버 전용 API(`THREAD_ENTRY` 등)를 호출하지 않는가? (AGENTS.md 증류)
- ✅ **리뷰 체크포인트**: 플랜 열거 변경이 조인 수 증가 시 폭발적 비용을 만들지 않는가? (AGENTS.md 증류)
- ✅ **리뷰 체크포인트**: 비용 산식 변경이 인덱스 스캔 vs 순차 스캔 선택에 미치는 영향을 검토했는가? (AGENTS.md 증류)
- ✅ **리뷰 체크포인트**: 통계가 없거나 오래된 경우의 폴백 동작이 합리적인가? (AGENTS.md 증류)

**`src/optimizer/AGENTS.md` 의 "Fix cost estimation = plan_generation.c" 는 사실과 다르다** — develop 의 Where-to-Look 표에 여전히 그대로 있다(재확인). 실제 비용 함수는 전부 `query_planner.c` 에 있다: `qo_plan_compute_cost`(:755), `qo_sscan_cost`(:1742), `qo_iscan_cost`(:2249), `qo_sort_cost`(:2922), `qo_nljoin_cost`(:3548), `qo_mjoin_cost`(:3705), `qo_hjoin_cost`(:3784), `qo_follow_cost`(:4089). `plan_generation.c` 는 QO_PLAN→XASL 변환·술어 배치 담당이다.
- ✅ **리뷰 체크포인트**: 비용 모델 변경 리뷰는 `plan_generation.c` 가 아니라 `query_planner.c` 의 `qo_*_cost` 계열을 대상으로 잡을 것.

**set optimization level 513 은 플랜 선택을 바꾸지 않는다 (하위 8비트만 레벨)** — `src/optimizer/optimizer.h:82` 의 `OPT_LEVEL(level) = ((level) & 0xff)` 때문에 513 & 0xff = 1 = 기본 레벨이다. `:85 SIMPLE_DUMP 0x100`, `:86 DETAILED_DUMP 0x200` 은 출력 경로에서만 소비된다(develop 재확인). 따라서 덤프에서 관찰한 플랜은 측정 런의 플랜과 동일하다고 단정해도 되고 "덤프라서 플랜이 다를 수 있다"는 유보는 불필요하다.
- ✅ **리뷰 체크포인트**: 하위 8비트를 건드리는 변경만 실제 최적화 레벨을 바꾸므로 플랜 변화 가능성을 검토하고, 상위 비트 변경은 출력 전용으로 볼 것.

**qo_dump 출력에는 기각된 후보 플랜이 섞여 있다 — 최종 플랜은 마지막 `Query plan:` 블록** — 플랜 덤프 파일에는 탐색 중 기각된 후보 플랜이 수만 줄 들어 있다. 최종 채택 플랜은 파일의 마지막 `Query plan:` 블록이며 그 뒤로 `Query stmt:` → 결과셋 → 타이밍 줄이 이어진다. 탐색 중간의 `join_info[...]`/`best:` 항목을 최종 플랜으로 인용하는 것이 가장 흔한 오독이다.
- ✅ **리뷰 체크포인트**: 플랜 관련 주장·버그리포트가 인용한 덤프 조각이 마지막 `Query plan:` 블록에서 나온 것인지 확인하고, 중간 탐색 로그 근거의 결론은 무효로 볼 것.

**저장된 btree NDV 는 실제와 크게 어긋날 수 있다** (실측 587K vs 실제 11) — NDV 기반 선택도·비용을 만지기 전에 통계 신선도부터 확인.

**비용 추정값이 실제 실행시간과 비단조 — 절대 비용 모델이 깨져 있다** — 추정 비용과 실측 시간이 크게 어긋나고 순서(단조성)조차 보존되지 않는다: 17a est ~2494 / 실측 ~41s, 29a est ~1877 / ~68s, 8c est 8.24M / 47s. 즉 비용값은 플랜 간 상대 비교에도 신뢰하기 어렵다. **보강 — 같은 질의 안에서도 비용 순서가 시간 순서와 역전된다(34개 중 어긋남 32 / 일치 0 / 동률 2)** (.52, `07480dfd1`, 2026-09-18, JOB 계약 — 「JOB 실측」 절 첫 줄): 옵티마이저가 고른 플랜(base)과 힌트로 찾은 더 빠른 플랜(best)의 루트 비용·확정 측정 시간을 대조하면 예외 없이 "더 싸다고 본 쪽이 더 느리다" — `16b` 는 비용 6,862 ↔ 856,864(125배 비싸다고 본 쪽)가 17.444s ↔ 3.768s 로 4.6배 빠르고, `17a` 는 4,254 ↔ 209,436 / 7.108s ↔ 1.918s. 어긋난 32개에서 놓친 시간 합계 86.4s. 탐색 실패가 아니라 **비용 함수가 틀린 것**이다 — 플래너는 틀린 함수의 최소값을 정확히 찾고 있다(§3). — 정소희(.50) 2026-10-28
- ✅ **리뷰 체크포인트**: 'CUBRID 비용이 더 낮으니 이 플랜이 맞다'는 논거는 단독으로 채택하지 말 것.

**per-term 선택도를 고쳐도 전체 성능은 그대로였다 → 병목은 카디널리티 전파/비용 모델** — 조인 선택도(`histogram_get_join_selectivity`) 도입 후 항목별 조인 선택도 값(`n.id=ci.person_id` 2.40e-7 등)이 바뀌었는데도 전체 시간은 불변이었다(2026-07-03 A/B: 순서 매칭 28→30/113, 686.0→701.5s(+2.3%), 기하평균비 1.001). 즉 성능을 좌우하는 것은 개별 term 의 선택도가 아니라 조인 트리를 따라 올라가는 카디널리티 전파와 비용 모델 쪽이고, 실제로 17e 는 조인 순서가 바뀌었는데도 8.6초 느려졌다 — 순서 변화가 곧 성능 개선은 아니다.
- ✅ **리뷰 체크포인트**: 선택도 함수 하나를 고치는 PR 이 '카디널리티가 맞아졌으니 빨라질 것'이라 주장하면 의심하고, 개별 sel 정확도와 최종 플랜 품질을 분리해 검증할 것.

**값↔조인 팬아웃 상관 미모델링으로 인한 '정확도 역설'** — 히스토그램 필터 선택도는 uniform 기본값보다 훨씬 정확하다: `k.keyword IN(흔한 키워드 7개)` 5.22e-5 vs uniform 0.00698(134x), `cn.name~'Lionsgate'` 5.21e-5 vs 0.01(192x), `mc.note LIKE '%(Blu-ray)%'` 0.0032 vs 0.1(31x). 그런데 더 느린 순서를 고른다 — 필터가 살려낸 7개 키워드가 mk 에서 팬아웃이 매우 큰 값들인데, 조인 선택도는 값과 무관한 평균 1/NDV 라서 '어떤 값이 살아남았는지'로 조건화되지 않아 k⋈mk 를 과소추정한다(31b 계열; 22a k⋈mk 추정 CUBRID 35 / 실제 37,091). uniform 은 k 필터를 과대추정해 우연히 함정을 피할 뿐이고, per-MCV-value 조인 통계가 없는 것은 단순 버그가 아니라 근본적 옵티마이저 한계다. 수치 근거(`17a` 첫 조인 ×1,231, `mi_idx` ÷1,221)와 "카디널리티 오차의 주범은 미매칭이 아니라 `ncard × sel`" 판정은 §3 「조인 선택도 `1/NDV` 균등 가정」(.52, `07480dfd1`). — 정소희(.50) 2026-10-28
- ✅ **리뷰 체크포인트**: 필터 선택도 정확도 개선이 오히려 느려지는 회귀는 조인 선택도의 값-조건화 부재를 먼저 의심하고, 필터 선택도 코드를 되돌려 '고치는' 변경에는 반대할 것.

**sarg×조인 독립 가정·uniform eq-join 의 구조적 과소추정** — `mi.info='Horror'` 같은 sarg 가 사실상 `info_type_id=genres` 를 함의하는데도 it1 조인 선택도에서 1/113 이 또 곱해지는 구조적 과소추정이 남아 있다(19d 의 divergence 도 voice ⊂ actress 상관 때문). 같은 맥락으로 4a 의 `it⋈mi_idx` eq-join 선택도는 uniform 1/max(NDV)(~1/113)로 나와 실제 대비 ~1000x 과소추정한다. 17a 도 k⋈mk 스큐 과소추정(est 28 vs 실제 41,840)이 실행시간을 지배한다.

### 비용 상수 (query_planner.c 상단)

**비용 상수는 query_planner.c 상단 한 곳에만 정의된다 (동기화 대상 헤더 없음)** — develop 기준 목록: `TEMP_SETUP_COST 5.0`(:80), `QO_CPU_WEIGHT 0.0025`(:81), `ISCAN_OID_ACCESS_OVERHEAD 5`(:84), `FETCH_HEAP_COST 0.25`(:89), `MJ_CPU_OVERHEAD_FACTOR 20`(:90), `HJ_BUILD_CPU_OVERHEAD_FACTOR 40`/`HJ_PROBE_CPU_OVERHEAD_FACTOR 20`(:91-92), `HJ_MEM_ALLOC_CONSTANT 1500`(:93), `HJ_FILE_IO_WEIGHT 0.5`/`HJ_PARTITION_FILL_FACTOR 0.8`/`HJ_HASH_ENTRY_POS_SIZE 12`(:94-103), `ISCAN_IO_HIT_RATIO 0.5`(:104), `SSCAN_DEFAULT_CARD 50`(:105), `GUESSED_BIND_LIMIT_CARD 2000`(:106), `RBO_CHECK_COST 50`/`RBO_CHECK_RATIO 1.2`/`RBO_CHECK_LIMIT_RATIO 10`(:108-110), `QO_COST_EQ`(상대오차 1e-6, :115). `BTREE_DESCENT_PAGE_OVERHEAD`·`QO_EFFECTIVE_CACHE_PAGES`·`SORT_MERGE_FAN_IN` 은 **develop 에 없음(CBRD-27094/PR#7622 계열)**. 과거에 "`query_planner_constants.h` 에도 같은 상수가 있어 양쪽을 동기화해야 한다"고 알려졌으나 이는 오류로 정정됐다 — 그런 헤더는 추적 파일로 존재하지 않고 미추적 백업 `query_planner_constants.h~` 가 grep 에 걸린 것이었다(`git ls-files` 로 확인). 상수 수정은 `query_planner.c` 한 곳으로 끝난다.
- ✅ **리뷰 체크포인트**: 비용 상수 변경 PR 에서 "헤더와 이중 정의 동기화"를 요구하지 말 것.

**correlation(클러스터링 팩터) 미수집 — ISCAN_OID_ACCESS_OVERHEAD 20→5 하향으로 땜질** — 컬럼-물리순서 상관계수를 수집하지도 사용하지도 않아 인덱스 스캔 비용에 클러스터링 팩터가 없다. 보정 수단으로 `ISCAN_OID_ACCESS_OVERHEAD` 를 20 에서 5 로 낮춰 뒀고 바로 위 주석에 TODO 가 달려 있다: "Lowered 20 -> 5 to favor index scan when low/stale leading-column NDV inflates sel via 1/pkeys[0]. TODO: per-index clustering factor."(develop query_planner.c:82-84). 즉 이 상수는 '정확한 값'이 아니라 누락된 correlation 을 흡수하는 보정치이고, correlation plumbing 실험 코드는 stash@{0}(B1)에 남아 있다.
- ✅ **리뷰 체크포인트**: 인덱스 스캔 비용 상수 조정 변경은 correlation 부재를 흡수 중인 5 의 의미를 이해하는지 확인하고, correlation 을 실제 도입하면 이 상수를 원복해 이중 보정을 피할 것.

**QO_EFFECTIVE_CACHE_PAGES 는 512MB 가정값 (이 문단은 CBRD-27094 브랜치 기준 — develop 반영 `bacd5d0d2`, 파라미터화 `fa551431b` 는 아래)** — `QO_EFFECTIVE_CACHE_PAGES = 32768.0`(=512MB, 브랜치 query_planner.c:112)은 하드코딩된 가정값이며 코드 주석이 한계를 자백한다: "matches the data_buffer_pages default … The real parameter is server-only, so the client-side optimizer cannot read it". 같은 값이 `qo_mackert_lohman_pages()` 안의 `b`(:3611-3613)로 다시 나타난다. 서버를 16GB 버퍼로 운영하면 이 가정값이 실제와 32배 어긋난 상태로 비용이 계산된다.
- ✅ **리뷰 체크포인트**: 버퍼 크기 `b` 에 의존하는 비용식 변경은 대용량 버퍼 실측으로 튜닝했다는 주장을 32배 괴리를 감안해 재검토할 것.

**`QO_EFFECTIVE_CACHE_PAGES 32768.0` 은 Mackert-Lohman 의 캐시 가정이고, 서버 `data_buffer_pages` 를 클라이언트가 읽지 못해 상수로 둔 것이다** (.50, 4f0f90b62, 2026-09-21): 4f0f90b62 query_planner.c:132 주석이 그 사정을 밝힌다. PR#7993(CBRD-27126, 머지 `fa551431b`)이 이를 클라이언트 파라미터 `cost_effective_cache_pages`(INT, 페이지 수, 기본 32768, 하한 0)로 노출했다 — develop `2d925cb86` query_planner.c:160 의 `QO_EFFECTIVE_CACHE_PAGES` 가 그 파라미터를 읽는다. `qo_mackert_lohman_pages` 는 b=0 이면 T>b 분기에서 lim=0 → `pages_fetched = N` 으로 안전하게 퇴화한다(0 나눗셈 없음; 함수 안 주석 :4294-4296). — 정소희(.50) 2026-10-28

**기본 선택도 상수 (EQ 0.001 / COMP 0.1)** — 통계가 없을 때 쓰는 기본 상수는 `DEFAULT_EQUAL_SELECTIVITY 0.001`(query_planner.h:116), `DEFAULT_COMP_SELECTIVITY 0.1`(:118)이다(develop 재확인; 그 외 :113-121 에 NULL 0.01/EXISTS 0.1/EQUIJOIN 0.001/BETWEEN 0.01/IN 0.01/RANGE 0.1).
- ✅ **리뷰 체크포인트**: 폴백 경로 질의의 카디널리티가 지나치게 작으면 이 상수를 의심하고, 상수를 바꾸는 변경은 영향 범위가 넓으므로 단독 변경으로 A/B 할 것.

- ✅ **리뷰 체크포인트**: 비용식에 새 상수를 넣을 때 ①sscan/iscan 대칭인가 ②기존 프리미티브(cost_seq_page 등)로 합성 가능한가(신규 파라미터 남발 금지) ③NCARD=0 극한에서 발산하지 않는가.

**비용 값은 `QO_CPU_WEIGHT`(0.0025) 의 정수배라 `.5` 경계가 흔하다 — `(double) 0.0025f`(−2.2e-8)만으로도 덤프의 정수 반올림이 뒤집힌다** (.50, 06b647fc9, 2026-09-21): 같은 볼륨에서 NL 58→57 실측. 그래서 PR#7993(CBRD-27126, 머지 `fa551431b`)은 CPU 단가를 정수 역수 `cost_cpu_tuples_per_page=400`(`1.0/400` 이 0.0025 와 비트 동일)으로 노출했다 — develop `2d925cb86` query_planner.c:97-102(`QO_CPU_WEIGHT` = `1.0 / cost_cpu_tuples_per_page`, 주석 "Costs in this model are integer multiples of this price, so exact ties are common, not rare"). 시스템 파라미터에 double 타입은 없다(`SYSPRM_DATATYPE` = INTEGER/FLOAT/BOOLEAN/KEYWORD/BIGINT/STRING/INTEGER_LIST, system_parameter.h:575-586). 같은 PR 로 단가 5종 — `cost_seq_page`·`cost_random_page`(FLOAT), `cost_cpu_tuples_per_page`·`cost_effective_cache_pages`·`cost_heap_fetch_per_oid`(INT) — 이 `PRM_FOR_CLIENT | PRM_USER_CHANGE | PRM_FOR_QRY_STRING` 으로 들어왔고 기본값은 옛 리터럴과 같다(system_parameter.c:5608-5684). — 정소희(.50) 2026-10-28
- ✅ **리뷰 체크포인트**: 비용 단가를 float 로 읽거나 상수에 `f` 접미사를 붙이는 변경은 덤프의 `.5` 반올림·동률을 뒤집을 수 있다 — 플랜 덤프 diff 로 확인할 것.

**`TEMP_SETUP_COST`(5.0) 는 `fixed_cpu_cost` 에 더하는 정책 오프셋이지 페이지 수가 아니다** (.50, 4f0f90b62, 2026-09-21): `qo_sort_cost` 가 리스트 파일 셋업 몫으로 `fixed_cpu_cost` 에 더한다(4f0f90b62 query_planner.c:3109; 원 주석 "mostly to discourage the optimizer from choosing merge join for joins of little classes"). develop `2d925cb86` 은 :3233 에서 같고, :3236-3237 주석이 "TEMP_SETUP_COST above is a CPU-side policy offset, not a page count, and is not priced" 라고 적는다(`qo_analytic_sort_cost` :5271 도 같은 용법). — 정소희(.50) 2026-10-28
- ✅ **리뷰 체크포인트**: 이 상수에 페이지 단가(`cost_seq_page` 등)를 곱하는 변경은 단위 오류다.

### qo_analyze_term (query_graph.c:2013)

**PREDICATE_TERM 에서 term 별 히스토그램 사용 여부를 진단 플래그로 남긴다** — `env->sel_hist_used`/`env->sel_hist_fallback`(query_graph.h:977-978)을 term 별로 리셋·검사해 `QO_TERM_SEL_FROM_HISTOGRAM`(query_graph.h:756)을 세운다(develop query_graph.c:2815-2822). 어느 term 이 히스토그램을 실제로 탔는지 이 플래그로 구분할 수 있고, plan_generation.c:3213 에서도 소비된다.

**혼합 OR 조건은 join term 으로만 분류되어 단일 릴레이션 sarg 가 0개가 된다** — TPC-H q19 의 큰 OR 는 각 분기 안에 part 컬럼과 lineitem 컬럼이 섞여 있어 CUBRID 의 term 분류가 OR 전체를 join term 으로만 취급한다. 그 결과 part 에 sarg 가 0개가 되어 part 를 줄이는 인덱스 프로브 자체가 성립하지 않는다. 각 분기의 part 조건 OR 를 WHERE 에 수동 중복 추가하면 결과값 동일(30104438.0911)하면서 5.6s → 0.618s 로 개선됨을 실증했고(cubrid-tpch/exp/q19_orext.sql, develop b572177a1), `l_partkey` 선두 인덱스는 CUBRID 에도 이미 있어 추출을 못 해서 못 쓰는 것이 핵심이었다. → 현재 develop 은 rewriter 의 `qo_extract_or_restrictions()` 로 이를 해소(해당 절 참조).
- ✅ **리뷰 체크포인트**: 인덱스가 있는데 안 쓰이는 사례는 term 분류 결과(sarg 개수)를 먼저 의심할 것.

### qo_expr_selectivity (query_planner.c:10126)

**PT_EXPR 가 아닌 노드가 들어올 수 있다** (상수 접힘 결과 등) — 가드 없으면 코어. 처리할 땐 `total_selectivity = 1.0` 같은 값 강제가 아니라 **`continue`(중립)** 가 맞다. AND 결합에서 미지항이 전체를 1.0으로 덮어쓰면 다른 항의 선택도가 소거된다. (2026-08 hotfix 에서 확정, 사용자 검증 완료)

**조인 선택도 호출부의 (1-null_frequency) 이중 곱 규약** — 호출부는 attr=attr 선택도 반환값에 `(1 - nf)` 를 양쪽 컬럼에 대해 두 번 곱한다(develop query_planner.c:10345-10354, `selectivity * (1 - nf1) * (1 - nf2) + nf1 * nf2` 형태 — null-safe `<=>` 는 NULL-NULL 질량 가산). 그래서 `histogram_get_join_selectivity()` 는 자기 계산값을 양쪽 null 팩터로 미리 나눠서 반환하도록 구현돼 있고 주석이 규약을 명시한다(develop histogram_cl.cpp:1643-1656: "the caller (qo_expr_selectivity) multiplies the returned selectivity by (1 - null_frequency) of BOTH name arguments … so divide both back out"). 이 규약을 모르고 순수 selectivity 를 그대로 반환하면 null 이 있는 컬럼에서 선택도가 (1-nf)² 배만큼 과소평가된다.
- ✅ **리뷰 체크포인트**: 조인 선택도 반환값 규약 변경 시 호출부의 (1-nf)×2 보정과 함수 내부 나눗셈이 짝을 이루는지 반드시 같이 확인할 것.

**일반화 — 헬퍼의 non-null 조건부 계약은 조인 경로만이 아니라 모든 술어 노드에서 한 곳이 이행한다** (.52, `c0e06bef9`, 2026-09-22): `qo_expr_selectivity ()` 가 or_next 체인의 **노드마다** `pt_get_end_path_node (arg1|arg2)` 가 PT_NAME 이고 `null_frequency >= 0` 이면 `(1 - null_frequency)` 를 곱한다(c0e06bef9 query_planner.c:10606-10650; CBRD-26202 #7180 도입, CBRD-27039 #7442 · CBRD-27059 #7473 · CBRD-26746 #7508 정련). comp·range·between·like·in·NE·NOT_* 가 전부 개별 소비 함수가 아니라 이 공통 후처리를 지나므로, `qo_comp_selectivity ()` 등만 보면 "곱하는 호출자가 없다"로 오판한다(CBRD-27254 가 그 오판이었고 develop 에서 재현되지 않아 종결 — 결함 아님). 위 "이중 곱 규약" 의 일반화다. develop `2d925cb86` :12000-12039 에서 같은 구조(재확인 2026-10-28). — 정소희(.50) 2026-10-28

**부정 술어의 NULL 차감은 곱 순서로 이미 맞다** (.52, `c0e06bef9`, 2026-09-22): 헬퍼 조건부 sel_c → `qo_not_selectivity ()` 의 `1 - sel_c` → 공통 후처리 `× (1 - nf)` = `(1 - nf) - sel_abs`. 실측(30% NULL, 10,000행): `a NOT BETWEEN 200 AND 400` 참 0.559 / 추정 0.559, `a <> 500` 0.699/0.699, `s NOT LIKE 'v1%'` 0.56/0.56, `a NOT IN (1,2,3)` 0.700/0.697. `IS [NOT] NULL` 은 `not_null_calculated` 로 공통 곱에서 빠진다. 재현물 claude-workspace `projects/CBRD-27254/repro/nullfrac_contract.sql`. — 정소희(.50) 2026-10-28

### qo_equal_selectivity (query_planner.c:10572)

attr=attr 은 `histogram_get_join_selectivity`(:10602) 우선, 실패 시 `qo_index_cardinality`(:10609-10610)의 `1/max(icard)`, 그것도 없으면 `DEFAULT_EQUIJOIN_SELECTIVITY`. attr=const/host_var 는 `histogram_get_equal_selectivity`(:10634/:10683) 우선. 히스토그램/MCV 부재 시 폴백이 기존 `1/max(icard)` 경로로 살아 있는지가 리뷰 관건이다.

### qo_between_selectivity / qo_range_selectivity (query_planner.c:11157 / :11231)

**BETWEEN 은 대부분 PT_RANGE 로 정규화되고, 남는 형태는 이제 히스토그램으로 추정한다** — 과거(CBRD-27094 @ faf5a3b2a 기준) `qo_between_selectivity()` 는 아무 계산 없이 `DEFAULT_BETWEEN_SELECTIVITY`(0.01)를 반환하고 `env->sel_hist_fallback` 만 세우는 사실상 죽은 경로였다(BETWEEN 이 재작성 단계에서 PT_RANGE 로 정규화되어 `qo_range_selectivity` 가 쓰이므로). develop 은 CBRD-27037(#7570, dde911f48) 머지로 달라졌다: 재작성되지 않고 도달하는 형태 — 특히 NOT BETWEEN — 를 `qo_between_range_histogram_selectivity()` 로 히스토그램 추정한다. 주석이 근거를 명시한다: "what reaches here is the form that was not rewritten -- notably NOT BETWEEN, whose complement is not a single range"(develop :11168-11173). col<col(컬럼 대 컬럼 비교)은 기본값을 쓴다.
- ✅ **리뷰 체크포인트**: PT_BETWEEN 경로를 '버그'로 지적하기 전에 PT_RANGE 정규화 이후에도 도달 가능한 형태인지 확인하고, 반대로 정규화를 바꾸는 변경은 이 경로의 도달 집합을 바꿀 수 있으니 주의할 것.

관련 develop 머지 이력: 양측 범위 히스토그램 추정의 1행 플로어(#7726, 7e65be797), 버킷의 `<` vs `<=` 구분(#7741, 44c199cee), 측정된 인덱스 스캔 선택도의 1행 플로어(CBRD-27192, 05522fac8).

### qo_all_some_in_selectivity (query_planner.c:11431)

**IN 리스트 선택도 — 원소별 MCV 프로브가 없다** — IN 리스트 선택도는 원소 개수 × 등호 선택도로만 계산하고(`list_card = pt_length_of_list(...)` develop :11486/:11490, 서브쿼리는 XASL cardinality :11497, 실패 시 legacy 1000), 원소별로 MCV/히스토그램을 프로브하지 않는다. 따라서 선택적인 IN 리스트(희소값)에서 선택도가 크게 과대평가된다. develop 은 하드 상한 0.5 를 그대로 유지한다(`in_selectivity > 0.5 ? 0.5 : in_selectivity`, :11507-11508 "compute selectivity--cap at 0.5"); 상한을 `MIN(in_selectivity, 1.0)` 으로 바꾸고 "the former hard cap of 0.5 had no distributional basis" 주석을 단 것은 CBRD-27094 브랜치다(develop 에 없음 — CBRD-27094/PR#7622 계열).
- ✅ **리뷰 체크포인트**: IN 조건 질의의 플랜이 이상하면 `list_card * equal_selectivity` 근사를 먼저 확인하고, 개선 시 원소별 MCV 프로브 후 중복 보정을 포함해 합산할 것.

### planner_visit_node (query_planner.c:7564)

**조인 카디널리티의 MAX(1.0) 바닥이 분수 카디널리티를 없애 조인 순서를 노이즈로 만든다** — 조인 결과 card 를 1.0 으로 바닥 처리하는 지점은 `planner_visit_node()` 안의 `cardinality = MAX (1.0, cardinality);`(develop :8124, :8134, :8158)와 `total_rows = MAX (1.0, total_rows);`(:8160)이다. 그 결과 25/30 계열 쿼리는 조인 2단계부터 모든 중간 결과가 card=1 이 되고, 이후 조인 순서는 ±1~4 코스트 틱 수준의 노이즈로 결정된다. 같은 함수의 조인 선택도 루프도 곱할 때마다 `selectivity = MAX (1.0 / MAX (cardinality, 1.0), selectivity)` 로 바닥을 누른다 — 술어 여럿의 곱이 바닥에 눌리는 사정은 §3 보강(.52, `07480dfd1`). — 정소희(.50) 2026-10-28
- ✅ **리뷰 체크포인트**: 조인 카디널리티 계산 변경 시 MAX(1.0) 바닥이 어디서 걸리는지, 분수 카디널리티를 보존해야 하는 경로에 적용돼 순서 결정이 코스트 노이즈에 좌우되지 않는지 확인할 것.

**조인 순서 결정이 완전 동률(tie) / RBO dead zone 에 몰려 있어 통계 미세 변화에 취약하다** — eqjoin 선택도가 상류 카디널리티를 1~2 로 압축해버리기 때문에 부착 순서 결정이 비용 동률 구간에서 tie-break 로 결정된다 — 17a 의 t-vs-mc 부착은 1915 vs 1915 완전 동률(추정상 probe multiset 이 동일), 22a 는 1265 vs 1273(Δ8) 이었다. 그래서 아주 작은 통계 변화가 순서를 뒤집는다: Duj1 도입으로 `mk.keyword_id` sel 이 6.197e-6 → 6.698e-6 으로 바뀌자 pattern-C 계열(16b/17a/17e/2d)이 다시 DIFF 로 뒤집히고 20b/20c/9d 가 새로 일치해 order-match v2 가 38→34 로 회귀했다. 동률 판정은 `QO_COST_EQ(x, y)`(develop query_planner.c:115, 상대오차 1e-6; CBRD-27139 #7572 로 반대칭·부동소수 내성 확보), RBO 게이트는 `RBO_CHECK_COST 50`/`RBO_CHECK_RATIO 1.2`/`RBO_CHECK_LIMIT_RATIO 10`(:108-110, 사용처 :4396-4400, :4757)으로 구현돼 있다.
- ✅ **리뷰 체크포인트**: 선택도/NDV 를 건드리는 PR 은 '개선했다'가 아니라 '동률 구간에서 어느 쪽으로 뒤집혔나'로 평가하고, 순서 매치 수치 변동의 원인이 실제 정확도인지 tie-flip 인지 구분해 근거를 요구할 것.

**qo_apply_unique_join_cardinality 회귀 가설은 반증됨 — 오히려 net-helpful** — `qo_apply_unique_join_cardinality` 와 `qo_unique_index_cardinality` 는 실험 브랜치 신규 함수다(commit 5f3b970d8 "parameter tune"; **develop 에도 CBRD-27094 브랜치에도 없음**). `join_card = rhs_side_card × unique_ratio`, `unique_ratio = MIN(1, unique_side_card / unique_index_card)` 가 언더플로우해 1:1 FK→PK 조인을 card 1 로 붕괴시킨다는 가설이 있었으나, 함수를 no-op(`return term_sel`)으로 만드는 결정적 테스트에서 (1) {k,mk,t} 의 card-1 붕괴가 그대로 유지되었고(붕괴의 진원은 base eqjoin 선택도의 곱), (2) order-match 가 37→34 로 떨어지고 26개 질의의 순서가 바뀌었다. 즉 이 캡은 전체적으로 도움이 되는 쪽이며 가설은 폐기·되돌렸다.
- ✅ **리뷰 체크포인트**: 이 두 함수를 회귀 원인으로 지목하는 의견은 이미 반증된 가설임을 상기하고, 카디널리티 붕괴는 캡 함수가 아니라 base eqjoin 선택도 곱부터 계측할 것.

**부분 조인 탐색은 열거 예산으로 제한된다** — develop 은 CBRD-27142(#7721, 876a70814)로 테이블 수 계단(staircase) 대신 `qo_join_unit_from_budget()`(:9694)이 "추정 열거량이 예산에 들어가는 최대 레벨"을 골라 플래닝 비용을 조인 수 전 구간에서 유계로 만든다(주석 :9665-9693에 근거·실측 수치). 플랜 열거 폭을 건드리는 변경은 이 예산 함수와의 상호작용을 확인할 것. `ORDERED` 힌트는 이 예산을 건너뛰고 full DP 로 올리고 `LEADING` 은 올리지 않는다 — 「JOB 실측」 절(.52, `07480dfd1`). — 정소희(.50) 2026-10-28

### qo_plan_compute_cost (query_planner.c:755)

플랜 vtbl 의 cost_fn 디스패치 지점 — 각 플랜 타입의 비용 함수(`qo_*_cost`)가 vtbl 로 연결되며, `TEST_HASH_JOIN_FORCE_ENABLE`(:63) 같은 디버그 스위치도 vtbl 교체(:397-403)로 동작한다(해시 조인 절 참조).

### qo_sscan_cost (query_planner.c:1742)

시동 비용이 없다: `fixed_cpu_cost = 0.0`, `fixed_io_cost = 0.0`, `variable_cpu_cost = NCARD * QO_CPU_WEIGHT`, `variable_io_cost = TCARD`(develop :1747-1758). NCARD==0(통계 미수집)이면 `1.0 * QO_CPU_WEIGHT` = 0.0025 를 주는 분기가 있다(:1749-1752). iscan 에만 상수항을 더하는 변경이 소형 테이블 동률을 뒤집는 이유가 이 '대응항 없음'이다(descent_cpu 계열 참조).

### qo_iscan_cost (query_planner.c:2249)

**develop 현행 heap-fetch 모델: 완전 클러스터 object_IO + MIN(heap_rows, opages) 캡의 per-row 서차지** — 커버링 스캔이면 `object_IO = 1.0`, heap_access = 0. 아니면 `object_IO = opages * heap_sel` 에 CBRD-27113(#7527, a81193c9b)이 도입한 per-extra-row 서차지 `heap_fanout = (heap_rows > 1.0) ? MAX(0, MIN(heap_rows, opages) - 1.0) * FETCH_HEAP_COST : 0.0`(:2459)을 더한다 — 단일행(unique/pk) 프로브는 0 을 더해 기존 비용을 정확히 유지(blast-radius safe, 상수 주석 :85-88). 캡의 물리적 근거는 주석 그대로다: "fetching more rows than there are heap pages cannot touch more distinct pages"(:2455-2458). leaf IO 는 fixed/variable 로 분리된다: 하강이 닿는 첫 leaf 는 fixed(`fixed_io_cost = index_IO + first_leaf`, :2475), `leaves - first_leaf`·`iss_leaves`·heap_fanout 은 variable 측 `object_IO = MAX (1.0, object_IO) + ...`(:2469). PR#7622 는 이 MIN 캡 모델을 Mackert-Lohman 으로 교체하며 "MIN 이 k≈T 근처에서 최대 58% 과대추정"을 근거로 들었다 — 판단 쟁점은 "단일 스캔에 (재읽기를 포함하는) T>b 분기를 적용하는 것이 타당한가"로 귀결된다(develop 미머지).
- ✅ **리뷰 체크포인트**: heap-fetch 추정식 교체 PR 은 새 모델이 distinct-page 상한 불변식을 깨는지 먼저 확인하고, 과대추정 개선 주장과 상한 붕괴 위험을 함께 저울질할 것.

**옛 완전 클러스터 가정의 NL 프로브 고정 비용 문제 (역사)** — 인덱스 스캔 비용에서 object_IO 를 `opages × sel`(대상 행이 페이지에 완전 클러스터돼 있다는 가정)로만 계산하고 `ISCAN_IO_HIT_RATIO 0.5` 할인까지 곱해지던 시절, NL 내부 프로브 비용이 inner 관계 크기·fanout 과 거의 무관한 ~3~4 로 고정됐다 — 36M행 cast_info 프로브와 7행 kind_type 프로브가 같은 값으로 평가됐다. 이것이 JOB divergence 2순위 원인으로 10c(57.7s) 8c(37.3s) 18a(58.9s) 19a-c 의 주범이었고, 브랜치 커밋 c31d3b2f6 에서 object_IO 를 무상관 가정 `MIN(heap_rows, opages)` 로 바꿔 총 683→455.2초(-33%), 8c 96.9→8.7, 8d 103→3.3, 10c 65→5.3 으로 개선됐다(PK 프로브는 카디널리티 MAX(1.0) 바닥 때문에 불변). 회귀도 동반됐다: 19c/d +4~5s, 9c/5c/13b/13c/7a +2~3s, 1a 0.03→0.59(소형 쿼리의 해시 오버헤드). develop 은 위의 FETCH_HEAP_COST 서차지 형태로 흡수했다.
- ✅ **리뷰 체크포인트**: 인덱스 스캔/NL 프로브 비용식 변경은 (1) 프로브 비용이 inner 크기·fanout 에 단조 증가하는지, (2) 클러스터링 가정이 무상관에서 임의로 벗어나지 않았는지, (3) PK/유니크 단건 프로브가 MAX(1.0) 바닥으로 여전히 불변인지, (4) 1a 류 소형 쿼리 회귀는 없는지 확인할 것.

**iscan 힙 fetch 비용의 MAX(1.0) 플로어가 페이지 비용 계수를 삼킨다** — 랜덤 페이지 비용 계수 4.0 실험(실험 브랜치 상수) 결과 두 배치 모두 실패했다: (i) MAX(1.0) 플로어 **이전**에 곱하면 완전히 무력하다 — 선택적 probe 는 `opages × sel ≪ 1` 이라 플로어가 계수를 통째로 삼킨다(19d 만 순서가 흔들림). (ii) 플로어 **이후**에 적용해 probe 당 최소 4.0 을 강제하면 order-match v2 가 40→35 로 회귀했다(3a/3c/5c/7a/9d 상실). 둘 다 되돌렸고, 결론은 probe 비용 구조에 per-tuple 비용 세분화가 선행돼야 한다는 것이다(그 실험 상수는 현재 소스에 없다 — develop 의 랜덤 페이지 단가는 `fa551431b` 이후 `cost_random_page` 파라미터를 읽는 `QO_COST_RANDOM_PAGE`).
- ✅ **리뷰 체크포인트**: 스캔 비용 상수를 추가·조정하는 변경은 그 항이 MAX/floor 뒤에서 실제로 살아남는지 먼저 확인하고(살아남지 못하면 no-op), 살아남는 위치라면 probe 전반의 균일 패널티로 스캔 방식 선택이 뒤집히지 않는지 확인할 것.

**LIKE prefix 파생 범위와의 중복 상쇄** — rewriter 가 prefix LIKE 에서 파생한 BETWEEN 범위(`PT_EXPR_INFO_LIKE_DERIVED_RANGE`, CBRD-27036 계열 bd835423b/a67a38674)는 유지된 LIKE 의 부분집합이므로, `qo_iscan_cost()` 가 같은 곱에 LIKE 가 참여하는 경우에만 범위를 상쇄한다(rewriter/query_rewrite_term.c:2369-2374 주석). 파생 술어 쌍의 플래그를 모르면 선택도 이중계상으로 오독하기 쉽다.

#### descent_cpu 회귀 계열 (develop 에 없음 — CBRD-27094/PR#7622 계열)

아래 항목들의 코드·행번호는 CBRD-27094 @ faf5a3b2a 기준이다. develop 에는 descent_cpu 도 `BTREE_DESCENT_PAGE_OVERHEAD` 도 `iscan_descent_cpu` 도 없다.

**descent_cpu 가 sscan 에 대응항 없이 과금되던 비대칭 (PR#7622 CI 27건 회귀의 근본원인, 브랜치에서 수정됨)** — `qo_iscan_cost` 는 모든 인덱스 스캔에 루트→리프 하강 비용을 물린다: `descent_cpu = (ceil(log2(NCARD + 1.0)) + (height + 1.0) * BTREE_DESCENT_PAGE_OVERHEAD) * QO_CPU_WEIGHT`(브랜치 query_planner.c:2517-2519, `BTREE_DESCENT_PAGE_OVERHEAD 50` :96, `QO_CPU_WEIGHT 0.0025` :82). 문제가 된 버전은 이 값을 `planp->variable_cpu_cost` 에 직접 합산했는데, `qo_sscan_cost` 에는 대응하는 시동 비용이 전혀 없어 iscan 만 일방적으로 과세되고 동률 플랜이 계통적으로 sscan/풀스캔으로 뒤집혔다. 브랜치 head(faf5a3b2a)는 descent 를 `planp->iscan_descent_cpu` 로 분리 발행해(:2520) `qo_nljoin_cost` 의 inner 경로에서만 소비하고(:3709 `inner_cpu_cost = guessed_result_cardinality * (inner->variable_cpu_cost + inner->iscan_descent_cpu)`), 그 근거가 :2503-2517 주석에 남아 있다.
- ✅ **리뷰 체크포인트**: iscan 비용 항을 추가/수정할 때 `qo_sscan_cost` 에 대칭 항이 있는지 반드시 함께 확인하고, descent 계열 값을 `variable_cpu_cost` 에 직접 더하는 패치는 거부할 것.

**iscan 에만 붙는 고정 CPU 항은 소형 테이블 동률을 뒤집는다** — btree descent 보정처럼 sscan 에 대응항 없는 상수를 iscan variable cost 에 더하면 NCARD=0~수십에서 sscan 으로 플립(실측 0.2575 vs 0.01). 2.5M행에선 0.009%라 대형 벤치(JOB)만 보면 안 보인다. **비용 모델 변경은 소형·대형 양쪽에서 검증할 것.** (PR #7622 27건 회귀의 단일 근본 원인)

**(height+1)*50*W = 0.25 는 테이블 크기와 무관한 평탄 페널티 — 토이 테이블·NCARD=0 에서 치명적** — descent_cpu 의 `(height + 1) * BTREE_DESCENT_PAGE_OVERHEAD * QO_CPU_WEIGHT` 성분은 카디널리티에 전혀 반응하지 않는 고정값 0.25 이며, 브랜치 주석이 그 수치를 그대로 기록한다: "0.2575 for a 4-row table against 0.01 for the sequential scan, and 0.25 against 0.0 when statistics are missing (NCARD = 0)"(브랜치 :2513-2515). 반대로 title 2.5M 같은 대형 테이블에서는 0.5550 대 6320.78 로 0.009% 에 불과해 존재감이 없다 — 즉 이 항은 오직 소형 객체에서만 지배적이 되어 '데이터와 무관하게' 동률을 깬다. (`qo_sscan_cost` 의 NCARD==0 분기 0.0025 덕에 비율이 무한대는 아니지만 여전히 100배다.)
- ✅ **리뷰 체크포인트**: 비용 상수를 카디널리티/페이지수와 무관한 상수항으로 넣지 말고, 넣어야 한다면 TCARD 비례로 스케일하고 NCARD=0(통계 미수집) 경로에서 어떤 값이 되는지 반드시 계산해 볼 것.

**descent_cpu 의 원래 의도는 inner(반복 프로브) 보정이며 구동측은 variable_cpu 를 1회만 문다** — 설계 의도는 주석에 있다 — "after the repeated-probe correction in qo_nljoin_cost () saturates the heap IO, a multi-million-probe nested loop still does not look free"(브랜치 :2505-2507). `variable_cpu_cost` 는 nljoin 에서 프로브 수로 곱해지므로 inner 경로에 한정해도 의도는 그대로 달성되는 반면, 구동측(조인의 outer 또는 단독 스캔)은 `variable_cpu_cost` 를 정확히 한 번만 지불하므로 여기에 descent 를 물리는 것은 의도와 무관한 순수 부작용이었다. 그래서 1순위 수정안이 '(a) inner 경로에만 물리기' 였고 브랜치는 이를 `iscan_descent_cpu` 분리 발행(:2520)으로 구현했다.
- ✅ **리뷰 체크포인트**: 'per-probe 성격의 비용'을 추가할 때 그 항이 구동측 스캔에서도 한 번 부과되는지 확인하고, per-probe 항은 inner 전용 필드로 분리 발행해 `qo_nljoin_cost` 에서만 소비하는 패턴을 따를 것.

**JOB 벤치마크는 이 결함을 잡아내지 못한다 — 독립된 네 번째 축** — descent 비대칭은 대형 테이블에서 총비용의 0.01% 미만이라 JOB(IMDB) 질의로는 전혀 드러나지 않았다. 기존 JOB 분석의 세 축(ML 무상한 분기 / 초소형 inner 하한 부재 / 저프로브 할인 소실)과 완전히 독립된 네 번째 결함 축이며, 오직 회귀 TC 의 토이 테이블(3~13행, 카탈로그 1~2페이지)에서만 노출된다.
- ✅ **리뷰 체크포인트**: 비용모델 변경의 검증을 JOB 개선치만으로 끝내지 말고, 소형/통계없는 테이블 경로를 별도 검증할 것 — 회귀 TC 플랜 diff 가 그 유일한 센서다.

**회귀의 일관된 패턴 — 커버링 인덱스가 힙 풀스캔으로 강등되고 레인지 프루닝이 사라진다** — 27건 CI diff 에서 반복 관찰된 패턴: (1) 구동측 커버링 iscan → 힙 sscan 강등(`y.a_y_index` 상실 등), (2) 선택적 인덱스 포기 — UNIQUE 전체키+커버링 → 선행 1컬럼+비커버링, (3) 키범위를 버리고 전구간 스캔+필터, (4) 선택적 sarg 가 구동측 키레인지에서 프로브별 key filter 로 강등. 대표 사례로 `sql/_16_index_enhancement/_05_index_covering_plan_dump/cases/_03_index_covering.sql` 은 구동측 커버링 iscan 이 힙 sscan 이 되면서 레인지 프루닝을 잃어 `a>1` 3행 구동이 4행 전건 구동이 되고 프로브가 3→4 로 늘었다(자매 케이스 `sql/_18_index_enhancement_qa/.../_t110_25_join.sql` 은 클래스명 미마스킹이라 교차확인에 유용).
- ✅ **리뷰 체크포인트**: 플랜 diff 에서 'covers → 힙 스캔', '키레인지 → 전구간+filtr', '프로브 수 증가'가 함께 나타나면 개별 답안 drift 가 아니라 계통적 비용모델 결함을 의심할 것.

**NCARD=0(통계 미수집) 테이블에서 커버링 인덱스가 통째로 버려지는 교과서 사례** — `shell/_28_features_844/.../_03_mixed_test/_06_update_delete/cases/_06_update_delete.sh` 는 통계가 없는 테이블에서 `y.a_y_index` 커버링 스캔이 y 풀스캔으로 강등되고, 선택적 sarg 가 구동측 키레인지에서 프로브별 key filter 로 밀려났다. NCARD=0 이면 `log2(0+1)=0` 이라 descent_cpu 의 로그항은 사라지지만 평탄항 0.25 는 그대로 남는 반면 sscan 쪽은 0.0025 에 그치므로 iscan 이 무조건 진다 — 통계 미수집 경로는 비용 비대칭이 최악으로 증폭되는 지점이다.
- ✅ **리뷰 체크포인트**: 비용 공식 변경 시 NCARD=0 / TCARD 최소값 경로를 별도로 계산해, 통계 없는 테이블에서 인덱스가 구조적으로 선택 불가가 되는지 확인할 것.

**고정 descent charge 가 카탈로그 뷰의 정확한 비용 동점(6 vs 6)을 깨서 시스템 카탈로그 질의를 퇴행시킨다** — `shell/_03_itrack/itrack_1002486/cases/itrack_1002486.sh` 는 develop 에서 cost 6 vs 6 의 정확한 동점이던 플랜이 고정 descent charge 로 깨진 사례다. 그 결과 `db_index` 뷰가 선택적 시크를 포기하고 `_db_index` 전순차 스캔 + 행마다 `_db_class` OID fetch 후 사후필터로 바뀌었다. 1~2페이지짜리 카탈로그 테이블이 `(height+1)*50 = 100` 연산단위를 무는 것은 명백한 과금 과다이며, 평탄항을 TCARD 비례로 바꾸자는 수정후보 (c)의 직접 근거다.
- ✅ **리뷰 체크포인트**: 비용 상수 변경 시 페이지 수가 1~2 에 불과해 상수항에 극도로 민감한 시스템 카탈로그(`_db_index`/`_db_class`) 뷰 질의 플랜을 반드시 확인할 것.

**그 밖의 대표 회귀 TC 4건 — 프로브당 행수·UNIQUE 매칭·파티션 프루닝·키범위** — (1) `sql/_35_fig_cake/cbrd_25382/cases/cbrd_25382_1.sql`: NL inner 인덱스가 `i_c`(cd 유니크, 1행/프로브)에서 `i_a`(ca,cb,cc, 2행/프로브)로 바뀌어 btree time 149~156→260~272, fetch 48000→80000(비용 언마스킹 1046 vs 1326). (2) `sql/_33_elderberry/cbrd_24042/cbrd_24182/cases/r_outer_join.sql`: outer join 최내측 inner 가 `idx(c_a,c_b)` UNIQUE 전체키+covers 에서 `idx_a(c_a,c_c)` 선행 1컬럼+filtr 로 강등 — 프로브당 최대 1행 보장을 잃는 것은 어떤 비용 이득으로도 정당화되기 어렵다. (3) `sql/_13_issues/_12_2h/cases/bug_bts_9935_03.sql`: 14개 hunk 전부가 covers → t2 힙 풀스캔이 되면서 IN 상수의 컴파일타임 LIST 파티션 프루닝까지 소멸(형제 bug_bts_4563_3, bug_bts_6649, bug_bts_6706, cbrd_26260 과 동일 근본원인). (4) `shell/_39_fig_cake/.../cbrd_25080/cases/cbrd_25080.sh` no_limit: `idx3(col_c)` 키범위를 버리고 `idx1` 전구간+필터로 — 추정 1만행 기준 28% 퇴행이지만 실제 결과가 0행이면 100배 이상 퇴행한다(같은 파일 서브테스트 4·5 는 비용 자릿수만 변한 순수 재블레스 대상). 힌트 경로도 안전하지 않다: `shell/_06_issues/_14_2h/bug_bts_6680/cases/bug_bts_6680.sh` 의 `NO_DESC_IDX` 케이스는 outer 가 `iscan x(5행)`에서 `sscan y(9행 전건)`으로 뒤집혀 프로브가 5→9 로 늘고 그중 6건이 조인 후 filtr 로 폐기된다.
- ✅ **리뷰 체크포인트**: 'UNIQUE 전체키 매칭 상실', '프로브당 행수 증가', '파티션 프루닝 정보 소멸', '키범위 → inf~inf' 는 추정 퇴행률이 작아 보여도 무조건 회귀로 판정하고 실측(btree time, fetch)으로 확인할 것.

### qo_mackert_lohman_pages (query_planner.c:4292 — `bacd5d0d2` 로 develop 반영; 아래 첫 문단 행 번호는 브랜치 기준)

**T>b 분기에는 캡이 없어 N 에 선형·무상한으로 커진다** — `qo_mackert_lohman_pages(T, N)`(브랜치 query_planner.c:3608-3636)에는 구조적 비대칭이 있다: `T <= b` 분기에는 `if (pages_fetched > T) pages_fetched = T;` 캡이 있으나 `T > b` 분기(`b + (N-lim)*(T-b)/T`)에는 캡이 없다. 이 함수는 `qo_iscan_cost` 의 단일 스캔 object_IO(브랜치 :2480)와 `qo_nljoin_cost` 의 반복 프로브 포화(브랜치 :3741-3742) 양쪽에서 쓰인다. 실측: cast_info(힙 129,909 페이지)에서 N=3,018,730 일 때 2,262,020 페이지 = 힙 전체의 17.41배가 나오며, 동일 입력에서 develop 의 `MIN(heap_rows, opages)` 캡은 129,909 로 상한을 지킨다. 버퍼 크기 `b` 는 하드코딩된 `QO_EFFECTIVE_CACHE_PAGES`(비용 상수 절 참조). (2026-10-28: 이 함수는 `bacd5d0d2` 로 develop 에 들어와 `qo_iscan_cost` 단일 스캔 object_IO(:2608)와 NL 포화(:4476-4479)에 쓰이고, T>b 분기(:4309-4320)에는 여전히 캡이 없다 — 비교 대상이던 `MIN (heap_rows, opages)` 캡은 develop 에서 사라졌다. `b` 는 `fa551431b` 이후 `cost_effective_cache_pages`. develop `2d925cb86` 재확인 — 정소희(.50) 2026-10-28)
- ✅ **리뷰 체크포인트**: 단일 스캔에서 힙 페이지 수를 초과하는 fetch 추정이 나오면 T>b 분기의 캡 부재가 의도된 것인지(재읽기 포함 의미인지) 검토를 요구할 것.

### qo_nljoin_cost (query_planner.c:3548)

(95b79e7ed 기준) inner 반복 프로브의 IO 는 `ISCAN_IO_HIT_RATIO 0.5` 할인(:3619) 또는 `SSCAN_DEFAULT_CARD` 가산(:3625)으로 계산되고, 서브쿼리 CPU 보정이 :3675-3676 에 있었다. **CBRD-27094(`bacd5d0d2`) 이후 iscan inner 는 평탄 할인 대신 Mackert-Lohman 포화로 계산된다** — develop `2d925cb86` 은 힙 몫(`iscan_heap_io`)과 리프 몫을 각자 객체 크기(힙 TCARD / 인덱스 페이지)에 포화시키고(:4461-4481), sscan inner 는 `(inner_scan_card + SSCAN_DEFAULT_CARD) * variable_io_cost`(:4487) 그대로이며, 서브쿼리 보정 블록은 `#if 0`(:4499-4541)이라 `ISCAN_IO_HIT_RATIO` 는 그 안에만 남았다(§3). — 정소희(.50) 2026-10-28

**IO 단가는 `MIN` 양변에 같이 곱해야 포화 지점이 불변이다 — `MIN (card × heap_io, heap_fetched)` 는 페이지 수끼리의 비교다** (.50, 87b25579e, 2026-09-21 → PR#7993 머지 `fa551431b`): IO 단가를 곱하려면 `iscan_heap_io`·`variable_io_cost` 쪽과 `heap_fetched`·`leaf_fetched` 쪽 양변에 같은 인수를 곱해야 한다 — 한쪽만 곱하면 단가가 비용을 스케일하는 대신 포화 지점을 옮긴다. 실측: 비커버링 NL 1만 프로브에서 random 단가 ×2 → +359(포화 357 페이지 ×2), cache=0 → 18,326→1,017,969. develop `2d925cb86` 은 포화 상한에도 `QO_COST_RANDOM_PAGE` 를 곱하고(:4476-4479) 주석 :4472-4475 가 이 규칙을 적는다. — 정소희(.50) 2026-10-28

**커버링 인덱스 프로브(`count(*)`)는 힙 페치 0·프로브당 리프 IO ~0.0002 페이지라 NL 포화 상한이 걸리지 않는다** (.50, 87b25579e, 2026-09-21): `cost_effective_cache_pages` 효과를 보려면 비커버링(`count(b.pad)`) 프로브가 필요하다. — 정소희(.50) 2026-10-28

**SEMI/ANTI idx-join 의 inner 는 첫 매치에서 멈추는 것으로 값이 매겨진다** (.51, 2026-09-22 "비용 모델 반영 여부 미확인" → 수정됨: `2ef77b8f0` CBRD-27397, 2026-10-23): PR#7991(`64516d22e`, CBRD-27465)이 NL semi/anti 의 inner 인덱스 스캔에 첫 키 정지(key limit 1)를 넣을 때는 비용 모델을 건드리지 않았다(그 커밋은 plan_generation.c·실행기만). 그 뒤 `2ef77b8f0` 가 `qo_nljoin_cost` 에 분기를 넣었다 — `JOIN_INNER`·`QO_JOINMETHOD_IDX_JOIN` 이고 `qo_plan_semi_anti_join_type (inner) != PT_JOIN_NONE`·`iscan_range_rows > 0` 이면 `inner_scan_card = guessed_result_cardinality × hit_prob / iscan_range_rows`, `inner_fetch_rows = guessed_result_cardinality × hit_prob`(hit_prob = 등가 조인 term 의 head_factor 곱; develop `2d925cb86` query_planner.c:4408-4432, `iscan_range_rows` 는 `qo_iscan_cost` 가 프로브당 키 범위 행수로 기록 :2583). 그래서 key limit 이 붙는 플랜이 비용에서도 싸게 보인다. sscan inner 의 nl-join 과 해시 SEMI/ANTI(#8001 `8ea02c8e8`)는 이 보정 밖이다(코드 판독, 실측 안 함). — 정소희(.50) 2026-10-28

**NL 프로브 비용 과소평가 — 300버킷 통계에서 q19 플랜이 정반대로 뒤집힌다** — 4버킷 통계에서는 lineitem 구동(sscan → part PK 프로브, 추정 2.88M, 실측 ~5s)을 고르지만, 300버킷 히스토그램에서는 part 구동(part 2M 무필터 sscan → fk_lineitem_partsupp 인덱스 프로브 2M회, 추정 1.91M 으로 더 싸 보임, 실측 25~48s)으로 뒤집힌다. 추정 순위가 실측과 정반대이며(플랜 덤프 cubrid-tpch/plans/q19_b572_16G_300bk.raw vs q19_b572_16G_defbk.raw), 이는 NL 프로브 비용 과소 계열 문제다. 즉 통계 정밀도 향상이 잘못된 비용 모델 아래에서는 오히려 나쁜 플랜을 고르게 만든다.
- ✅ **리뷰 체크포인트**: 통계 정밀도(버킷 수) 변경 후 플랜 플립이 생기면 통계가 아니라 비용 모델을 먼저 의심하고, 대량 프로브(수백만 회) 플랜의 추정 비용이 sscan-구동 플랜보다 싸게 나오지 않는지 확인할 것.

**PR#7453 계열 프로브 IO 상한이 q19 플랜 플립을 막는다 (동시에 여러 질의를 움직인다)** — PR#7453 계열의 비용 모델 수정(프로브 object_IO 를 `MIN(heap_rows, opages)` 로 제한)을 담은 overhaul 브랜치는 동일 SSOT 조건(8G·300버킷)에서 q19 가 뒤집히지 않고 lineitem 구동을 유지해 5.34s 로 끝난다(develop 46.96s 대비 8.8배) — 잘못된 프로브 IO 비용이 만든 '가짜 박빙'을 벌려놓은 실증이다. 다만 전체는 250.3s(develop 281.2s 대비 -11%)로, q19 -41.6s·q5 -7.4s·q22 개선인 반면 q3 +57%·q7 +21%·q13 +21%·q18 +17% 회귀가 남는다(results/ssot_34748fed7_0805_161834.tsv vs results/ssot_b572177a1_0805_152020.tsv).
- ✅ **리뷰 체크포인트**: 프로브 IO 비용 상한 관련 코드를 수정할 때는 q19 뿐 아니라 q3/q7/q13/q18 회귀를 함께 확인할 것 — 이 상한은 여러 질의의 플랜 선택을 동시에 움직인다.

**M-L 포화가 물리 I/O 만 줄이고 프로브당 버퍼접근을 지우는 문제 (hash-join → idx-join 역전) (develop 에 없음 — CBRD-27094/PR#7622 계열)** — 반복 프로브 보정(M-L 포화)은 프로브가 많아지면 힙 I/O 를 포화시켜 상수에 수렴시키는데, 실제로 남는 프로브당 버퍼 접근(실측 약 24 pgbuf_fix/프로브)이 비용에 반영되지 않았다. 그 결과 hash-join(sscan/sscan)이 idx-join 으로 뒤집혔고 실측이 `time 933, fetch 240904, ioread 130` — 서버시간 8.8배, 버퍼 페치 65배 퇴행했다(sql/_35_fig_cake/cbrd_24044/cbrd_25060/cases/cbrd_25060_2.sql 5번 블록 두 번째 쿼리, 힌트 없는 ordered 4컬럼 등가조인). 브랜치 head 는 힙/리프를 각자 객체 크기로 따로 포화시키고(브랜치 :3739-3745) 잔여 프로브당 비용을 `iscan_descent_cpu`(:3709)로 남기는 형태이며, 이 결함은 descent 비대칭과 같은 함수 계열이라 서로 간섭할 수 있어 반드시 분리해 측정해야 한다.
- ✅ **리뷰 체크포인트**: NL 반복 프로브 보정(포화)을 손댈 때 포화 후에도 프로브당 최소 버퍼접근 비용이 남는지, hash-join 대비 역전이 생기지 않는지 확인하고, descent 관련 수정과 같은 커밋에 섞지 말 것.

**해시 조인 활성화가 NL 프로브 저가 버그를 증폭시킨다 (8d 재앙 사례)** — 8d 가 5.4→103.1초로 터진 원인은, 해시 조인이 1행짜리 rt 를 늦게 붙일 자유를 주자 옵티마이저가 `cn⋈mc⋈t⋈ci`(추정 30.2M행) 프리픽스를 만들고 rt 를 해시로 필터하는 플랜을 골랐기 때문이다. 카디널리티 추정치는 30M 으로 정확했는데 비용이 싸게 나온 것이 문제였다 — NL 프로브 저가 평가(ci 프로브 cost 4) 버그를 해시 조인이 더 공격적으로 악용하는 복합 문제다. 결론: 해시 조인 도입은 2순위 갭을 해소하지만 `qo_nljoin_cost` 가 inner 크기/fanout 을 반영하도록 고치지 않으면 8c/8d 형 악용이 계속 나온다.
- ✅ **리뷰 체크포인트**: 조인 방식 선택 변경이 '추정 카디널리티는 큰데 비용은 작게 나오는' 프리픽스를 새로 만들지 않는지, 특히 1행짜리 필터 테이블을 뒤로 미루는 플랜이 생기지 않는지 확인하고, 카디널리티가 맞는데 느려졌다면 비용식을 의심할 것.

### qo_mjoin_cost (query_planner.c:3705)

**머지 조인 스캔 범위 추정 미구현** — 머지 조인에서 양쪽 입력을 어디까지 스캔하게 되는지를 히스토그램으로 추정하는 로직이 없다. 즉 머지 조인은 항상 양쪽 전체 스캔 비용으로 계산되어, 한쪽이 조기 종료되는 경우를 과대 비용으로 본다.
- ✅ **리뷰 체크포인트**: 머지 조인 비용 변경은 스캔 범위 추정 부재를 전제하는지 확인하고, 새로 도입한다면 히스토그램 경계와 조인 키 범위의 교집합을 기준으로 할 것.

### qo_hjoin_cost / qo_examine_hash_join (query_planner.c:3784 / :6818)

**해시 조인 게이트는 뒤집혔다 — 옛 default-disable 이 아니라 현재는 force-enable 디버그 스위치** — 과거 분석 시점에는 `TEST_HASH_JOIN_ENABLE 0` 으로 해시 조인 선택이 컴파일 아웃되어 있었고, `qo_examine_hash_join` 이 기본 차단하여 옵티마이저가 좌편향(left-deep) 인덱스-NL 체인만 만들 수 있었다 — JOB 113 질의에서 CUBRID 는 864 조인 전부 idx-join(hash 0/merge 0)이었다. PR CUBRID#6782(CBRD-26475, 머지 커밋 1608d670e)가 default-disable 게이트를 제거해 `qo_hjoin_cost` 가 활성화됐고, 현재 매크로는 의미가 반대다 — `TEST_HASH_JOIN_FORCE_ENABLE 0`(develop :63)이 1 이면 vtbl 이 `qo_zero_cost` 로 바뀌어 해시 조인을 **강제**한다(develop :397-403). 활성화 당시 전체 측정은 615.5→749.2초(+21.7%), 순서 매칭 31→33 으로 결과가 극명히 갈렸다(18a 61.5→22.5s 개선 vs 8c 44→96.9s, 8d 5.4→103.1s).
- ✅ **리뷰 체크포인트**: 해시 조인 관련 변경은 매크로가 force-enable 의미임을 전제하는지, NL 선호 오프셋 `HJ_MEM_ALLOC_CONSTANT 1500`(develop :93, 적용 :3834/:3842)이 의도대로인지, 채택 여부가 갈리는 쿼리군에서 개선/회귀를 함께 측정했는지 확인할 것.

**CBRD-26475 가 의도적으로 고정한 hash-join 선택을 되돌리는 회귀는 재블레스 대상이 아니다** — `sql/_35_fig_cake/cbrd_24044/cbrd_25060/cases/cbrd_25060_2.sql` 의 해당 쿼리는 커밋 `bdd75ed8b [CBRD-26475] The optimizer selects a hash join execution plan (#2987)`(2026-07-16)이 hash-join 선택을 검증하려고 새로 추가한 것이다. 비용모델 변경으로 이 쿼리가 idx-join 으로 넘어가면 바로 위에 있는 `no_use_hash` 변형의 기대 플랜과 문자 단위로 동일해져 테스트가 자기 목적을 완전히 상실한다. 따라서 이 케이스는 재블레스가 아니라 코드로 풀어야 한다.
- ✅ **리뷰 체크포인트**: 플랜 답안 재블레스 전에 해당 TC 를 추가한 커밋의 의도를 확인하고, 같은 파일 내 힌트 변형과 기대 플랜이 동일해지는 재블레스는 거부할 것.

### qo_get_class_info / qo_get_attr_info / qo_copy_histogram_value (query_graph.c)

**파스 트리가 smclass->histogram 을 '빌린 포인터'로 들고 있던 dangling 결함 — 해소됨(develop 937d09feb, CBRD-27279 #7761)** — 과거 develop 은 `QO_SEG_PT_NODE (seg)->info.name.histogram = hist_stats->histogram[h];` 로 `smclass->histogram`(class_object.h:787, 온디맨드 로드되는 클래스 통계)을 복사 없이 대입해, PT_NODE 가 자기 소유가 아닌 스키마 캐시 메모리를 컴파일이 끝날 때까지 들고 있었다. 컴파일 도중 smclass 통계가 리로드/디캐시되면(HA, 캐시 압박, 동일 클래스가 여러 QO 노드로 등장) 포인터가 dangling 이 되어 segv 가 난다 — PR#7726(CBRD-27129)의 CI test_sql 실패(cbrd_25089 LEADING 힌트 케이스 CAS 코어덤프)의 근본 원인이며 해당 PR 과 무관한 develop 결함이었다. CBRD-27094 브랜치에서 만든 수정이 develop 에 머지되어(937d09feb), 현재 develop 은 `qo_copy_histogram_value()`(query_graph.c:5253)로 parser 아레나 복사본을 만들어 대입하고(:5448-5452), 주석이 근거를 남긴다: "own a copy: the cache-owned blob can be freed before the term analysis consumes this annotation".
- ✅ **리뷰 체크포인트**: PT_NODE 나 QO 구조체에 smclass/스키마 캐시에서 얻은 포인터를 그대로 대입하는 코드가 추가되면 거부하고, 컴파일 스코프 복사(`qo_copy_histogram_value` 패턴) 또는 핀 고정을 요구할 것.

**QO_GET_CLASS_STATS 는 self_allocated 복사 경로가 있으나 QO_GET_HIST_STATS 는 무보호 (비대칭, 매크로는 develop 에 잔존)** — 두 매크로는 `query_graph.h:201-204` 에 나란히 정의돼 있지만 소유권 정책이 다르다. CLASS_STATS 는 `self_allocated` 플래그(:76)로 복사본을 만들고 해제까지 관리하는 경로가 있어 컴파일 중 스키마 캐시 변경으로부터 보호되는 반면, `QO_GET_HIST_STATS(entryp)` 는 여전히 `(entryp)->smclass->histogram` 원본 포인터를 그대로 돌려준다(develop 재확인). 위 dangling 결함의 구조적 원인이었고, 현재는 주석 사이트(qo_get_attr_info)의 복사 대입으로 보완된 상태다 — 매크로 사용처를 새로 늘리는 코드는 같은 결함을 재생산할 수 있다.
- ✅ **리뷰 체크포인트**: 통계 접근 매크로/헬퍼를 추가·수정할 때 CLASS_STATS 경로와 HIST_STATS 경로의 소유권 정책이 대칭인지 확인할 것 — 한쪽만 복사하는 신규 코드는 같은 결함을 재생산한다.

**그 크래시의 진단 3종 세트: prepare 중 역참조 / reset 가드 / 캐시 상태 의존** — 콜스택은 `hist::HistogramReader::reset(string_view)` ← `histogram_init_reader_from_lhs` ← `histogram_get_join_selectivity` ← `qo_expr_selectivity` ← `do_prepare_select` 로, 히스토그램 포인터는 실행이 아니라 **질의 컴파일(prepare) 도중** 역참조된다 — 통계 캐시가 컴파일 구간 전체에 살아 있어야 한다는 암묵적 수명 요구다. `HistogramReader::reset()` 은 크기·`HST2` 매직·버전·`total_size_ != blob_.size()` 가드를 모두 갖고 있으므로 손상된 '내용'은 정상 거부되며, reset() 안에서 실제 segv 가 나려면 전달된 string_view(버퍼 포인터/길이) 자체가 이미 무효여야 한다 — 이것이 '내용 손상'이 아니라 '포인터 dangling' 으로 원인을 좁힌 판정 근거다. 발현은 통계 캐시 상태에 의존해 간헐적이라 선행 2,485 케이스가 만든 캐시 상태가 있어야 재현되고, 단독 CTP·동일 하네스·csql release/debug·JDBC setQueryInfo·CTP mini 는 모두 통과했다.
- ✅ **리뷰 체크포인트**: 히스토그램 파싱 크래시는 reset() 가드 통과 여부로 '포맷 문제'와 '수명 문제'를 구분하고, 단위 재현 실패를 '문제 없음'의 근거로 삼지 말 것.

**`null_frequency` 는 히스토그램과 같은 자리에서 함께 PT_NAME 에 주석된다** (.52, `c0e06bef9`, 2026-09-22): `qo_get_attr_info ()` 가 세그먼트 대표 PT_NAME 에 `histogram = NULL, null_frequency = 0.0` 을 놓고 hist_stats 가 있으면 둘을 같이 채운다(c0e06bef9 query_graph.c:5459-5473), `set_seg_node ()` 가 술어의 PT_NAME 으로 둘을 함께 복사한다(:3003-3004). 그래서 "헬퍼는 나눴는데 호출자는 곱하지 않는" 조합(히스토그램 있음 ∧ nf 미지)이 구조적으로 생기지 않고, 히스토그램 없는 컬럼은 nf 0.0 → 곱이 항등이다(qo_expr_selectivity 절 "일반화" 항목과 짝). 같은 주석은 XASL 생성 시점에 "이 컬럼에 히스토그램이 있나" 를 값 프로브 없이 판정하는 데 쓸 수 있다 — 단 세그먼트 대표가 아닌 동일 컬럼 노드는 NULL 일 수 있어 `histogram_blob_from_class_cache ()` 폴백이 필요하다(.52, c0e06bef9, 2026-09-22). develop `2d925cb86` 재확인: 주석 query_graph.c:5520-5538, 복사 :3071-3072, 폴백 histogram_cl.cpp:666. — 정소희(.50) 2026-10-28

### stats_get_histogram / db_get_histogram_committed (histogram/histogram_cl.cpp:2567 / :2522)

**옵티마이저의 히스토그램 읽기는 잠금 조회였고, CBRD-27369 로 무잠금 커밋 읽기가 됐다** (.51, PR#7900 `1b6e8e3a0` 기준, 2026-09-09 실측 → 수정됨: `0d0809963` CBRD-27369, 2026-09-30): 머지 전에는 `stats_get_histogram` → `db_get_histogram` → `db_find_multi_unique (DB_FETCH_READ)` → `obj_find_multi_attr` → 클라이언트 `btree_find_unique`(서버 `sbtree_find_unique` 가 `S_SELECT_WITH_LOCK` 고정) → 행 S 락, 이어서 `au_fetch_instance_force (..., LC_FETCH_DIRTY_VERSION)` → 또 S 락이었다. `_db_histogram` 은 `tf_is_catalog_class`(ct_Classes)에 없어 무잠금 카탈로그 경로도 안 탔다. 그래서 오토커밋 OFF 세션이 `UPDATE STATISTICS` 를 커밋하지 않으면 같은 테이블 SELECT 컴파일이 커밋까지 블록됐고(lockdb: `_db_histogram` 인스턴스 X 보유 / S 대기), 반대로 컴파일만 한 세션의 S 락도 커밋까지 남아 `UPDATE STATISTICS` 의 X 를 막았다. develop `2d925cb86` 은 `stats_get_histogram ()`(:2567)이 `db_get_histogram_committed ()`(:2522 → `obj_find_multi_attr_committed ()`)로 마지막 커밋 버전을 락 없이, 트랜잭션 MVCC 스냅샷도 만들지 않고 읽는다(호출 :2646, 함수 머리 주석 :2507-2520). 잠그는 `db_get_histogram ()`(:2469)은 `;info histogram`·DDL 경로에만 남고, 쓰는 쪽은 조회 시점에 행 X 를 잡는다(`db_find_multi_unique_for_update ()`). — 정소희(.50) 2026-10-28
- ✅ **리뷰 체크포인트**: 컴파일 경로에서 카탈로그 행을 읽는 새 코드가 `db_get_histogram ()` 같은 잠금 조회를 쓰면, 미커밋 `UPDATE STATISTICS` 뒤에서 컴파일이 블록되는 회귀다.

### 히스토그램 일반 (histogram/)

**현재 히스토그램이 커버하는 범위 (equi-depth + MCV + HLL NDV)** — `feature/reservoir-sampling`(0b84bbaac, CBRD-26936) 계열 기준으로 equi-depth 히스토그램(HST2 blob, 카탈로그 `_db_histogram`) + MCV(1% 임계) + HLL 기반 NDV + 정확한 null_frequency 가 구현돼 있다(통계 수집 후속은 develop 532ce4b6d CBRD-26959 #7476). 선택도 함수는 등호(MCV 매칭 + 잔여 분산, `histogram_get_equal_selectivity` :1032), 범위(버킷 보간 — 템플릿 `comp_parts()` develop histogram_cl.cpp:908, :1299-1311 에서 int64/double/string_view/uint64 인스턴스화), LIKE(:1824), NULL 검사까지 갖췄다.
- ✅ **리뷰 체크포인트**: 새 선택도 경로 추가 시 기존 등호/범위/LIKE/NULL 검사 선택도와 중복 구현하지 말고, 버킷 보간이 필요하면 `comp_parts()` 를 재사용할 것.

**표현식 f(col) 에는 히스토그램이 적용되지 않는다 (PT_NAME 만 인정)** — 히스토그램 조회는 피연산자가 `PT_NAME` 인 경우에만 성립한다(`if (lhs == NULL || lhs->node_type != PT_NAME)` develop histogram_cl.cpp:598, :2524). `UPPER(col) = 'X'`, `col + 1 > 10` 같은 표현식은 히스토그램을 못 타고 기본 상수로 떨어진다(표현식 통계 기능 없음).
- ✅ **리뷰 체크포인트**: 선택도 변경이 표현식 노드를 다루려 하면 PT_NAME 제한을 우회/확장하는지 확인하고, 확장 시 파스트리 노드 타입별 안전성(부작용 있는 함수 등)을 같이 볼 것.

**develop 의 히스토그램 센티널 버그(-1 vs 0) — '4버킷 통계'의 정체** — 실험에서 '4버킷 통계'로 관측되던 상태는 실제로는 당시 develop 의 센티널 값 버그(-1 과 0 혼동)로 히스토그램이 의도대로 쓰이지 않던 것이며, CBRD-26959 의 커밋 c4bb4b04a 에서 수정됐다. 따라서 그 이전 develop 에서 얻은 '4버킷이 더 빠르다'는 관측은 통계 정밀도의 효과가 아니라 버그로 인한 우연이다.
- ✅ **리뷰 체크포인트**: 히스토그램/통계 코드에서 '없음'을 나타내는 센티널이 -1 인지 0 인지 혼동되지 않는지, 신규 코드가 두 값을 모두 미설정으로 처리하는지 확인할 것.

**히스토그램 생성 SQL/코드를 바꾸면 저장된 히스토그램은 반드시 재생성해야 한다** — 히스토그램 빌드 템플릿이나 NDV 계산식을 바꿔도 이미 카탈로그(`_db_histogram`)에 저장된 히스토그램은 갱신되지 않는다. 코드 변경 후 테이블 × 컬럼 루프로 `ANALYZE TABLE <t> UPDATE HISTOGRAM ON <cols>` 재생성이 필요하고, 원래 샘플이 100% 였던 것만 FULLSCAN 으로 재생성해야 스케일이 어긋나지 않는다. 도구 — **develop 재확인 완료(04620b2ce, 2026-09-01 .52 실측): CBRD-26959 계열이 머지되어
구 문법이 파서에서 삭제됐다.** `ANALYZE TABLE ...`은 `unexpected 'analyze'`(ANALYZE는
ANALYZE PARTITION 전용), `SHOW HISTOGRAM`도 삭제. 현행 문법은 하나다:
`UPDATE STATISTICS ON [t] WITH FULLSCAN, 300 BUCKETS;` (옵션: FULLSCAN | RANDOM SEED |
NO HISTOGRAM | DROP HISTOGRAM | <n> BUCKETS). **WITH 절을 생략하면 문법 오류 없이 샘플링 +
기본 버킷이 되어 조용히 표준과 달라진다.** 조회는 csql `;info histogram <class> [<attr>]`.
`update statistics on all classes`도 히스토그램을 만들지만 **전수스캔이 아니고 버킷 수만으로는
구분이 안 된다** — 검증은 적재 로그의 `Statistics updated successfully` 줄 수를 센다.
- ✅ **리뷰 체크포인트**: 히스토그램 빌드 경로 변경 PR 에서 '재생성 없이 측정한 결과'가 근거로 제시되면 무효로 보고, 샘플/FULLSCAN 여부가 원본과 동일하게 재생성됐는지도 확인할 것.

**히스토그램 리더의 행수 스케일은 샘플 스케일로 자기일관적이다** — 리더의 `total_rows()` 는 마지막 버킷의 누적값이며 샘플 스케일 기준이다. 덤프의 버킷 행수와 같은 스케일이므로 내부적으로 일관되는데, 전체 테이블 실제 행수를 분모로 놓고 손계산하면 ×2 수준의 '스케일 버그'처럼 보인다 — 실제로는 계산자의 분모 선택 오류였다(과거 오진 사례).
- ✅ **리뷰 체크포인트**: 선택도 손검증 시 분모를 전체 테이블 행수가 아니라 SHOW HISTOGRAM 덤프의 샘플 스케일 행수로 맞추고, '스케일이 2배 틀렸다'는 지적은 분모 확인 전에 채택하지 말 것.

**Duj1(Haas-Stokes) NDV 추정기의 구현 위치와 계약** — Duj1 은 전적으로 `HISTOGRAM_WITH_SAMPLING_SCAN_QUERY_TEMPLATE`(histogram_cl.hpp) 안에서 SQL 로 구현돼 있다: `sampq` CTE 가 `q = LEAST(1, sample_rows / <클래스 행수>)` 를 계산하고, hist_grouped 의 approx_ndv = `CAST(ROUND(LEAST(n/q, GREATEST(d, n*d/(n - f1 + f1*q)))) AS BIGINT)`, 여기서 f1 = SUM(count=1 케이스). C 쪽(histogram_cl.cpp `get_histogram`)은 `sm_find_class` + `sm_get_class_with_statistics` → `stats->heap_num_objects` 로 클래스 카디널리티를 추가 `%lld` 인자로 전달하며, 이를 위해 query_buf 를 3072+ 로 키웠다. FULLSCAN 템플릿은 q=1 이면 Duj1 이 d 로 자연 퇴화하므로 손대지 않았고, 가드(f1==n, f1==0, clamp)가 필요하다는 점이 설계 전제다. *(행번호·상세는 CBRD-27094 @ faf5a3b2a 기준 재검증 — develop 반영 여부/위치 재확인 필요)*
- ✅ **리뷰 체크포인트**: 템플릿 문자열에 포맷 인자를 추가/변경했다면 query_buf 크기, 모든 호출부의 %lld 개수·순서, fullscan 템플릿과의 인자 불일치, 그리고 `sm_get_class_with_statistics` 로 얻은 통계 포인터의 수명/해제를 함께 확인할 것.

**Duj1 의 보정 한계 — 페이지 단위 SAMPLING_SCAN 클러스터링** — Duj1 적용으로 NDV(mc.company_id)가 160,692 → 199,557 로 올라갔으나 실제값 234,997 에는 못 미친다(sum bucket ndv 160,656 vs 234,997 @50% sample). 원인은 페이지 단위 SAMPLING_SCAN 이라 같은 페이지 내 값들이 클러스터링되어 f1(1회 등장 값) 통계가 실제 무작위 표본과 다르기 때문이다. 즉 추정기를 고쳐도 표본 추출 방식이 남은 오차의 상한을 결정한다.
- ✅ **리뷰 체크포인트**: NDV 추정 정확도 개선 주장은 표본 추출 방식(페이지 단위 vs 행 단위)을 함께 볼 것 — 무작위 표본을 전제한 추정기 공식을 페이지 샘플에 그대로 적용하는 코드에는 그 전제 위반을 지적할 것.

### hist::string_key_size_for_column / histogram_extract_key (histogram/histogram_reader.hpp:285 / histogram_cl.cpp:786)

**히스토그램 문자열 키 정규화는 `hist::string_key_size_for_column (column_type, s, size)` 하나가 정의한다 — 컬럼 타입이 CHAR 면 후행공백을 빼고, VARCHAR·BIT 는 바이트 그대로** (.50, PR#7977 `a82e6d6ae`, 2026-09-17 → 머지 `fd030f826` CBRD-27251, 2026-10-13): `histogram_reader.hpp` 의 inline 함수를 샘플러(`extract<std::string>`·`ndv_hll_hash`, histogram_sampler_sr.cpp)와 프로브(`histogram_extract_key`, histogram_cl.cpp, 인자 `column_type = reader.value_type ()`)가 공유한다. 그 전(develop 6497720ec)에는 프로브가 **리터럴 타입**을 기준으로 스트립해 VARCHAR 컬럼 + `'abcd '` 가 `'abcd'` MCV 에 맞았다(1,600행 재현 sel 0.125 vs 참값 100행) — 타입 검사기가 CHAR 리터럴을 VARCHAR 컬럼 타입으로 강제변환하지 않기 때문이다(src-parser §2 「pt_coerce_expr_arguments — 비교 피연산자의 문자열 타입」). develop `2d925cb86` 재확인: 정의 :285(계약 주석 :268-283), 샘플러 histogram_sampler_sr.cpp:531·:2552, 프로브 histogram_cl.cpp:860(호출 :1199·:1396). — 정소희(.50) 2026-10-28

**런타임 문자열 등가(`db_string_compare`, string_opfunc.c)는 `ignore_trailing_space=no`(기본, 히든 파라미터)일 때 양쪽이 모두 패딩 타입(CHAR)일 때만 후행공백을 무시하고, `yes` 면 항상 무시한다** (.50, 6497720ec, 2026-09-17): `ti = QSTR_IS_PADDED_LENGTH (t1) && QSTR_IS_PADDED_LENGTH (t2)`. 히스토그램 MCV 스윕(`string_values_equal_under_collation`)은 VARCHAR 로 DB_VALUE 를 만들어 이 함수를 부르므로 파라미터를 자동으로 따른다(`yes` 에서 `t_vc.c='abcd'` 0.2125=340행 ✓). 파라미터는 `static bool ignore_trailing_space` 로 프로세스당 1회 캐시된다. develop `2d925cb86` 재확인: string_opfunc.c:462·:469·:536-539, histogram_cl.cpp:2030-2045. — 정소희(.50) 2026-10-28

### comp_parts (histogram_cl.cpp:908)

**min/max·avg_width 미저장 → 첫 버킷 하한이 없어 근사 핵을 쓴다** — 히스토그램에 컬럼 min/max 와 avg_width 를 저장하지 않아 첫 버킷의 하한 경계값을 알 수 없고, 이는 범위 조건의 하단 경계 근처 선택도가 원리적으로 부정확한 원인이다. develop 주석이 문제를 그대로 서술한다: "The first bucket has no previous endpoint stored (its lower bound is unknown), so bucket_hi (b - 1) would read bucket record (uint) -1 -> assert in debug / out-of-bounds in release"(develop histogram_cl.cpp:923-930). 우회 방식: 옛 half-mass(절반 질량) 근사는 두 번째 버킷 폭을 아래로 미러링하는 방식으로 대체됐다("instead of half the first bucket's mass"). 근본 해결은 여전히 min/max 수집·저장이라 통계 수집 포맷 변경이 선행돼야 한다. *(원 메모의 histogram_cl.cpp:756-759 / 커밋 56e3aabf8 half-mass 는 행 번호 확인 필요 — 현재 소스와 불일치)*
- ✅ **리뷰 체크포인트**: 범위 선택도 버그는 histogram_cl.cpp:918-935 의 첫 버킷 하한 근사가 원인인지 먼저 의심할 것.

### histogram_get_join_selectivity (histogram_cl.cpp:1528)

**MCV 투포인터 조인 선택도 — develop 머지됨(10d0aa0e7, CBRD-26746 #7508)** — 양쪽 MCV 를 정렬해 투포인터로 매칭 → 매칭 MCV 기여분 + 잔여 확률을 `잔여/(nd - nmatches)` 로 분배(develop :1619-1639; many-to-many collation-aware 매칭은 양측 분모에서 각자의 matched distinct 를 제외한다는 주석 포함) → 최종적으로 `min(totalsel1, totalsel2)` 선택(:1641, 주석 "the smaller estimate is the view from the larger-NDV side") → 양쪽 (1-nf) 로 나눠 반환(:1643-1656, qo_expr_selectivity 절 참조) → 0 이면 `1/(total_rows1*total_rows2)` 바닥(:1660-1663). 히스토그램/MCV 부재 시 폴백은 기존 `1/max(icard)`. 검증: `t.kind_id=mc.company_type_id` sel 0.147469(손계산 일치), `cn.id=ci.person_role_id` 카디널리티 17.57M(null 제외 실제치 부합).
- ✅ **리뷰 체크포인트**: 조인 선택도 변경 시 세 단계(MCV 투포인터 / 잔여를 nd-nmatches 로 분배 / min(totalsel1,totalsel2))가 모두 보존되고 MCV·히스토그램 부재 시 폴백 경로가 살아있는지 확인할 것.

**조인 선택도는 히스토그램(MCV)을 쓴다 — 무너지는 자리는 "한쪽이 PK" 인 조인이다** (.52, `07480dfd1`, 2026-09-18, JOB 계약 — 「JOB 실측」 절 첫 줄): `qo_equal_selectivity`(07480dfd1 query_planner.c:10973)가 `attr=attr` 에서 이 함수를 **먼저** 부르고 `1/max(icard)` 는 실패 시 폴백이다(:10975-10985). 붕괴 기전: `matchprodfreq` 는 **양쪽 MCV 에 같은 값**이 있어야 기여하는데 스타형 스키마의 차원 테이블은 PK 라 쏠림이 0 이고(`keyword.id` 134,170 값 각 1행), 교집합이 비면 `otherfreq1 × (otherfreq2 + unmatchfreq2) / (nd2 − nmatches2)` ≈ **1/NDV** 만 남는다 = 평균 팬아웃. ✅ "조인이 히스토그램을 안 쓴다" 가 아니라 **한쪽이 PK 면 MCV 가 구조적으로 버려진다**(값을 알면 MCV 가 정답을 준다는 실측은 「JOB 실측」 절 `17a` ×1.012). develop `2d925cb86` 에서 같은 식(histogram_cl.cpp:1788·:1798, min :1802 — 재확인 2026-10-28). — 정소희(.50) 2026-10-28

**조인 선택도에 NDV clamp 가 없어 과대 계산된다 (20a 회귀)** — 조인 선택도 도입(ba0d955ee) 후 17a/17d/20a 의 조인 순서가 base 와 달라졌다 — per-term 선택도 값(`n.id=ci.person_id` 2.4e-7 등)이 평평한 비용 모델과 결합되어 순서가 악화됐다. 20a 의 직접 원인은 mk-cc 선택도가 3.53e-6→6.81e-6 으로 배증한 것이고, 그 원인은 `cc.movie_id` 의 NDV 가 93,514 인데 조인 상대인 title 도메인은 2.5M 이라 NDV clamp(작은 쪽 NDV 를 상대 도메인/조인 대상 크기로 제한)가 없기 때문이다(develop 코드에도 clamp 없음 — 재확인).
- ✅ **리뷰 체크포인트**: 조인 선택도 관련 변경은 양쪽 NDV clamp 적용 여부를 확인하고, per-term 선택도 값만으로 성공 판정하지 말고 최종 조인 순서/시간까지 확인할 것.

**histogram_get_eqjoin_selectivity Stage 3 의 버킷 오버랩 MIN 언더컷 (Card-cost defect #2) (develop 에 없음 — CBRD-27094 이전 실험 계열)** — `histogram_get_eqjoin_selectivity`(실험 브랜치 histogram_cl.cpp Stage 3)는 버킷쌍 기반 `overlap_residual_mass` 를 계산해 건전한 전역 fallback 값과 MIN 을 취했고, 이 때문에 선택도가 부당하게 낮아졌다. 17a 에서 `mc.company_id=cn.id`(FK→PK) sel 이 오버랩값 3.065e-6 로 전역 fallback 3.58e-6 을 언더컷했고(uniform 4.26e-6), 그 결과 t-vs-mc 부착 결정이 비용 1915 vs 1915 완전 동률이 되어 tie-break 가 순서를 결정했다. 오버랩 MIN 을 제거하자 attachment-order 매치 34→38/113, leaf 27→31/113, 회귀 0 이며 16b/17a/17e/2d(pattern-C 계열)가 새로 일치했다(검증: `SHOW HISTOGRAM movie_companies ON company_id` / `company_name ON id` 덤프). *(이 심볼은 CBRD-27094 브랜치에도 develop 에도 없다 — `histogram_get_join_selectivity` 만 존재)*
- ✅ **리뷰 체크포인트**: eqjoin 선택도 경로에 보정항(오버랩/잔여질량 등)을 MIN/MAX 로 끼워넣는 변경은 거부하고, 추가 항이 건전한 전역 추정을 아래로 끌어내리지 않는지 확인할 것.

**한쪽만 MCV 리스트가 있는 eqjoin fallback 이 MCV 행의 조인 질량을 통째로 누락 (Card-cost defect #3) (실험 브랜치 계열)** — 기존 fallback 은 `non_mcv_frac_l × non_mcv_frac_r / max(ndv)` 였는데, 이는 MCV 에 속한 행들의 조인 기여를 0 으로 만든다(mc 의 MCV 15.8% 행이 아무 기여도 안 함) → term sel 3.58e-6. Stage 3 에서 `!has_both_mcv_lists` 일 때 `selectivity_mass = 1/max(lhs_total_ndv, rhs_total_ndv)` 로 고치자 1/234,997 = 4.255e-6(이상값)이 나오고, max 를 쓰므로 정확한 PK 쪽 NDV 가 채택되어 LHS NDV 잡음에 강건해진다(17a 검증 mc⋈cn sel = 4.25537e-6).
- ✅ **리뷰 체크포인트**: MCV 경로 밖(non-MCV) 잔여 비율만 곱해 선택도를 만드는 코드가 보이면 MCV 행의 조인 질량이 사라지지 않는지 확인 — 분모는 min 이 아니라 max(NDV) 여야 하고 분자에 non_mcv_frac 곱이 남으면 재발이다.

**양쪽 모두 MCV 가 있는 many-to-many 조인은 여전히 과대추정 (위 두 수정과 무관)** — C-1(오버랩 언더컷 제거)/C-3(한쪽-MCV fallback) 수정은 `company_id=cn.id` 류의 한쪽-MCV/오버랩 케이스만 고친다. movie_id 계열의 many-to-many 조인은 양쪽에 MCV 리스트가 있어 both-MCV/overlap 경로로 들어가고 uniform(1/max(NDV)) 대비 과대추정이 남는다. 실측으로 stash(C-1+C-3+Duj1) 복원 시 movie_id 조인 4건의 선택도가 origin 과 바이트 단위로 동일했다(31b `mi_idx.movie_id=mk.movie_id` 2.174e-6 고정) — 즉 이 회귀들에 대해 두 수정은 완전히 무력(inert)이다.
- ✅ **리뷰 체크포인트**: eqjoin 선택도 수정이 특정 회귀를 고친다고 주장하면 그 조인이 both-MCV 경로인지 one-sided 경로인지부터 확인할 것 — 선택도 값이 그대로인지 비교하면 즉시 반증 가능하다.

### histogram_get_like_selectivity (histogram_cl.cpp:1824)

**LIKE prefix 를 (선택도 추정에서) 범위로 변환하지 않고 버킷 경계값 매칭만 한다 (편향)** — CUBRID 의 이 함수는 LIKE 접두사를 `[prefix, prefix+)` 범위 조건으로 바꾸는 변환 없이 MCV 매칭 + 버킷 경계값 매칭(`matched_non_mcv_buckets`, develop :1909-1920) + 휴리스틱만 쓴다. 경계값에만 의존하므로 접두사가 버킷 경계와 어긋나면 선택도가 편향된다. (인덱스 스캔용으로는 rewriter 가 prefix LIKE 에서 파생 BETWEEN 범위를 만들지만 — CBRD-27036, qo_iscan_cost 절 참조 — 그것은 스캔 범위이지 히스토그램 보간 선택도가 아니다.)
- ✅ **리뷰 체크포인트**: LIKE 선택도 개선 PR 은 접두사→범위 변환을 도입했는지 아니면 또 다른 휴리스틱을 얹었는지 구분할 것 — 후자는 편향을 다른 방향으로 옮길 뿐이다.

**develop 의 혼합식: 크기 기반 블렌드 + 클램프 (disagreement_boost 는 develop 에 없음)** — develop 은 비-MCV 추정을 히스토그램 크기로 가중한다: 버킷 100개 이상이면 경계값 매칭 비율을 전적으로 신뢰, 10~99개면 `w = size/100` 으로 패턴 휴리스틱과 블렌드, 10개 미만이면 휴리스틱 단독(:1931-1946). 결과는 [0.0001, 0.9999] 로 클램프(:1947-1955)하고, (1-nullfrac) 나눗셈 규약 후 `max(1/total_rows, sel)` 바닥을 적용한다(:1965-1975). 패턴 휴리스틱 `pattern_heuristic_selectivity`(:1670)는 상수 FIXED_CHAR 0.20 / ANY_CHAR 0.9 / WILDCARD 5.0 을 쓴다.

**disagreement_boost 가 매칭 버킷 0개일 때 패턴 휴리스틱을 0으로 지운다 (Card-cost defect #1) (develop 에 없음 — 실험 브랜치 계열)** — 패턴에 매칭되는 히스토그램 버킷이 0개일 때(희귀 패턴에서는 정상 — 샘플된 bucket_hi 값이 수백 개뿐) `disagreement_boost` 가 boosted_weight 를 1 로 밀어 `pattern_heuristic_selectivity` 를 0 으로 만든다. 그 결과 sel 이 1/NCARD 로 클램프되어 `k.keyword LIKE '%sequel%'` 가 정확히 1행으로 추정된다(실제 30). 패턴 휴리스틱 자체는 단독으로 ~43행이다 — 수정 방향은 `matched_non_mcv_buckets == 0` 이면 boost 를 적용하지 말고 pattern_sel 로 폴백하는 것. *(`disagreement_boost` 심볼은 CBRD-27094 브랜치에도 develop 에도 없음 — 실험 브랜치 한정)*
- ✅ **리뷰 체크포인트**: 패턴 선택도 코드에서 '매칭 버킷 0개'가 에러가 아니라 정상 경로로 처리되고 휴리스틱 폴백이 살아 있는지, 가중치 혼합식이 한쪽 항을 0으로 만들 수 있는 구조인지 확인할 것.

**CHAR 컬럼 LIKE/REGEXP 의 히스토그램 추정은 저장값을 컬럼 선언 폭(문자 수)까지 재패딩해 매칭한다 — `histogram_repad_char_value`** (.50, PR#7977, 2026-09-17 → 머지 `fd030f826` CBRD-27251): 런타임은 패딩된 힙 값에 패턴을 적용하므로(`t_ch.c LIKE 'abcd %'` 340행) 스트립된 저장값으로는 0.000625 로 과소추정했다. develop `2d925cb86`(histogram_cl.cpp:1942, 컨텍스트 `histogram_repad_ctx ()` :1923-1940)은 타입·선언 폭을 히스토그램 blob 헤더(`reader.value_type ()`·`value_precision ()`, 샘플러가 본 값)에서, 코드셋은 술어가 해석된 collation 에서 얻는다 — CHAR 가 아니거나 폭이 없으면(≤0) 재패딩하지 않고, `intl_char_count` 가 다루는 코드셋 4종(ISO88591·RAW_BYTES·KSC5601_EUC·UTF8) 밖이면 건너뛴다. 소비처 `like_match_value` :1977(재패딩 :1986)·:2280. — 정소희(.50) 2026-10-28

### qo_rewrite_like_terms / qo_rewrite_like_for_index_scan (rewriter/query_rewrite_term.c:2547 / :2380)

**LIKE 항은 `LIKE 'abc'` → 등가, `LIKE 'abc%'`·`'abc %'` → 범위 항 + 잔여 LIKE 항으로 재작성되고, 잔여 LIKE 항의 sel 은 like 추정 / 범위 추정(상한 1)이다** (.50, 6497720ec 실측, 2026-09-17): 파생 범위는 `PT_EXPR_INFO_LIKE_DERIVED_RANGE`, 원 LIKE 는 `PT_EXPR_INFO_LIKE_HAS_DERIVED_RANGE` 로 짝지어지고, `qo_derived_term_compensate ()`(query_graph.c, CBRD-27306 `a64ba7ab9`)가 원 술어에 조건부 몫 `sel (origin) / sel (derived)` 만 남긴다(1 로 상한; like 추정이 범위 추정보다 크면 범위 쪽을 like 추정까지 올리고 LIKE 는 1 — develop `2d925cb86` :9026-9144; 인덱스 비용 쪽 상쇄는 qo_iscan_cost 절 「LIKE prefix 파생 범위와의 중복 상쇄」). `set optimization level 513` 출력의 term 은 sel 순 정렬이라 `term[0]` 만 보면 LIKE 추정을 오독한다 — REGEXP 항(재작성 없음)으로 확인하는 게 정확하다. — 정소희(.50) 2026-10-28

**host variable 패턴 `col LIKE ?` 도 컴파일 시 generic 파생 range 를 얻는다** (.52, c0e06bef9, 2026-09-22): `qo_rewrite_like_terms ()` 가 `pt_is_pseudo_const (pattern)` 분기에서 `qo_rewrite_like_for_index_scan ()` 을 불러 `col RANGE (like_match_lower_bound(?) ge_lt like_match_upper_bound(?))` 를 붙이고 `PT_EXPR_INFO_LIKE_DERIVED_RANGE` 를 세운다 — PREPARE 플랜 덤프 `term[0]: s range (like_match_lower_bound(?:0) ge_lt like_match_upper_bound(?:0)) (sel 0.1)` 로 확인. 경계가 식이라 그 항은 히스토그램 범위 추정을 못 받고 기본값에 머문다(→ §3). ✅ "`LIKE ?` 는 리라이트가 비대칭이라 bounded index scan 을 못 탄다" 는 전제(CBRD-27143 초기 서술)는 성립하지 않는다. develop `2d925cb86` 재확인: 분기 query_rewrite_term.c:2639-2656, 플래그 :2446. — 정소희(.50) 2026-10-28

**상수 접두어 LIKE 는 파생 경계가 접혀 자동 파라미터화되므로 같은 문장 텍스트의 모든 접두어 패턴이 XASL 캐시 엔트리 하나를 공유하고, 플랜은 첫 패턴의 값으로 고른다** (.52, c0e06bef9, 2026-09-22): `select count(pad) from t where s like 'abc%'`(sscan, sel 0.8999) 뒤 `'xyz%'` 는 플랜 덤프 없이 캐시 히트로 같은 sscan. 결과는 정확하고 플랜만 첫값 고정 — bind peek 의 OFF 계약(develop `620ceaf6a` 이전)과 같은 성질(설계 사실). `620ceaf6a`(CBRD-27490, 2026-10-21)는 `histogram_bind_fingerprint ()` 를 UINT64 양자화 해시(EQ sel×1e12·범위 sel×100)에서 술어별 예상 행 수 벡터 + 밴드 비교(`BIND_WATCH_BAND` 1.5배·힌트 1.1배·`BIND_WATCH_ROW_FLOOR` 1,000행, histogram_cl.hpp:181-189)로 바꾸고 플랜 변형(`plan_cache_bind_variants`, 기본 5)을 들였다 — 정리는 src-compat §2 「do_replan_statement_with_bind_peek / do_replan_statement_internal」. 그 지문은 사용자 호스트 변수만 세고 자동 파라미터(index ≥ `host_var_count`)는 뺀다(`histogram_is_user_host_var ()` histogram_cl.cpp:2884, 주석 :2878-2882) — 그래서 이 성질은 develop `2d925cb86` 에도 남는다(코드 판독, 실측 안 함). — 정소희(.50) 2026-10-28

### HistogramReader::reset (histogram_reader.cpp:72)

**구버전 히스토그램 blob 은 v2 리더가 조용히 거부하고 폴백한다 (단, per-term 진단 플래그가 있다)** — `reset()` 은 크기(develop :75), `HST2` 매직(:82), 버전==2(:86), `total_size_ != blob_.size()`(:98-104) 가드를 갖고, 불일치 blob 을 에러 없이 `ER_FAILED` 로 돌려보낸다. 주석이 의도를 명시한다: "an old-format (HST1) or corrupt record. Reject it gracefully so callers fall back to default estimates". 즉 새 통계 코드는 '동작하지 않는' 게 아니라 '아무 말 없이 옛 경로로 도는' 형태로 실패하므로, 통계를 재생성하지 않은 DB 에서는 개선 효과가 0 으로 측정된다. 진단 훅: `env->sel_hist_used`/`env->sel_hist_fallback`(query_graph.h:977-978)과 `QO_TERM_SEL_FROM_HISTOGRAM`(qo_analyze_term 절 참조)으로 어느 term 이 히스토그램을 실제로 탔는지 구분할 수 있다.
- ✅ **리뷰 체크포인트**: 히스토그램 포맷/버전 변경 PR 은 리더의 버전 불일치가 `sel_hist_fallback` 등으로 관측 가능한지, 그리고 성능·정확도 검증 전에 히스토그램을 재생성했는지 확인할 것.

### qo_extract_or_restrictions (rewriter/query_rewrite_term.c:4795)

**멀티 spec OR 에서 단일 spec 제약 추출 — develop 머지됨(c283e799d, CBRD-27171 #7613)** — join-OR 의 모든 분기가 한 릴레이션 전용 조건을 가지면 그 OR 를 해당 릴레이션의 중복 제약으로 WHERE 에 추가한다(TPC-H q19 가 canonical shape 라고 함수 주석이 명시). rewriter 레벨 구현이며 호출부는 query_rewrite.c:480. 검토 당시 후보 위치로 CNF 변환/term 분류부(query_graph.c 의 `qo_analyze_term`)도 거론됐으므로 동일 기능이 여러 레이어에 중복 추가되지 않는지 주의해야 한다.
- ✅ **리뷰 체크포인트**: OR 추출 변경이 rewriter 와 query_graph.c/qo_analyze_term 양쪽에 중복으로 들어가지 않았는지, '모든 분기가 해당 릴레이션 전용 조건을 가진다'는 전제를 정확히 검사하는지(한 분기라도 조건이 없으면 부정확한 제약) 확인할 것.

**location != 0 (outer join ON 유래) 팩터는 반드시 제외해야 한다** — outer join 의 ON 절에서 유래한 팩터(location != 0)를 OR 추출 대상에 포함하면 outer join 의 null-확장 행이 사라져 결과가 달라진다. develop 머지본은 이 가드를 내장했다: "a factor that came from an outer join's ON condition (location > 0) is evaluated at its join level and does not reject the null-padded rows, while the derived filter would run at WHERE level and wrongly reject them"(develop :4824-4830). PR#7613 개발 중 커밋 4f6e24024 로 추가됐고, LEFT JOIN 항등식(4097 = 4074 + 23)으로 검증했다. 추가 가드: `or_next` 체인이 달린 팩터는 flatten 이 disjunct 일부만 모아 과강한 제약을 만들 수 있어 스킵(:4815-4820), disjunct 수 상한 `QO_OR_EXTRACT_MAX_DISJUNCTS 8`.
- ✅ **리뷰 체크포인트**: 제약을 WHERE 로 끌어올리는(pull-up) 모든 변형에서 term 의 location 값 가드가 있는지, LEFT/RIGHT JOIN 회귀 케이스(전체 행수 = 매칭 행수 + null-확장 행수)로 검증됐는지 확인할 것.

**선택도 이중계상은 머지본이 PT_EXPR_INFO_OR_DERIVED 마크로 보정한다** — 추출된 OR 를 원래 join term 과 함께 남긴 채 단일 릴레이션 제약으로 추가하면 같은 조건이 두 번 곱해져 선택도가 이중 계산된다(PR#7613 draft 시점에는 '남은 개선 ①'). develop 머지본은 파생 팩터를 `PT_EXPR_INFO_OR_DERIVED`(모양에 따라 `_EXPENSIVE` 추가)로 마크하고, 이 마크가 QO_TERM 플래그로 전달되어 `qo_node_add_sarg()` 가 행수 이중계상을 스킵하고 `make_pred_from_plan()` 이 인덱스가 채택하지 않은 비싼 복사본을 드랍한다(함수 주석 :4788-4794).
- ✅ **리뷰 체크포인트**: 중복 제약을 추가하는 변경에 선택도 보정(추출 절을 원 절의 선택도에서 나누거나 계산에서 제외)이 함께 들어갔는지 확인할 것 — 없으면 카디널리티 과소추정으로 다른 질의에 회귀가 생긴다.

**추출된 OR 가 하류에서 재전개되어 27-conjunct 로 풀리면 추가 1.3x 손해** — 추출 결과를 단일 term 형태로 유지하지 못하면 하류 처리에서 다시 전개되어 27-conjunct 형태가 되고, 단일 term 유지 대비 약 1.3배 느려진다(IMP-027 실측 0.293s vs 당시 출력 0.383s). draft 시점 '남은 개선 ②' 였다 — **develop 머지본이 단일 term 을 유지하는지는 미확인(재검증 필요)**.
- ✅ **리뷰 체크포인트**: 추출한 OR 절이 하류 CNF/term 전개에서 다시 분해되지 않고 하나의 term 으로 유지되는지 플랜/term 덤프로 확인할 것.

**`qo_extract_or_restrictions ()` 의 대상은 `pt_cnf ()` 가 분배하지 않고 하나로 유지한 OR 팩터다** (.52, 9ee8bac8b, 2026-09-28): `count_and_or > 100` 이면 `TRANSFORM_CNF_OR_COMPACT` 로 OR 를 분배하지 않는다(cnf.c:993). 분기가 한 conjunct 만 다르면 공통항 제거 후 `col IN (…)` 하나로 접혀 분배되므로 추출이 일어날 여지가 없다. develop `2d925cb86` 재확인(cnf.c:993, 상한 `QO_OR_EXTRACT_MAX_DISJUNCTS 8` query_rewrite_term.c:4891). — 정소희(.50) 2026-10-28
- ✅ **리뷰 체크포인트**: OR 추출 TC 는 분기마다 여러 conjunct 를 다르게 해야 상한(8분기)·추출 여부를 검사할 수 있다.

**통계 없는 테이블의 PREPARE 마커 플랜은 노드 card 0 이라 `sscan × sscan` NL 이 cost 1 로 선택될 수 있고, host variable 이 OR 안에 있으면 그 EXECUTE 는 카티션 규모 평가가 된다** (.52, 9ee8bac8b, 2026-09-28): 200k×20k 에서 10분 초과. — 정소희(.50) 2026-10-28
- ✅ **리뷰 체크포인트**: host variable 이 OR 안에 있는 TC 는 통계가 있는 국면에서만 돌린다.

**소형 인덱스 캡은 JOB 조인 순서를 바꾼다 — JOB 차원 테이블이 캡 구간에 들어간다** (2026-08-28 실측, `.51`)
— 위 '평탄 페널티' 를 고치는 방법으로 평탄항을 `MIN (descent, MAX (1, NCARD) * QO_CPU_WEIGHT)` 로
상한하는 안을 시도했는데, **JOB 플랜 10건이 바뀌고 그중 2건이 회귀**였다. JOB 은 대형 팩트 테이블만
있는 벤치가 아니다 — `ct`(company_type 4행), `cct1/cct2`(comp_cast_type 4행), `kt`(kind_type 6행),
`lt`(link_type 18행), `it`(info_type 113행) 같은 차원 테이블이 있고, 캡은 NCARD 가
`MAX(1, height) * BTREE_DESCENT_PAGE_OVERHEAD` (단층 50, 2층 100) 미만일 때 물리므로 **4~18행 차원
테이블의 인덱스 스캔이 거의 공짜가 되어 조인 순서 앞으로 끌려온다.**

가장 나쁜 결과는 `1a`·`1b` 의 조인 순서 변화다. 1a 는 수정 전 `it mi_idx mc ct t` 였던 순서가
캡 투입 후 `mc ct mi_idx it t` 로 바뀌었고 시간도 0.014s → 0.242s.
인터리브 median-of-5(rep 마다 팔 교대) + MAD 판정으로 1a +1629%, 27c +75%, 23c +8.7%, 15d +9.1%
회귀 대 개선 8건.

반면 **inner 전용 분리(`iscan_descent_cpu`)만 남긴 버전은 JOB 플랜에 완전히 중립**이다 — 113개
질의의 플랜 덤프가 비용 수치를 제외하면 base 와 **전건 동일**(구조·접근 방식 포함, 상이 0건).
원인 분리도 이 대조로 했다: 캡만 넣은 빌드와 (inner+캡) 빌드의 플랜이 **같은 10건, 같은 순서**로
바뀌어 캡이 단독 원인임이 드러났다. 최종 PR#7622 는 캡을 철회하고 inner 전용만 유지한다
(단일 커밋, JOB 235.3s → 207.5s / 개선 21·회귀 10·무변화 82, develop 04620b2ce 대비).

- ✅ **리뷰 체크포인트**: (1) "소형 테이블 보호" 목적의 상한·바닥을 넣을 때 **그 벤치의 차원
  테이블이 그 구간에 들어가는지** 행수로 확인할 것 — JOB 은 4~18행 차원 테이블을 가진다.
  (2) 비용모델 변경의 1차 증거는 시간이 아니라 **플랜 덤프 전수 대조**다. 플랜이 동일하면 실행
  경로가 같으므로 시간 차는 정의상 이 변경 탓이 아니다(측정 노이즈·베이스 차이로 귀속).
  (3) 한 커밋에 두 메커니즘을 넣으면 원인 분리에 빌드가 하나 더 든다 — 이 건이 실례다.


### qo_index_cardinality / qo_index_cardinality_with_dedup / qo_get_group_ndv (query_planner.c:11509 / :11579 / :707)

[출처 .50, 기준 develop 5f3a30d09 → PR#7856, CBRD-27140]

- develop 5f3a30d09 에서 반환형 `int`, 안쪽은 `INT64 ndv = info->ndv` 를 `INT_MAX` 로 clamp("need to change type to INT64" 주석) 한 뒤
  `MIN (ndv, cum_stats.pkeys[0])`. `pkeys[0]`(인덱스 부분키 NDV)이 int 라 2^31 초과 인덱스에서 음수가 되면 `pkeys[0] > 0` 가드에 걸려
  컬럼 NDV 만 남는다 — 즉 인덱스 NDV 오버플로의 실피해는 "인덱스 통계 상실 → 컬럼 NDV/폴백 상수" 이고, `qo_iscan_cost` 의
  `1/pkeys[index]` sel_limit(:2267), ISS `iss_leaves = pkeys[0]`(:2354), `qo_plan_cmp` 의 `a_keys/b_keys`(:4791~) 가 함께 폴백된다.
- PR#7856 이후 세 함수 반환 `INT64`, 호출부 `icard`/`group_ndv`/`NDV_INFO.total_ndv` 도 INT64, `QO_ATTR_CUM_STATS.keys/pkeys` INT64
  (`SIZEOF_ATTR_CUM_STATS_PKEYS` 가 `sizeof (INT64)`). 선택도 산식은 전부 `(double)` 로 나누므로 정밀도 변화 없음.
- `qo_get_col_product_ndv()`(:12074) 는 GROUP BY 컬럼들의 NDV 곱을 `total_ndv *=` 로 누적한다 — INT64 라도 컬럼 수가 많으면 넘칠 수 있고
  상한 clamp 가 없다(기존 int 시절부터). 미수정 관찰.

### 비용 모델 실측 캘리브레이션과 세 가지 함정 (.51, 기준 PR#7622 `0721d8da0`, 2026-09-02 release 실측)

- **단위 스케일은 행 단위에서 일관**하다: 1단위 ≈ 6 µs. pk 프로브(2단 인덱스, 커버링) = descent_cpu 0.29단위 = 실측 2.1 µs;
  hash build+probe 행 1쌍 = 0.15단위 = 0.95 µs. 반면 `HJ_MEM_ALLOC_CONSTANT`(구 1500)는 비용이 아니라 "작은 입력은 NL" 정책
  오프셋 — 실측 고정비는 ~100단위(1000×1000 해시 3 ms 중 0.6 ms). JOB 1a 에서는 이 오프셋이 NL 프로브 수 과소추정을 가려 주고
  있어 100 으로 내리면 hash 체인이 이겨 14 ms→303 ms. PR#7622 는 800 으로 낮추고 경계(25060 이 hash 를 고르려면 C<1244,
  1a 가 NL 을 지키려면 C>408)를 정의부 주석에 기록. 값 하나가 두 벤치마크 사이에 끼어 있다는 뜻이며, 근본 해법은 필터된
  차원 테이블을 거친 조인 카디널리티 추정(1c·5c·7a·9c 회귀와 같은 축).
- **`qo_iscan_cost` 커버링 분기의 `object_IO = 1.0`은 유령 힙 페이지**였다. variable 쪽에 남아 `qo_nljoin_cost` 의 분리 포화에서
  leaf 몫으로 분류돼 인덱스 페이지수에 포화되고, 비커버링 프로브의 진짜 힙 페이지는 힙 페이지수에 포화 → 힙 < 인덱스인 소형
  테이블에서 커버링 프로브가 더 비쌈(r_outer_join 60 vs 59). 0 으로 고쳐 커버링 = 비커버링 − 힙 페이지. **랜딩 리프를
  프로브당 IO 로 세는 대안은 틀렸다**: 리프 fix CPU 는 `descent_cpu` 의 `(height+1)` 단계에 이미 있고, 큰 인덱스(mi.movie_id
  수만 페이지)를 수천 번 프로브하는 경로가 "리프 전부 1회 IO"를 물어 JOB 23a 0.58→1.33 s(폐기, `4c03b97e3`).
- **`qo_plan_cmp` 의 RBO 밴드가 토이 TC 판정의 실체**다: 비-LIMIT 는 Δ≥`RBO_CHECK_COST`(50) AND 비≥`RBO_CHECK_RATIO`(1.2)
  일 때만 비용으로 결정, LIMIT 는 비≥10. 그 안은 구조 규칙(`qo_plan_iscan_terms_cmp` 의 "range term 많은 인덱스 우선" 등) →
  비용 855 vs 2661(비 1.18)인 cbrd_25382_1 이 term 3개인 i_a(2행/프로브)를 term 1개인 i_c(1행)보다 고른다. 비용 모델을 고쳐도
  두 후보가 밴드 안에 있으면 결과는 RBO 가 정한다 — TC 플랜 diff 를 볼 때 먼저 밴드 안인지 확인할 것.
- 트레이스 `parallel workers` 줄은 `parallel_hash_join_page_threshold`(hidden, 기본 2048 페이지) 아래에선 안 나온다. CI 환경은
  이 줄이 나오는 답안을 갖고 있으므로 로컬 재현엔 `=1` 이 필요했다(cbrd_25382_1·24906_1/2).

### JOB 실측 — 조인 탐색·힌트·병렬·카디널리티 (.52, develop `07480dfd1`, 2026-09-18)

측정 계약 `AK-par4`: JOB 113질의(DB `joinorder`), `parallelism=4`(제품 기본값)·`data_buffer_size=16G`·`taskset -c 0-15`, 21테이블 `UPDATE STATISTICS … WITH FULLSCAN, 300 BUCKETS` 성공 21/21 후 서버 재기동, `recompile` 없이 warmup 1패스(정상상태), 기준 develop `07480dfd1`(release) — 카디널리티 측정은 별도 `qref` 레인(직렬 + 전 스텝 `NO_USE_HASH` + `memoize_memory_limit=0`). 이 절과 §3 의 JOB 항목은 이 계약이 전제다. 행 번호는 `07480dfd1` 기준.

#### 조인 탐색·힌트 — planner_visit_node / add_hint / qo_examine_*_join / 힌트 이름 검증

- **플래너는 구조적으로 left-deep 전용이다 — 어떤 힌트로도 bushy 를 만들 수 없다** (.52, `07480dfd1`): 조인 탐색의 tail 이 항상 단일 노드다(query_planner.c:7778 `tail_info = planner->node_info[QO_NODE_IDX (tail_node)]`; head 만 다중 노드 prefix, :7769). 예외는 연결 없는 partition 을 합치는 `qo_cp_new`(:10061)뿐이고 힌트로 제어되지 않는다. — 정소희(.50) 2026-10-28
- **`ORDERED` 는 FROM 순서 전체 사슬을 강제하고 동시에 탐색을 full DP 로 올린다. `LEADING` 은 올리지 않는다** (.52, `07480dfd1`): `add_hint ()` 가 노드 i 에 `OUTER_DEP_SET(i) = OUTER_DEP_SET(i-1) ∪ {i-1}` 을 건다(query_graph.c:4455-4472). `join_unit` 은 `num_path_inner || (hint & PT_HINT_ORDERED)` 일 때만 `nodes_cnt` 가 되고 아니면 예산 기반이다(query_planner.c:9850-9861, budget 320000 / `QO_JOIN_UNIT_MAX` 8 — planner_visit_node 절 "부분 조인 탐색은 열거 예산으로 제한된다"). 즉 **무힌트는 9테이블 이상에서 greedy 부분탐색**을 탄다 — JOB 113개 중 절반이 그 구간. ✅ 힌트 답지와 무힌트 baseline 의 시간 차에는 "탐색 폭" 성분이 섞일 수 있다. — 정소희(.50) 2026-10-28
- **조인 방법 힌트는 그 스텝의 inner 노드에서만 읽힌다 — FROM 첫 항목에 건 방법 힌트는 무효다** (.52, `07480dfd1`): `qo_examine_idx_join` :6505/:6509, `qo_examine_nl_join` :6639-6641, `qo_examine_merge_join` :6791-6794, `qo_examine_hash_join` :6955-6971(RIGHT OUTER 일 때만 outer 에서 읽음). `ORDERED` 와 함께 쓰면 **조인 하나하나를 지정**할 수 있다(조인 k 의 방법 = FROM (k+1)번째 별칭의 힌트). 실측: JOB 113질의 × 3레인 = 339건이 의도대로 실현됐고, 864개 조인 전부를 해시로 만드는 것도 성립한다(전부 등가조인이라). — 정소희(.50) 2026-10-28
- **힌트 인자 별칭이 하나라도 안 맞으면 그 질의의 힌트 전체가 경고 없이 삭제된다** (.52, `07480dfd1`): `LEADING`/`USE_NL`/`USE_IDX`/`USE_MERGE` 는 REQUIRE_ALL_MATCH → name_resolution.c:7893-7952, 실패 시 :8007-8010 에서 `hint = PT_HINT_NONE`. 반면 `USE_HASH`/`NO_USE_HASH`/`INDEX_SS`/`INDEX_LS` 는 DISCARD_NO_MATCH(안 맞는 이름만 버림). 실사례: `~/dev/tests/joinorder/queries/benchmark/answer/31a_answer.sql` 은 `LEADING(it1, …)` 인데 31a 의 FROM 에 `it1` 이 없어 답지 전체가 무힌트로 실행되고 있었다. ✅ 리뷰 체크포인트: 힌트를 쓴 TC·벤치가 "힌트가 안 먹는다"로 보이면 먼저 **별칭 오타**를 의심한다. — 정소희(.50) 2026-10-28
- **강제 순서로 유효 플랜이 안 나오면 플래너가 힌트를 전부 버리고 무힌트로 재플래닝한다** (.52, `07480dfd1`): `qo_optimize_query` 가 NULL → xasl_generation.c:18255-18300 에서 `hint_ignored=true`, `hint=PT_HINT_NONE`. detailed dump 의 `[Warning: HINT ignored]` 로만 드러난다. 원인 대부분은 교차곱 스텝(query_planner.c:8082-8092 `edge_cnt==0`) 또는 `idx_join_cnt==0` 인 스텝의 `USE_IDX`(:8290-8297, :8343). ✅ 힌트 기반 측정은 **반드시 플랜 덤프로 실효를 검증**해야 한다. — 정소희(.50) 2026-10-28
- **`USING INDEX` 부분 목록은 나열되지 않은 테이블을 자유롭게 놔둔다. 테이블별 `alias.NONE` 이 있다** (.52, `07480dfd1`): `add_using_index` 가 `n == 0 && !is_none` 이면 `QO_NODE_USING_INDEX = NULL` 로 남긴다(query_graph.c:4712-4717) → 그 테이블은 인덱스 자유 선택. 테이블별 인덱스 금지는 `identifier DOT NONE`(csql_grammar.y:14227, `PT_IDX_HINT_CLASS_NONE`). 스키마에 없는 인덱스 이름은 **경고도 로그도 없이** 그 항목만 삭제된다(view_transform.c:7705-7728 의 `er_clearid ()` + `pt_reset_error ()`, `error_log_warning` 기본 false). ✅ 인덱스를 고정하려면 **전 별칭 명시 + 이름 기계 검증**이 필요하다. — 정소희(.50) 2026-10-28
- **merge join 은 `optimizer_enable_merge_join` 이 PRM_HIDDEN·기본 false 라 `USE_MERGE` 없이는 나오지 않는다** (.52, `07480dfd1`): system_parameter.c:3548-3553, query_planner.c:6806-6810(힌트 분기 뒤에 와서 `USE_MERGE` 가 파라미터를 이긴다). JOB 113질의 무힌트 플랜에 m-join 0건. — 정소희(.50) 2026-10-28
- **JOB 무힌트 조인방법 분포 = idx-join 840 / hash-join 24 / nl-join 0 / m-join 0 (864 조인)** (.52, `07480dfd1`, 2026-09-18): 113질의 `SET OPTIMIZATION LEVEL 514` 전수 덤프. 2026-06 분석의 "864 전부 idx-join, 해시 0"(qo_hjoin_cost 절)은 **낡았다** — CBRD-26475 게이트 제거 효과. 해시가 선택된 질의 14개: `1c 1d 5c 8c 8d 9c 9d 10c 13a 13d 15d 18c 19d 23a`. — 정소희(.50) 2026-10-28

#### 병렬과 비용 — qo_*_cost / qo_plan_cmp / parallel_opt_use / qo_top_plan_new / compute_parallel_degree

- **옵티마이저 비용식은 병렬을 변수로 삼지 않는다** (.52, `07480dfd1`, 2026-09-18, CLIENT 컴파일 경로): 세 층에서 확인. ① **비용 함수 9종**(`qo_sscan_cost` 1905 / `qo_iscan_cost` 2332 / `qo_sort_cost` 3043 / `qo_nljoin_cost` 3759 / `qo_mjoin_cost` 3952 / `qo_hjoin_cost` 4031 / `qo_follow_cost` 4349 / `qo_worst_cost` 4504 / `qo_zero_cost` 4520, 전부 query_planner.c) 어디에도 워커 수로 나누는 항도 병렬 셋업 상수도 없다 — 이들이 읽는 시스템 파라미터는 `SR_NBUFFERS`(3122·3139)·`MAX_HASH_LIST_SCAN_SIZE`(4098)·`PB_NBUFFERS`(4376·4385) 셋뿐. ② **플랜 비교** `qo_plan_cmp`(4613)는 fixed/variable × cpu/io 네 항 합만 본다(4635~4638, 최종 `cost_cmp:` 5345). ③ **후보 생성 게이트** `qo_examine_hash_join`(7082)의 진입 조건도 병렬과 무관하다(7094·7103·7132~7139) — "병렬이 되니까 해시조인을 후보로 올린다" 같은 간접 경로도 없다. `QO_PLANTYPE` 은 SCAN/SORT/JOIN/FOLLOW/WORST 5종뿐이고(query_planner.h:42) 부분경로 목록 개념이 없다. develop `2d925cb86`: 비용 함수가 읽는 파라미터에 `cost_*` 단가 5종(`fa551431b`)이 더해졌으나 병렬 관련 항은 여전히 없다(query_planner.c 의 `parallel` 참조는 비용 함수 밖뿐 — 재확인 2026-10-28). — 정소희(.50) 2026-10-28
- **`plan->parallel_opt_use` 는 저울의 추가 아니라 승자에게 붙이는 라벨이다** (.52, `07480dfd1`, 2026-09-18): 전 소스 참조가 4곳뿐 — 선언 query_planner.h:235, 초기화 query_planner.c:563, 설정 :3377(`qo_join_new`(3183) 안, 즉 후보 조인마다·비용계산 `qo_plan_compute_cost`(3387) **직전**), 소비 **plan_generation.c:2855 한 곳**. 소비처는 `xasl->parallelism` 에 힌트값/`0`(disable)/`-1`(런타임 auto-compute)를 매핑할 뿐이고, 이 함수는 이미 승자가 정해진 뒤의 XASL 생성기다. 판정 함수 `qo_check_hjoin_for_parallel_opt`(14595~14728)는 힌트와 적격성(MERGE 문, PARALLEL_ENABLE 없는 SP·메서드)만 보는 **부작용 없는 순수 분류 함수**라 간접 영향도 없다. 인덱스 스캔 병렬도도 `qo_apply_parallel_index_scan_threshold` 가 `qo_to_xasl ()` 진입부(plan_generation.c:3316, 주석 "already optimized")에서 PT_SPEC 에 써넣을 뿐이다. develop `2d925cb86` 은 참조가 5곳 — `qo_plan_signature ()` 의 플랜 모양 지문(query_planner.c:12872, CBRD-27490 `620ceaf6a`)이 늘었으나 이것도 비용 비교가 아니다(재확인 2026-10-28). — 정소희(.50) 2026-10-28
- **단 하나의 예외 — 병렬 *가능성* 이 플랜 모양을 바꾸는 자리가 있고 그 비용은 비교에 들어간다** (.52, `07480dfd1`, 2026-09-18): `qo_top_plan_new`(query_planner.c:1236)의 1445~1466 이 `plan->need_final_sort` 면 `SORT_ORDERBY` 플랜을 얹는다 — 주석 "a hash join may not preserve the order of its probe input **when partitioned or run in parallel**". `qo_top_plan_new` 은 `qo_plan_compute_cost` 직후에 불리므로(`qo_join_new` 3387 → 3429) 얹힌 sort 는 `qo_sort_cost` 로 값이 매겨져 `qo_plan_cmp` 비교에 **실제로 들어간다**. ⚠ 다만 분기 조건은 `need_final_sort`(hash/merge join 이면 3416·3424 에서 무조건 세움)뿐이고 병렬 파라미터·힌트·차수를 보지 않는다 — **병렬성을 가정한 무조건 보수 규칙**이지 병렬성을 변수로 삼는 비용항이 아니다. 그래도 "병렬은 플랜에 영향 0" 이라고 쓰면 과하다. — 정소희(.50) 2026-10-28
- **⚠ 측정 함정 — `parallelism` 은 세션 중 못 바꾼다. 병렬을 끄려면 힌트를 쓴다** (.52, `07480dfd1`, 2026-09-18): `parallel_query::compute_parallel_degree ()`(px_parallel.cpp:36)가 `parallelism` 과 페이지 임계값 3개를 **`static` + `std::call_once`** 로 캐시한다(43~56) — 서버 프로세스 수명 동안 1회만 읽는다. 게다가 `PRM_ID_PARALLELISM` 의 플래그는 `PRM_FOR_SERVER | PRM_FOR_CLIENT | PRM_FORCE_SERVER` 로 **`PRM_USER_CHANGE` 가 없고**(system_parameter.c:5146), 임계값 3개는 `PRM_FOR_SERVER | PRM_HIDDEN`(5170·5194·5206)이다. 즉 `SET SYSTEM PARAMETERS 'parallelism=1'` 로는 직렬 재측정이 **안 된다** — `cubrid.conf` 를 고치고 서버를 재기동해야 한다. 반면 **힌트는 캐시를 우회한다**: `hint_degree >= 2` 면 로그 계단도 `parallelism` 상한도 건너뛰고 `MIN (hint_degree, system_core_count)` 를 그대로 쓰고(126~142), `0 <= hint_degree < 2` 면 `return 0` 으로 직렬이 된다(146~148); 클라이언트 쪽 같은 우회가 plan_generation.c:3213~3221. ✅ 직렬 재측정은 `PARALLEL(1)` / `NO_PARALLEL_SCAN`·`NO_PARALLEL_SUBQUERY`·`NO_PARALLEL_HASH_JOIN` 힌트로 한다(`qref` 레인이 이 방식). develop `2d925cb86` 재확인 2026-10-28: `call_once` px_parallel.cpp:60-81, 플래그 system_parameter.c:5143-5146. — 정소희(.50) 2026-10-28

#### 카디널리티·조인 선택도 — 측정으로 본 사실

- **카디널리티 오차와 비용가중치 오차는 서로 다른 질의에서 난다 — 순위상관 ρ = −0.024** (.52, `07480dfd1`, 2026-09-18): JOB 113질의 중 두 값이 다 있는 110개에서 스텝 최대 CARD오차와 스텝 최대 k오차(= `(Δcost/Δtime) × CARD오차` 를 같은 조인방법 중앙값으로 나눈 것)를 log 값 Spearman 으로 대조 — **ρ = −0.024**, 각자의 중앙값(CARD ×116 / k ×7.4)으로 가른 사분면도 25/30/30/25 로 독립 기대치 27.5 와 사실상 같다. CARD 최상위 무리(`2b`·`17b`·`17a`·`32b`·`17e`, 전부 ×1,231 — 같은 조인 `mk.keyword_id=k.id` 하나 때문)의 k 는 ×2.0~4.7 이고, k 최상위(`5c` ×1,131 / `11b` ×399 / `8b` ×163)의 CARD 는 ×56 / ×310 / ×446 이다. 두 축 모두 1위인 질의는 `10c` 하나(조인 `chn.id=ci.person_role_id` ÷46,393, k ×5,086 — §3 NULL 상관 항목). ✅ **두 결함은 따로 고쳐야 한다** — 카디널리티 추정을 고쳐도 가중치 오차는 남고, 그 반대도 같다. 재현: .52 `job-plan-viewer` 왼쪽 순위도 3개. — 정소희(.50) 2026-10-28
- **MCV 는 정답을 들고 있다 — 값만 알면 정확하다 (`17a` ×1.012)** (.52, `07480dfd1`, 2026-09-18): `17a` 의 `k.keyword='character-name-in-title'` → `k.id=117`(실측). `movie_keyword` 에서 `keyword_id=117` 인 행 = 41,840(COUNT). `movie_keyword.keyword_id` 의 MCV[117] freq 0.00936 × 4,523,930 = 42,344 → **×1.012**. 평균 팬아웃 `4,523,930/134,170 = 33.7` 로는 ×1,241 틀린다(측정된 CARD오차 ×1,231 과 같은 크기). MCV 300개(값의 0.2%)가 전체 행의 30.8% 를 덮고 그 안에서 fanout 이 2,129배 퍼져 있다(중앙 3,167 / p90 7,103 / 최대 71,795). ✅ 정보는 통계에 있고 계산식이 그 자리에서 못 쓴다(histogram_get_join_selectivity 절 "한쪽이 PK" 항목). — 정소희(.50) 2026-10-28
- **저장 히스토그램은 equi-depth 이고, 등간격으로 펴서 실제와 대조하면 정확하다** (.52, `07480dfd1`, 2026-09-18): histogram_bucketizer.hpp 머리 주석 "build equi-depth histogram buckets from a sample", 버킷 상한 `cap = ceil(non_mcv_rows / max_buckets)`. 저장본을 등간격 100칸으로 펴서(MCV=점질량, 버킷=구간 내 균등) 같은 구간의 `GROUP BY` 실측과 대조하면 **55개 수치형 컬럼 전수**에서 칸 배율 중앙값이 대부분 ×1.0x 다(`movie_keyword.keyword_id` 중앙 ×1.04 p90 ×1.13, `cast_info.person_role_id` 중앙 ×1.04 p90 ×1.08). ✅ **카디널리티 오차의 원인은 통계 품질이 아니다** — 재료는 정확하고 조인 계산식이 그 값을 쓸 수 없는 구조다. 도구: .52 `scripts/ak_hist.py`, 뷰어 `dist.html`. — 정소희(.50) 2026-10-28
- **덤프의 `card` 는 정수로 반올림된다 — 1 근처 스텝에서 오차가 부풀려 보인다** (.52, `07480dfd1`): `16a` 의 `t` 스텝 — 진짜 추정은 `34 × 2,528,312 × 3.955e-07 × 2.703e-02 = 0.919` 인데 덤프는 `card 1`. 술어별 오차의 곱은 ÷7.75 인데 스텝 CARD오차는 ÷8.43 으로 찍힌다(`7.75 × 1/0.919 = 8.43`). ✅ 술어별 오차의 곱과 스텝 오차가 8~9% 어긋나면 이 반올림을 의심한다. — 정소희(.50) 2026-10-28
- **카디널리티 추정은 조인 방법과 무관하다** (.52, `07480dfd1`, 2026-09-18): `natural`/`nohash`/`allhash` 세 레인의 조인 노드 `card` 열이 완전히 동일하다(`8c`·`8d`·`13a` 확인; `19c` 만 말단 3개가 1→2, 4→6 미세차). ✅ 그래서 q-error 를 한 레인(전 스텝 NL)에서 재서 모든 레인에 공통으로 쓸 수 있다. — 정소희(.50) 2026-10-28

#### trace 카운터로 조인 스텝 분해 — readkeys / filteredkeys (storage/btree.c)

- **`readkeys`/`filteredkeys` 는 키필터 통계가 아니라 프로브 적중 통계다** (.52, `07480dfd1`, 2026-09-18): btree.c:28077 이 키를 읽자마자 `read_keys++` 하고, 범위 밖이면 `end_scan` 이라 `qualified_keys` 에는 안 들어간다(:28099). 실측 — 864 리프 중 816 에서 `readkeys` 가 직전 스텝의 출력 행수와 정확히 일치(qref 레인). 즉 `readkeys` = **프로브 횟수**(아우터 행 수), `filteredkeys` = **결과를 하나라도 낸 프로브 수**, 차이 = **빈손 프로브**(아우터 값이 inner 에 없음)다. `17b` `ci` 는 키필터가 될 술어가 하나도 없는데 41,840→40,832 차이가 난다(1,008개 영화에 배우 기록 없음). ⚠ **이 차이를 키필터로 읽으면 조인 선택도에서 잘못 나눠 빼게 된다** — 미매칭은 "조인이 안 된다" 는 뜻이라 조인 선택도에 **포함돼야 할** 성분이다(처음엔 "옵티마이저가 키필터 감소를 반영 안 한다(173 리프)" 로 오독했다가 정정했다). — 정소희(.50) 2026-10-28
- **NULL 조인 키는 프로브 자체를 건너뛴다 — `readkeys` 를 "아우터 행 수" 로 읽으면 안 된다** (.52, `07480dfd1`, 2026-09-18): 이너 스캔의 `readkeys` 는 프로브 횟수인데, 조인 키가 NULL 인 아우터 행은 어차피 매칭이 없으므로 엔진이 프로브를 아예 안 한다 — `readkeys` = "조인 키가 NULL 이 아닌 아우터 행 수". `10c` 는 구동 스캔이 1,435,439 행을 냈는데 다음 스캔 `readkeys` 가 **15** 다. ⚠ 위 "816/864 일치" 는 **NULL 이 없는 조인 키에 한해** 성립한다 — 어긋나는 축이 두 개다: **빈손 프로브**(값이 inner 에 없음, `filteredkeys` 와의 차이)와 **건너뛴 프로브**(아우터 키가 NULL, `readkeys` 자체가 줄어듦). 뒤엣것은 `readkeys` 로는 안 보이고 **아우터 스캔의 실제 행수와 비교해야** 드러난다. — 정소희(.50) 2026-10-28
- **조인 스텝의 카디널리티는 네 항의 곱으로 정확히 분해된다 — 848/848 실측 일치** (.52, `07480dfd1`, 2026-09-18): `출력행 = 프로브수(readkeys) × 적중률(filteredkeys/readkeys) × 적중당팬아웃(btree rows/filteredkeys) × 데이터필터통과율(lookup rows/btree rows)`. 848개 리프 전부 오차 1% 이내. ✅ 스텝 오차를 볼 때 **어느 항이 틀렸는지** 이 분해로 가른다. — 정소희(.50) 2026-10-28
- **프로브 적중률은 인덱스 종류로 갈린다 — PK 룩업은 478/478 이 100%** (.52, `07480dfd1`, 2026-09-18): `pk_*` 룩업 478개 전부 100%(참조 무결성이 부모 존재를 보장). FK 인덱스 룩업 373개는 100% 211 / 90%+ 53 / 50~90% 75 / 50% 미만 34. 최저 `15d` `movie_id_aka_title` 4.1%(10,679 찾아 439), `16a` `movie_id_movie_companies` 22.6%. "자식→부모" 는 항상 맞고 "부모→자식" 은 데이터 나름이다. — 정소희(.50) 2026-10-28
- **스텝 CARD오차를 볼 때 구동(맨 앞) 스캔을 빼면 그 오차가 k 로 새어 든다** (.52, `07480dfd1`, 2026-09-18): 스텝오차는 "실제 배율 ÷ 추정 배율" 인데 구동 리프는 앞 스텝이 없어 배율을 못 만든다고 보고 `null` 로 뒀었다. 구동 리프는 물려받은 오차도 없으므로 배율이 곧 `실제/추정` 이다. JOB 113질의 중 구동 스캔에서 ×2 이상 틀리는 질의가 16개, 최대 `9a`·`19a` 의 est 96 → act 6,768(×70.5). ✅ 분해 지표를 만들 때 **첫 스텝을 빼면 그 스텝의 오차가 사라지는 게 아니라 다음 지표로 옮겨간다**. (같은 날 구동 스캔의 실제 행수를 다음 스캔의 `readkeys` 로 읽던 지표도 고쳤다 — NULL 키 프로브 건너뛰기 때문에 `10c` 가 "구동 스캔 ÷95,363" 으로 잘못 보였고, 고친 뒤 구동 ×1.003 / 조인 ÷46,393 으로 제자리를 찾았다.) — 정소희(.50) 2026-10-28

## 3. 예비 이슈 사항

> 미수정 버그·의심·문서 정정 후보·구조적 한계. 해소되면 삭제가 아니라 "해소됨(커밋/PR)"로 갱신.

- **[문서 결함]** `src/optimizer/AGENTS.md` Where-to-Look 의 "Fix cost estimation = plan_generation.c"는 오안내 — 실제는 query_planner.c 의 `qo_*_cost` 계열. develop 95b79e7ed 에 여전히 존재(재확인). 정정 PR 은 사용자 판단 대기.
- 조인 카디널리티 `MAX(1.0)` 바닥 — 분수 카디널리티 소거로 조인 순서가 코스트 노이즈에 좌우. develop planner_visit_node :8124/:8134/:8158/:8160 에 존재(재확인). **보강 — 여러 조인 술어의 선택도 곱이 바닥에 눌린다** (.52, `07480dfd1`, 2026-09-18): 07480dfd1 의 루프(query_planner.c:8390-8413)는 `sarged_terms` 전체를 돌며 `selectivity *= QO_TERM_SELECTIVITY (term)` 로 곱해 조인 술어를 빠뜨리지는 않지만, 곱할 때마다 `selectivity = MAX (1.0 / MAX (cardinality, 1.0), selectivity)`(:8413), 이어 `cardinality = MAX (1.0, cardinality)`(:8422)로 바닥을 누른다 — 술어가 여럿이면 1e-13 급으로 내려갈 곱이 바닥에 눌려 곱한 효과가 사라진다. 같은 뿌리. **미수정**(develop `2d925cb86` 재확인 2026-10-28 — planner_visit_node 의 선택도 바닥 :9725-9726·:9739, 카디널리티 바닥 :9472·:9615·:9803·:9811, `total_rows` :9813). — 정소희(.50) 2026-10-28
- 조인 선택도 NDV clamp 부재 — 조인 선택도 과대(20a 회귀). develop histogram_get_join_selectivity 에 clamp 없음(재확인).
- 구조적 미구현 4종: IN 원소별 MCV 프로브 미구현(develop cap 0.5 유지 재확인) / correlation 미수집(ISCAN_OID_ACCESS_OVERHEAD 5 로 땜질, develop :82-84 TODO 재확인) / 히스토그램 min·max 미저장(첫 버킷 하한 근사, develop :923 주석 재확인) / LIKE prefix→범위 변환 없음(선택도 측, develop 재확인).
- descent_cpu 비대칭 — **해소됨(PR#7622 `54b1b44d6`, inner 전용 과금)**. 잔여 두 축은 위 §2 캘리브레이션 절: `HJ_MEM_ALLOC_CONSTANT` 800 은 두 벤치 사이의 타협값(별건: 필터된 차원 테이블을 거친 조인 카디널리티), `qo_plan_cmp` 1.2배 밴드 안 "term 많은 인덱스 우선" 규칙(cbrd_25382_1, 별건 후보).
- (구 서술) descent_cpu 비대칭(iscan 전용 고정 CPU 항) — PR#7622 27건 회귀 근본 원인. develop 미머지(develop 에 descent_cpu 없음). **.50 수정 시도는 사용자 지시로 종결(2026-08-26, 미적용)** — 수정안(`iscan_descent_cpu` 필드 분리, nljoin inner 전용 과금)은 .50 `~/dev/cbrd27094-descent-fix.patch` 로 보존. 산식 검증 완료(구동측 0.2575→0, inner 과금 불변), 19a 플랜 유지 확인. JOB 순효과는 세션 오프셋(+5.76% 균일 시프트)으로 미확정 — 재개 시 동일 세션 A/B 필수.
- `qo_mackert_lohman_pages` T>b 분기 캡 부재 — 단일 스캔 fetch 추정이 힙 전체의 17.4배까지 발산. ~~develop 미머지(PR#7622 계열 브랜치 한정)~~ → `bacd5d0d2`(CBRD-27094)로 develop 에 들어와 `qo_iscan_cost` 단일 스캔 object_IO(:2608)와 NL 포화(:4476-4479)에 쓰인다. **미수정**(develop `2d925cb86` 재확인 2026-10-28 — T>b 분기 :4309-4320 에 캡 없음). — 정소희(.50) 2026-10-28
- `QO_GET_HIST_STATS` 매크로가 여전히 캐시 원본 포인터를 반환(query_graph.h:203-204) — dangling 자체는 주석 사이트 복사(937d09feb)로 해소됐으나, 매크로 신규 사용처는 같은 결함을 재생산할 수 있음(부분 해소).
- 파스 트리 histogram dangling 결함 — **해소됨(develop 937d09feb, CBRD-27279 #7761)**.
- OR 제약 추출 부재(q19) — **해소됨(develop c283e799d, CBRD-27171 #7613)**. 단, 추출 term 의 단일 term 유지(27-conjunct 재전개) 여부는 머지본에서 미확인.
  잔여 개선 후보(.50 프로젝트 md 이관, 2026-08-26): ① 추출 절의 **선택도 이중계상 보정**(추출 OR 를 중복 제약으로 더할 때 선택도를 나눠 보정) 미구현 ② 단일 term 형태 유지 시 추가 ~1.3x 여지(IMP-027 실측 0.293 vs 0.383) ③ CTP sql/medium 회귀 확인 미수행. 동일 발견이 주영진 IMP-027 캠페인에 있음(필터플랜 코스트 29,357까지 일치) — 중복 구현 방지 조율은 사용자 몫.
- **`ISCAN_IO_HIT_RATIO` 는 죽은 상수다** (.50, 4f0f90b62, 2026-09-21): CBRD-27094(`bacd5d0d2`)가 `qo_nljoin_cost` 의 평탄 캐시 할인을 Mackert-Lohman 포화로 바꾼 뒤 살아 있는 참조가 없다 — 4f0f90b62 query_planner.c:131 정의, :3845 주석, :3931-3932 `#if 0` 블록뿐. 파라미터로 노출하면 효과 없는 손잡이가 된다. **미수정**(정리 별건; develop `2d925cb86` 재확인 2026-10-28 — 정의 :153, 주석 :4446, `#if 0` 블록 :4537-4539). — 정소희(.50) 2026-10-28
- **`col LIKE ?` 의 파생 range 항 선택도가 기본값에 머문다 — 희귀 접두어의 인덱스 스캔 비용이 비관적** (.52, c0e06bef9, 2026-09-22): 경계가 `like_match_lower_bound(?)` 식이라 히스토그램 범위 추정을 못 받는다(§2 「qo_rewrite_like_terms」). **미수정**(후속 후보; develop `2d925cb86` 재확인 2026-10-28 — `histogram_split_hv_range ()` histogram_cl.cpp:2902 는 직접 PT_HOST_VAR 경계만 보고, `qo_between_range_arg_value ()` query_planner.c:12828 은 함수 경계에 NULL 을 줘 기본값으로 떨어진다). — 정소희(.50) 2026-10-28
- **`ignore_trailing_space=yes` 에서 문자열 범위 추정(`string_domain_frac_lt`, 바이트 순서)은 파라미터를 무시한다** (.50, PR#7977 적용 빌드, 2026-09-17): `t_vc.c < 'abcd '` 추정 200행 vs 참값 0. 히든 파라미터·기본 no 라 영향은 작다. **미수정**(별건 후보; develop `2d925cb86` 재확인 2026-10-28 — histogram_cl.cpp:1011 은 바이트 위치(`string_pos`)만 보고 파라미터를 읽지 않는다). — 정소희(.50) 2026-10-28
- **CHAR↔VARCHAR 조인의 `mcv_join_parts_str` 은 한쪽 스트립·한쪽 원본 MCV 를 비교하지만, 런타임은 패딩된 CHAR 와 원본 VARCHAR 바이트를 비교한다 — 정합 여부 미검증** (.50, 2026-09-17). **미수정**(별건 후보; develop `2d925cb86` 재확인 2026-10-28 — histogram_cl.cpp:1614 는 저장 MCV 끼리 `string_values_equal_under_collation` 으로 비교하고 재패딩하지 않는다). — 정소희(.50) 2026-10-28

**JOB 실측 예비 이슈** — 측정 계약 `AK-par4`(JOB 113질의, `parallelism=4`·`data_buffer_size=16G`·`taskset -c 0-15`, 21테이블 `WITH FULLSCAN, 300 BUCKETS` 후 재기동, warmup 1패스, 기준 develop `07480dfd1` release; 카디널리티는 `qref` 레인) — §2 「JOB 실측」 절 첫 줄과 같다.
- **같은 질의 안에서 비용 순서가 실제 시간 순서와 역전된다 — 34개 중 어긋남 32 / 일치 0 / 동률 2** (.52, `07480dfd1`, 2026-09-18): 수치는 §2 모듈 일반 「비용 추정값이 실제 실행시간과 비단조」 보강. 탐색 실패가 아니라 비용 함수가 틀린 것이다. **미수정**(재확인 못 함 — 측정 기반, develop `2d925cb86` 에서 재측정 안 함). — 정소희(.50) 2026-10-28
- **비용식의 행수 의존 지수가 실측과 어긋나고, idx-join 과 hash-join 이 반대 방향이다** (.52, `07480dfd1`, 2026-09-18): 술어 없는 FK→PK 전수 조인에 PK 범위만 얹어 행수를 바꿔 가며 `cost ~ 행수^a`, `time ~ 행수^b` 를 log-log 회귀(R² 0.95~1.00). `mk⋈keyword`: idx a=0.841 vs b=0.997(Δ−0.16), hash a=0.968 vs b=0.788(Δ+0.18); `mc⋈company_name`: idx a=0.820 vs b=1.137(Δ−0.32), hash a=0.917 vs b=0.774(Δ+0.14). 즉 **행수가 커질수록 idx 는 비용을 덜 매기고 hash 는 더 매겨** 격차가 벌어진다 — 상수배 보정으로는 고칠 수 없다. 재현 .52 `~/dev/tests/joinorder/scripts/ak_probe_curve.py`. **미수정**(근거 미확정 — 아래 ⚠; 재확인 못 함). — 정소희(.50) 2026-10-28
- **해시조인 가격이 조인 크기에 따라 부호가 뒤집힌다** (.52, `07480dfd1`, 2026-09-18): 카디널리티 오차를 0 으로 만든 프로브(q-error 1.000~1.001)에서 같은 순서·같은 카디널리티로 방법만 바꿔 비용비와 시간비를 대조. 큰 many-to-one 조인은 해시를 **과대계상**(`mk⋈keyword` 비용비 1.90 ↔ 시간비 0.37 = 5.1배, `mc⋈company` 2.01 ↔ 0.44 = 4.6배, `an⋈name` 7.24 ↔ 1.05 = 6.9배), 작은 조인은 **과소계상**(`mi_idx⋈info_type` 0.37 ↔ 1.50 = 0.25배, `title⋈kind_type` 0.42 ↔ 1.35 = 0.31배). 위 행수 의존 항 결함의 귀결. 재현 `scripts/ak_probe_k.py`. **미수정**(근거 미확정 — 아래 ⚠; 재확인 못 함). — 정소희(.50) 2026-10-28
  - ⚠ **위 두 건은 측정 계약 결함으로 근거가 약하다** (.52, `07480dfd1`, 2026-09-18): 비용은 병렬을 모르는 값인데(§2 「병렬과 비용」) 두 프로브(`ak_probe_curve.py`·`ak_probe_k.py`)는 **par4 에서 잰 시간**을 대조했다. 병렬이 잘 먹는 쪽(해시)이 체계적으로 유리해 보이는 방향이라 `hash b=0.78`(선형보다 느림)의 얼마가 build 분할상환이고 얼마가 병렬 기여인지 **분리되지 않았다**. 직렬 재측정 전까지 근거 미확정으로 다루고, 재측정은 파라미터가 아니라 **힌트로** 한다(§2 측정 함정). — 정소희(.50) 2026-10-28
- **병렬 차수 계산식이 서버·클라이언트 두 곳에 복제돼 있다 — drift 위험** (.52, `07480dfd1`, 2026-09-18): 서버 px_parallel.cpp:150·154 의 `x = num_pages / page_threshold; auto_degree = (63 - __builtin_clzll(x)) + start_degree;` 와 클라이언트 옵티마이저 plan_generation.c:3269~3271 의 `degree = (x <= 1) ? 2 : ((63 - __builtin_clzll (x)) + 2);` 가 **같은 식을 따로 구현**한다 — 후자는 전자를 호출하지 않고 주석(3270)으로 "matching compute_parallel_degree's start_degree=2 formula" 라고만 밝힌다. 한쪽을 고치면 다른 쪽이 조용히 어긋난다(계단은 **2배마다 +1**). **미수정**(develop `2d925cb86` 재확인 2026-10-28 — px_parallel.cpp:189(·:201), plan_generation.c:3441-3442). — 정소희(.50) 2026-10-28
- **필터가 조인 키의 NULL 여부와 상관돼 있으면 조인 카디널리티가 4~5자릿수 틀린다 — `10c` ÷46,393** (.52, `07480dfd1`, 2026-09-18): `10c` 의 구동 스캔 `cast_info` + `note like '%(producer)%'` 는 추정 1,430,440 vs 실제 1,435,439(×1.003)로 거의 정확하다. 틀리는 건 바로 다음 조인 `chn.id = ci.person_role_id` — 추정 693,474 vs 실제 15(÷46,393). 추정 통과율 `693,474/1,430,440 = 0.484798` 은 `cast_info.person_role_id` 의 **테이블 전체 non-NULL 비율** `17,571,519/36,244,344 = 0.484807` 과 소수 넷째 자리까지 같다 — 옵티마이저는 NULL 비율을 정확히 알고 반영한다(`term sel = 1.54378e-07 = 0.484807 / ncard(char_name) 3,140,339`). 실패는 **상관**이다: 필터를 통과한 1,435,439 행 중 `person_role_id` 가 NULL 이 아닌 건 15개(0.001%, 프로듀서는 배역이 없다). 선택도는 필터와 조인 키의 NULL 여부를 **독립으로 곱한다**. 아래 값↔팬아웃 상관과 같은 뿌리이되 축이 다르다 — 이쪽은 NULL 비율의 조건부 분포다. 실측: `SELECT COUNT(*) FROM cast_info WHERE note LIKE '%(producer)%'` → 1,435,439, `AND person_role_id IS NOT NULL` → 15. **미수정**(구조적; develop `2d925cb86` 재확인 2026-10-28 — `qo_expr_selectivity` 의 `(1 − nf)` 후처리 :12000-12039 는 다른 술어와 무관하게 곱하고, 조건부 NULL 비율 모델은 없다). — 정소희(.50) 2026-10-28
- **조인 선택도 `1/NDV` 균등 가정 — 값↔팬아웃 상관 미모델링이 카디널리티 오차의 주범이다** (.52, `07480dfd1`, 2026-09-18): §2 「trace 카운터로 조인 스텝 분해」의 네 항 분해로 848 리프를 전수 집계하면 적중률 중앙값 100%, 적중당 팬아웃 중앙값 1.00 이고, 오차 상위 리프는 **전부 적중률 100%** — 틀린 것은 미매칭이 아니라 `ncard × sel` 자체다. 예: `12b`·`1b`·`1d` 의 `mi_idx` 는 est 배율 12,213 vs 실제 10(÷1,221) — `sel = 8.85e-03 = 1/113`(`info_type` 행수의 역수)에 `ncard(movie_info_idx) = 1,380,035` 를 곱한 값인데 그 `info_type` 하나에 달린 행은 실제로 10개뿐이다(113종에 138만 행이 고르게 퍼져 있다는 가정의 실패); `5c` `mc` 는 est 44,351 vs 실제 798(÷55.6). 값 쪽 근거: `17a` 의 첫 조인 `mk.keyword_id=k.id` 는 추정 card 34 vs 실제 41,840(×1,231) — 34 는 `movie_keyword` 의 키워드당 평균 팬아웃(4,523,930/134,170 = 33.7)이고, 필터가 남긴 `'character-name-in-title'` 은 팬아웃 상위 3위다(팬아웃 min 1 / max 72,496). 필터 추정 자체는 정확했고(card 1 vs 실제 1행) 오차는 전부 조인 스텝에서 난다 — 스텝별로 나누면 `17a`·`16b` 는 첫 조인 하나만 ×1,230 이고 나머지 스텝은 전부 2배 안쪽이다(누적으로 보면 6개 조인이 다 ×1000 처럼 보이지만 물려받은 오차). §2 모듈 일반 「값↔조인 팬아웃 상관 미모델링」의 정량 근거. **미수정**(구조적; develop `2d925cb86` 재확인 2026-10-28 — `histogram_get_join_selectivity` 의 잔여 분배식 histogram_cl.cpp:1788·:1798 그대로, 값 조건부 조인 통계 없음). — 정소희(.50) 2026-10-28
- **옵티마이저가 스스로 고른 해시조인이 손해인 사례가 있다** (.52, `07480dfd1`, 2026-09-18): `5c` 는 4스텝 중 3개를 hash-join 으로 고르는데 전 스텝 `NO_USE_HASH` 로 막으면 3.250s → 0.562s(5.8배); 최종 답지는 1개만 해시로 써서 0.227s. `31c` 3.364→2.767(1.2배), `25c` 9.078→7.589(1.2배)도 같은 방향. CBRD-26475 로 해시 게이트가 열린 뒤 비용모델 미보정으로 보인다. **미수정**(재확인 못 함 — 측정 기반). — 정소희(.50) 2026-10-28

## 4. 진행중인 작업

> 각 컨테이너가 자기 소절을 직접 관리한다. 완료되면 지우지 말고 "완료(PR/커밋)"로 갱신.

### .50
- CBRD-27140: `qo_index_cardinality` 계열·`QO_ATTR_CUM_STATS` INT64 승격 (PR#7856, 2026-09-02 리뷰 대기).
- descent_cpu 회귀(PR#7622 근본 원인) 코드 수정 진행 중 — (a) inner-only 우선, 이후 (c) 페이지 비례 검토. 완료 시 .51의 재블레스 8건 진행 가능.
- PR#7613 (qo_extract_or_restrictions OR 제약 추출) — **완료(머지 c283e799d, CBRD-27171)**. 선택도 이중계상은 머지본이 PT_EXPR_INFO_OR_DERIVED 마크로 처리; 단일 term 유지(27-conjunct) 여부는 머지본에서 재확인 필요.
- CBRD-27094 히스토그램 조인 선택도 계열 브랜치 작업 — MCV 조인 선택도 도입(10d0aa0e7, CBRD-26746 #7508)과 histogram dangling 수정(937d09feb, CBRD-27279 #7761)은 develop 에 이미 머지됨; M-L/descent_cpu 계열(PR#7622)은 미머지.
- AGENTS.md "비용 추정=plan_generation.c" 오안내 정정 PR — 사용자 판단 대기.

### .51
- PR#7561 (CBRD-27126, feature/optimizer-constant-parameterize): 비용 상수 5종 시스템 파라미터화 + 나머지 고정 IO 항 파라미터 합성 + `cubrid calibratedb`(SA 전용 자동 측정 유틸) — 구현 완료, 푸시됨, 사용자 검토 대기.
- PR#7622 (CBRD-27094): head `f7a774e46`, descent 수정은 단일 커밋으로 스쿼시(`54b1b44d6`).
  캡 철회·inner 전용 확정(위 §2). JOB 전수 측정 게시(develop 04620b2ce 대비 235.3→207.5s, −11.8%).
  **남은 것은 CI 재실행과 TC 게이트**(cubrid-testcases#3206 sql 3건 / private-ex#3832 shell 5건, 둘 다
  draft). 2026-09-01 사용자 지시로 이 PR 은 별도 세션이 이어받는다 — 인수인계는 보드 #25 코멘트.
- PR#7622 CI 27건 분류 완료(재블레스 8 / 보류 19). `cbrd_25060_2`(hash-join → idx-join, 서버시간
  8.8배)는 descent 가 아니라 **M-L 포화** 축이라 이번 커밋 범위 밖이다 — CI 에 남으면 별도 커밋/이슈 판단.
- **2026-09-02~03 갱신(세션 359b58da)**: head `b19f16c39`(develop 재머지) = 커버링 유령 페이지 제거 + HJ 오프셋 800.
  CI 플랜 변경 TC 는 release 실행시간으로 판정(규칙 §2-1, 하네스 claude-workspace/tools/plan-ab). sql 12건 답안·4563_3 ORDERED 힌트
  → `tc/pr-7622` 푸시, **test_sql SUCCESS**(09-03 17:03 런). JOB 전수 develop 5f3a30d09 대비 246.1→221.4 s(−10.1%, 22/9/82).
  **남은 것: test_shell·gha-ci shell 실패 답안(25080·jdbc_dbcp·13852 등) + TC PR ready 전환 → 머지.** 상세는 claude-workspace
  `projects/CBRD-27094/플랜검증-실행시간.md`.

### .52
- PR#7622(CBRD-27094, 비용 모델 — 반복 프로브 ML 보정·하강 CPU·비상관 힙 페치·리프 포화):
  리뷰 완결(unresolved 0)·APPROVED·develop 머지(faf5a3b2a). 남은 것 = TC PR(tc/pr-7622) 정리 →
  Merge Gate 해제 → 머지. [기준: CBRD-27094 브랜치, 2026-08-26]
- CBRD-27283(correlation/클러스터링 통계 — clustered↔uncorrelated 비용 보간): 착수 가능 상태.
  검증 대상 = PR#7622 잔여 회귀 4건(9c/5c/13c/7a). 설계 참고 = 이 모듈 §2·§3의 .50 축적분. [보드 #75]