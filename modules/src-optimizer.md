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
| `histogram_get_equal_selectivity` | histogram/histogram_cl.cpp:1032 | attr=const 선택도(MCV+버킷, eqsel 상당) | qo_equal_selectivity(:10634/:10683), histogram_cl.cpp:2653/:2762 |
| `histogram_get_join_selectivity` | histogram/histogram_cl.cpp:1528 | attr=attr 등가조인 선택도(PG eqjoinsel_inner 이식) | qo_equal_selectivity(:10602) |
| `histogram_get_like_selectivity` | histogram/histogram_cl.cpp:1824 | LIKE 선택도(MCV+버킷 경계+휴리스틱) | qo_like_selectivity(:10406) |
| `comp_parts` | histogram/histogram_cl.cpp:908 | 범위 비교의 버킷 보간 템플릿(scalarineqsel 상당) | :1299-1311 에서 int64/double/string_view/uint64 인스턴스화 |
| `HistogramReader::reset` | histogram/histogram_reader.cpp:72 | HST2 blob 파싱·유효성 가드 | histogram_init_reader_from_lhs(histogram_cl.cpp:623), :2977 |
| `qo_extract_or_restrictions` | rewriter/query_rewrite_term.c:4795 | 멀티 spec OR 에서 단일 spec 제약 추출(CBRD-27171 #7613) | rewriter/query_rewrite.c:480 |

`qo_mackert_lohman_pages` 는 develop 에 없다(CBRD-27094/PR#7622 계열) — §2 해당 절 참조.

## 2. 분석 내용 (함수별)

> 항목은 함수 단위로 기술한다 — 각 항목의 제목/선두가 함수·파일명이다. 새 분석도 함수명을 앞세워 추가할 것.
> 행 번호는 develop 95b79e7ed 에서 재확인한 것을 우선 표기했고, develop 에 없는 심볼/코드는
> "(develop 에 없음 — CBRD-27094/PR#7622 계열)" 로 표시했다. 그 계열의 행 번호는 워크트리
> `/home/cubrid/dev/cubrid` 브랜치 `CBRD-27094` @ `faf5a3b2a` 기준이다.

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

**비용 추정값이 실제 실행시간과 비단조 — 절대 비용 모델이 깨져 있다** — 추정 비용과 실측 시간이 크게 어긋나고 순서(단조성)조차 보존되지 않는다: 17a est ~2494 / 실측 ~41s, 29a est ~1877 / ~68s, 8c est 8.24M / 47s. 즉 비용값은 플랜 간 상대 비교에도 신뢰하기 어렵다.
- ✅ **리뷰 체크포인트**: 'CUBRID 비용이 더 낮으니 이 플랜이 맞다'는 논거는 단독으로 채택하지 말고, 비용 모델 변경의 성패는 절대 비용값이 아니라 PG 와의 조인 순서 일치로 판단할 것.

**per-term 선택도가 PG 와 일치해도 격차가 남는다 → 병목은 카디널리티 전파/비용 모델** — eqjoinsel 도입 후 항목별 조인 선택도가 PG 와 수치까지 일치함을 확인했는데도(`n.id=ci.person_id` 2.40e-7 등) 전체 성능 격차는 PG 대비 2.72x 로 불변이었다(2026-07-03 A/B: 순서 매칭 28→30/113, 686.0→701.5s(+2.3%), 기하평균비 1.001). 즉 남은 격차의 원인은 개별 term 의 선택도가 아니라 조인 트리를 따라 올라가는 카디널리티 전파와 비용 모델 쪽이고, 실제로 17e 는 조인 순서가 PG 와 MATCH 로 바뀌었는데도 8.6초 느려졌다 — 순서 일치가 곧 성능 개선은 아니다.
- ✅ **리뷰 체크포인트**: 선택도 함수 하나를 고치는 PR 이 '카디널리티가 맞아졌으니 빨라질 것'이라 주장하면 의심하고, 개별 sel 정확도와 최종 플랜 품질을 분리해 검증할 것.

**값↔조인 팬아웃 상관 미모델링으로 인한 '정확도 역설'** — 히스토그램 필터 선택도는 uniform 기본값보다 훨씬 정확하다: `k.keyword IN(흔한 키워드 7개)` 5.22e-5 vs uniform 0.00698(134x), `cn.name~'Lionsgate'` 5.21e-5 vs 0.01(192x), `mc.note LIKE '%(Blu-ray)%'` 0.0032 vs 0.1(31x). 그런데 더 느린 순서를 고른다 — 필터가 살려낸 7개 키워드가 mk 에서 팬아웃이 매우 큰 값들인데, 조인 선택도는 값과 무관한 평균 1/NDV 라서 '어떤 값이 살아남았는지'로 조건화되지 않아 k⋈mk 를 과소추정한다(31b 계열; 22a k⋈mk 추정 CUBRID 35 / PG 135 / 실제 37,091). uniform 은 k 필터를 과대추정해 우연히 함정을 피할 뿐이고, per-MCV-value 조인 통계는 CUBRID 에도 PG 에도 없으므로 이는 단순 버그가 아니라 근본적 옵티마이저 한계다.
- ✅ **리뷰 체크포인트**: 필터 선택도 정확도 개선이 오히려 느려지는 회귀는 조인 선택도의 값-조건화 부재를 먼저 의심하고, 필터 선택도 코드를 되돌려 '고치는' 변경에는 반대할 것.

**PG 와 공통인 오차는 패리티 목표에서 손대지 않는다 (sarg×조인 독립 가정, uniform eq-join)** — `mi.info='Horror'` 같은 sarg 가 사실상 `info_type_id=genres` 를 함의하는데도 it1 조인 선택도에서 1/113 이 또 곱해지는 구조적 과소추정이 남아 있지만, PG 도 동일한 독립 가정을 쓰므로 CUBRID 고유 결함이 아니다(19d 의 divergence 도 voice ⊂ actress 상관 때문이며 양 엔진 공통). 같은 맥락으로 4a 의 `it⋈mi_idx` eq-join 선택도는 CUBRID·PG 모두 uniform 1/max(NDV)(~1/113)로 나와 둘 다 실제 대비 ~1000x 과소추정하며, 4-계열 leaf 순서 차이는 주로 플랜 모양 차이(PG 가 1행짜리 `it` 를 상위 outer 로 감쌈)이고 구동 체인 k→mk→mi_idx 는 양쪽 동일하다. 17a 도 k⋈mk 스큐 과소추정(est 28 vs 실제 41,840)이 실행시간을 지배하지만 PG 도 같은 과소추정(est 34)이라 발산 요인이 아니다.
- ✅ **리뷰 체크포인트**: '추정이 실제보다 1000배 작다'만으로 CUBRID 버그로 단정하지 말고 PG 추정값과 나란히 비교해 발산 여부를 먼저 확인할 것 — 상관관계를 보정하는 커스텀 휴리스틱은 PG 기준 이탈이므로 거부 대상이고, leaf 순서 차이는 attachment-order 기준으로 재확인할 것.

### 비용 상수 (query_planner.c 상단)

**비용 상수는 query_planner.c 상단 한 곳에만 정의된다 (동기화 대상 헤더 없음)** — develop 기준 목록: `TEMP_SETUP_COST 5.0`(:80), `QO_CPU_WEIGHT 0.0025`(:81), `ISCAN_OID_ACCESS_OVERHEAD 5`(:84), `FETCH_HEAP_COST 0.25`(:89), `MJ_CPU_OVERHEAD_FACTOR 20`(:90), `HJ_BUILD_CPU_OVERHEAD_FACTOR 40`/`HJ_PROBE_CPU_OVERHEAD_FACTOR 20`(:91-92), `HJ_MEM_ALLOC_CONSTANT 1500`(:93), `HJ_FILE_IO_WEIGHT 0.5`/`HJ_PARTITION_FILL_FACTOR 0.8`/`HJ_HASH_ENTRY_POS_SIZE 12`(:94-103), `ISCAN_IO_HIT_RATIO 0.5`(:104), `SSCAN_DEFAULT_CARD 50`(:105), `GUESSED_BIND_LIMIT_CARD 2000`(:106), `RBO_CHECK_COST 50`/`RBO_CHECK_RATIO 1.2`/`RBO_CHECK_LIMIT_RATIO 10`(:108-110), `QO_COST_EQ`(상대오차 1e-6, :115). `BTREE_DESCENT_PAGE_OVERHEAD`·`QO_EFFECTIVE_CACHE_PAGES`·`SORT_MERGE_FAN_IN` 은 **develop 에 없음(CBRD-27094/PR#7622 계열)**. 과거에 "`query_planner_constants.h` 에도 같은 상수가 있어 양쪽을 동기화해야 한다"고 알려졌으나 이는 오류로 정정됐다 — 그런 헤더는 추적 파일로 존재하지 않고 미추적 백업 `query_planner_constants.h~` 가 grep 에 걸린 것이었다(`git ls-files` 로 확인). 상수 수정은 `query_planner.c` 한 곳으로 끝난다.
- ✅ **리뷰 체크포인트**: 비용 상수 변경 PR 에서 "헤더와 이중 정의 동기화"를 요구하지 말 것.

**correlation(클러스터링 팩터) 미수집 — ISCAN_OID_ACCESS_OVERHEAD 20→5 하향으로 땜질** — 컬럼-물리순서 상관계수를 수집하지도 사용하지도 않아 인덱스 스캔 비용에 클러스터링 팩터가 없다. 보정 수단으로 `ISCAN_OID_ACCESS_OVERHEAD` 를 20 에서 5 로 낮춰 뒀고 바로 위 주석에 TODO 가 달려 있다: "Lowered 20 -> 5 to favor index scan when low/stale leading-column NDV inflates sel via 1/pkeys[0]. TODO: per-index clustering factor."(develop query_planner.c:82-84). 즉 이 상수는 '정확한 값'이 아니라 누락된 correlation 을 흡수하는 보정치이고, correlation plumbing 실험 코드는 stash@{0}(B1)에 남아 있다.
- ✅ **리뷰 체크포인트**: 인덱스 스캔 비용 상수 조정 변경은 correlation 부재를 흡수 중인 5 의 의미를 이해하는지 확인하고, correlation 을 실제 도입하면 이 상수를 원복해 이중 보정을 피할 것.

**QO_EFFECTIVE_CACHE_PAGES 는 512MB 하드코딩 (develop 에 없음 — CBRD-27094/PR#7622 계열)** — `QO_EFFECTIVE_CACHE_PAGES = 32768.0`(=512MB, 브랜치 query_planner.c:112)은 하드코딩된 가정값이며 코드 주석이 한계를 자백한다: "matches the data_buffer_pages default … The real parameter is server-only, so the client-side optimizer cannot read it". 같은 값이 `qo_mackert_lohman_pages()` 안의 `b`(:3611-3613)로 다시 나타난다. 서버를 16GB 버퍼로 운영하면 이 가정값이 실제와 32배 어긋난 상태로 비용이 계산된다.
- ✅ **리뷰 체크포인트**: 버퍼 크기 `b` 에 의존하는 비용식 변경은 대용량 버퍼 실측으로 튜닝했다는 주장을 32배 괴리를 감안해 재검토할 것.

**기본 선택도 상수가 PG 와 불일치 (EQ 0.001 / COMP 0.1)** — 통계가 없을 때 쓰는 기본 상수는 `DEFAULT_EQUAL_SELECTIVITY 0.001`(query_planner.h:116), `DEFAULT_COMP_SELECTIVITY 0.1`(:118)인 반면 PG 는 각각 0.005, 0.3333 이다(develop 재확인; 그 외 :113-121 에 NULL 0.01/EXISTS 0.1/EQUIJOIN 0.001/BETWEEN 0.01/IN 0.01/RANGE 0.1). 통계 없는 컬럼에서 CUBRID 가 PG 보다 훨씬 선택적이라고 가정하므로, 히스토그램이 없거나 폴백된 경로에서 카디널리티가 체계적으로 과소평가된다.
- ✅ **리뷰 체크포인트**: 폴백 경로 질의의 카디널리티가 지나치게 작으면 이 상수 차이를 의심하고, 상수를 PG 쪽으로 맞추는 변경은 영향 범위가 넓으므로 단독 변경으로 A/B 할 것.

- ✅ **리뷰 체크포인트**: 비용식에 새 상수를 넣을 때 ①sscan/iscan 대칭인가 ②기존 프리미티브(cost_seq_page 등)로 합성 가능한가(신규 파라미터 남발 금지) ③NCARD=0 극한에서 발산하지 않는가.

### qo_analyze_term (query_graph.c:2013)

**PREDICATE_TERM 에서 term 별 히스토그램 사용 여부를 진단 플래그로 남긴다** — `env->sel_hist_used`/`env->sel_hist_fallback`(query_graph.h:977-978)을 term 별로 리셋·검사해 `QO_TERM_SEL_FROM_HISTOGRAM`(query_graph.h:756)을 세운다(develop query_graph.c:2815-2822). 어느 term 이 히스토그램을 실제로 탔는지 이 플래그로 구분할 수 있고, plan_generation.c:3213 에서도 소비된다.

**혼합 OR 조건은 join term 으로만 분류되어 단일 릴레이션 sarg 가 0개가 된다** — TPC-H q19 의 큰 OR 는 각 분기 안에 part 컬럼과 lineitem 컬럼이 섞여 있어 CUBRID 의 term 분류가 OR 전체를 join term 으로만 취급한다. 그 결과 part 에 sarg 가 0개가 되어 part 를 줄이는 인덱스 프로브 자체가 성립하지 않는다 — PG 는 `optimizer/util/orclauses.c` 의 `extract_restriction_or_clauses()` 로 각 분기에서 part 전용 조건만 뽑아 중복 제약으로 추가해 part 를 ~2천 행으로 줄인다. 각 분기의 part 조건 OR 를 WHERE 에 수동 중복 추가하면 결과값 동일(30104438.0911)하면서 5.6s → 0.618s 로 개선됨을 실증했고(cubrid-tpch/exp/q19_orext.sql, develop b572177a1), `l_partkey` 선두 인덱스는 CUBRID 에도 이미 있어 추출을 못 해서 못 쓰는 것이 핵심이었다. → 현재 develop 은 rewriter 의 `qo_extract_or_restrictions()` 로 이를 해소(해당 절 참조).
- ✅ **리뷰 체크포인트**: 인덱스가 있는데 안 쓰이는 사례는 term 분류 결과(sarg 개수)를 먼저 의심할 것.

### qo_expr_selectivity (query_planner.c:10126)

**PT_EXPR 가 아닌 노드가 들어올 수 있다** (상수 접힘 결과 등) — 가드 없으면 코어. 처리할 땐 `total_selectivity = 1.0` 같은 값 강제가 아니라 **`continue`(중립)** 가 맞다. AND 결합에서 미지항이 전체를 1.0으로 덮어쓰면 다른 항의 선택도가 소거된다. (2026-08 hotfix 에서 확정, 사용자 검증 완료)

**조인 선택도 호출부의 (1-null_frequency) 이중 곱 규약** — 호출부는 attr=attr 선택도 반환값에 `(1 - nf)` 를 양쪽 컬럼에 대해 두 번 곱한다(develop query_planner.c:10345-10354, `selectivity * (1 - nf1) * (1 - nf2) + nf1 * nf2` 형태 — null-safe `<=>` 는 NULL-NULL 질량 가산). 그래서 `histogram_get_join_selectivity()` 는 자기 계산값을 양쪽 null 팩터로 미리 나눠서 반환하도록 구현돼 있고 주석이 규약을 명시한다(develop histogram_cl.cpp:1643-1656: "the caller (qo_expr_selectivity) multiplies the returned selectivity by (1 - null_frequency) of BOTH name arguments … so divide both back out"). 이 규약을 모르고 순수 selectivity 를 그대로 반환하면 null 이 있는 컬럼에서 선택도가 (1-nf)² 배만큼 과소평가된다.
- ✅ **리뷰 체크포인트**: 조인 선택도 반환값 규약 변경 시 호출부의 (1-nf)×2 보정과 함수 내부 나눗셈이 짝을 이루는지 반드시 같이 확인할 것.

### qo_equal_selectivity (query_planner.c:10572)

attr=attr 은 `histogram_get_join_selectivity`(:10602) 우선, 실패 시 `qo_index_cardinality`(:10609-10610)의 `1/max(icard)`, 그것도 없으면 `DEFAULT_EQUIJOIN_SELECTIVITY`. attr=const/host_var 는 `histogram_get_equal_selectivity`(:10634/:10683) 우선. 히스토그램/MCV 부재 시 폴백이 기존 `1/max(icard)` 경로로 살아 있는지가 리뷰 관건이다.

### qo_between_selectivity / qo_range_selectivity (query_planner.c:11157 / :11231)

**BETWEEN 은 대부분 PT_RANGE 로 정규화되고, 남는 형태는 이제 히스토그램으로 추정한다** — 과거(CBRD-27094 @ faf5a3b2a 기준) `qo_between_selectivity()` 는 아무 계산 없이 `DEFAULT_BETWEEN_SELECTIVITY`(0.01)를 반환하고 `env->sel_hist_fallback` 만 세우는 사실상 죽은 경로였다(BETWEEN 이 재작성 단계에서 PT_RANGE 로 정규화되어 `qo_range_selectivity` 가 쓰이므로). develop 은 CBRD-27037(#7570, dde911f48) 머지로 달라졌다: 재작성되지 않고 도달하는 형태 — 특히 NOT BETWEEN — 를 `qo_between_range_histogram_selectivity()` 로 히스토그램 추정한다. 주석이 근거를 명시한다: "what reaches here is the form that was not rewritten -- notably NOT BETWEEN, whose complement is not a single range"(develop :11168-11173). col<col(컬럼 대 컬럼 비교)은 PG 도 기본값을 쓰므로 패리티 상태다.
- ✅ **리뷰 체크포인트**: PT_BETWEEN 경로를 '버그'로 지적하기 전에 PT_RANGE 정규화 이후에도 도달 가능한 형태인지 확인하고, 반대로 정규화를 바꾸는 변경은 이 경로의 도달 집합을 바꿀 수 있으니 주의할 것.

관련 develop 머지 이력: 양측 범위 히스토그램 추정의 1행 플로어(#7726, 7e65be797), 버킷의 `<` vs `<=` 구분(#7741, 44c199cee), 측정된 인덱스 스캔 선택도의 1행 플로어(CBRD-27192, 05522fac8).

### qo_all_some_in_selectivity (query_planner.c:11431)

**scalararraysel(IN 리스트) 미구현 — 원소별 MCV 프로브가 없다** — IN 리스트 선택도는 원소 개수 × 등호 선택도로만 계산하고(`list_card = pt_length_of_list(...)` develop :11486/:11490, 서브쿼리는 XASL cardinality :11497, 실패 시 legacy 1000), PG 의 `scalararraysel` 처럼 원소별로 MCV/히스토그램을 프로브하지 않는다. 따라서 선택적인 IN 리스트(희소값)에서 선택도가 크게 과대평가된다. develop 은 하드 상한 0.5 를 그대로 유지한다(`in_selectivity > 0.5 ? 0.5 : in_selectivity`, :11507-11508 "compute selectivity--cap at 0.5"); 상한을 `MIN(in_selectivity, 1.0)` 으로 바꾸고 "the former hard cap of 0.5 had no distributional basis" 주석을 단 것은 CBRD-27094 브랜치다(develop 에 없음 — CBRD-27094/PR#7622 계열).
- ✅ **리뷰 체크포인트**: IN 조건 질의의 플랜이 이상하면 `list_card * equal_selectivity` 근사를 먼저 확인하고, 개선 시 원소별 MCV 프로브 후 중복 보정을 포함해 합산하는 PG 동작을 따를 것.

### planner_visit_node (query_planner.c:7564)

**조인 카디널리티의 MAX(1.0) 바닥이 분수 카디널리티를 없애 조인 순서를 노이즈로 만든다** — 조인 결과 card 를 1.0 으로 바닥 처리하는 지점은 `planner_visit_node()` 안의 `cardinality = MAX (1.0, cardinality);`(develop :8124, :8134, :8158)와 `total_rows = MAX (1.0, total_rows);`(:8160)이다. 그 결과 25/30 계열 쿼리는 조인 2단계부터 모든 중간 결과가 card=1 이 되고, 이후 조인 순서는 ±1~4 코스트 틱 수준의 노이즈로 결정된다 — PG 는 1 미만 분수 카디널리티를 그대로 유지한다는 점이 근본 차이다.
- ✅ **리뷰 체크포인트**: 조인 카디널리티 계산 변경 시 MAX(1.0) 바닥이 어디서 걸리는지, 분수 카디널리티를 보존해야 하는 경로에 적용돼 순서 결정이 코스트 노이즈에 좌우되지 않는지 확인할 것.

**조인 순서 결정이 완전 동률(tie) / RBO dead zone 에 몰려 있어 통계 미세 변화에 취약하다** — eqjoin 선택도가 상류 카디널리티를 1~2 로 압축해버리기 때문에 부착 순서 결정이 비용 동률 구간에서 tie-break 로 결정된다 — 17a 의 t-vs-mc 부착은 1915 vs 1915 완전 동률(추정상 probe multiset 이 동일), 22a 는 1265 vs 1273(Δ8) 이었다. 그래서 아주 작은 통계 변화가 순서를 뒤집는다: Duj1 도입으로 `mk.keyword_id` sel 이 6.197e-6 → 6.698e-6 으로 바뀌자 pattern-C 계열(16b/17a/17e/2d)이 다시 DIFF 로 뒤집히고 20b/20c/9d 가 새로 일치해 order-match v2 가 38→34 로 회귀했다. 동률 판정은 `QO_COST_EQ(x, y)`(develop query_planner.c:115, 상대오차 1e-6; CBRD-27139 #7572 로 반대칭·부동소수 내성 확보), RBO 게이트는 `RBO_CHECK_COST 50`/`RBO_CHECK_RATIO 1.2`/`RBO_CHECK_LIMIT_RATIO 10`(:108-110, 사용처 :4396-4400, :4757)으로 구현돼 있다.
- ✅ **리뷰 체크포인트**: 선택도/NDV 를 건드리는 PR 은 '개선했다'가 아니라 '동률 구간에서 어느 쪽으로 뒤집혔나'로 평가하고, 순서 매치 수치 변동의 원인이 실제 정확도인지 tie-flip 인지 구분해 근거를 요구할 것.

**qo_apply_unique_join_cardinality 회귀 가설은 반증됨 — 오히려 net-helpful** — `qo_apply_unique_join_cardinality` 와 `qo_unique_index_cardinality` 는 실험 브랜치 신규 함수다(commit 5f3b970d8 "parameter tune"; **develop 에도 CBRD-27094 브랜치에도 없음**). `join_card = rhs_side_card × unique_ratio`, `unique_ratio = MIN(1, unique_side_card / unique_index_card)` 가 언더플로우해 1:1 FK→PK 조인을 card 1 로 붕괴시킨다는 가설이 있었으나, 함수를 no-op(`return term_sel`)으로 만드는 결정적 테스트에서 (1) {k,mk,t} 의 card-1 붕괴가 그대로 유지되었고(붕괴의 진원은 base eqjoin 선택도의 곱), (2) order-match 가 37→34 로 떨어지고 26개 질의의 순서가 바뀌었다. 즉 이 캡은 전체적으로 도움이 되는 쪽이며 가설은 폐기·되돌렸다.
- ✅ **리뷰 체크포인트**: 이 두 함수를 회귀 원인으로 지목하는 의견은 이미 반증된 가설임을 상기하고, 카디널리티 붕괴는 캡 함수가 아니라 base eqjoin 선택도 곱부터 계측할 것.

**부분 조인 탐색은 열거 예산으로 제한된다** — develop 은 CBRD-27142(#7721, 876a70814)로 테이블 수 계단(staircase) 대신 `qo_join_unit_from_budget()`(:9694)이 "추정 열거량이 예산에 들어가는 최대 레벨"을 골라 플래닝 비용을 조인 수 전 구간에서 유계로 만든다(주석 :9665-9693에 근거·실측 수치). 플랜 열거 폭을 건드리는 변경은 이 예산 함수와의 상호작용을 확인할 것.

### qo_plan_compute_cost (query_planner.c:755)

플랜 vtbl 의 cost_fn 디스패치 지점 — 각 플랜 타입의 비용 함수(`qo_*_cost`)가 vtbl 로 연결되며, `TEST_HASH_JOIN_FORCE_ENABLE`(:63) 같은 디버그 스위치도 vtbl 교체(:397-403)로 동작한다(해시 조인 절 참조).

### qo_sscan_cost (query_planner.c:1742)

시동 비용이 없다: `fixed_cpu_cost = 0.0`, `fixed_io_cost = 0.0`, `variable_cpu_cost = NCARD * QO_CPU_WEIGHT`, `variable_io_cost = TCARD`(develop :1747-1758). NCARD==0(통계 미수집)이면 `1.0 * QO_CPU_WEIGHT` = 0.0025 를 주는 분기가 있다(:1749-1752). iscan 에만 상수항을 더하는 변경이 소형 테이블 동률을 뒤집는 이유가 이 '대응항 없음'이다(descent_cpu 계열 참조).

### qo_iscan_cost (query_planner.c:2249)

**develop 현행 heap-fetch 모델: 완전 클러스터 object_IO + MIN(heap_rows, opages) 캡의 per-row 서차지** — 커버링 스캔이면 `object_IO = 1.0`, heap_access = 0. 아니면 `object_IO = opages * heap_sel` 에 CBRD-27113(#7527, a81193c9b)이 도입한 per-extra-row 서차지 `heap_fanout = (heap_rows > 1.0) ? MAX(0, MIN(heap_rows, opages) - 1.0) * FETCH_HEAP_COST : 0.0`(:2459)을 더한다 — 단일행(unique/pk) 프로브는 0 을 더해 기존 비용을 정확히 유지(blast-radius safe, 상수 주석 :85-88). 캡의 물리적 근거는 주석 그대로다: "fetching more rows than there are heap pages cannot touch more distinct pages"(:2455-2458). leaf IO 는 fixed/variable 로 분리된다: 하강이 닿는 첫 leaf 는 fixed(`fixed_io_cost = index_IO + first_leaf`, :2475), `leaves - first_leaf`·`iss_leaves`·heap_fanout 은 variable 측 `object_IO = MAX (1.0, object_IO) + ...`(:2469). PR#7622 는 이 MIN 캡 모델을 Mackert-Lohman 으로 교체하며 "MIN 이 k≈T 근처에서 최대 58% 과대추정"을 근거로 들었다 — 판단 쟁점은 "단일 스캔에 (재읽기를 포함하는) T>b 분기를 적용하는 것이 타당한가"로 귀결된다(develop 미머지).
- ✅ **리뷰 체크포인트**: heap-fetch 추정식 교체 PR 은 새 모델이 distinct-page 상한 불변식을 깨는지 먼저 확인하고, 과대추정 개선 주장과 상한 붕괴 위험을 함께 저울질할 것.

**옛 완전 클러스터 가정의 NL 프로브 고정 비용 문제 (역사)** — 인덱스 스캔 비용에서 object_IO 를 `opages × sel`(대상 행이 페이지에 완전 클러스터돼 있다는 가정)로만 계산하고 `ISCAN_IO_HIT_RATIO 0.5` 할인까지 곱해지던 시절, NL 내부 프로브 비용이 inner 관계 크기·fanout 과 거의 무관한 ~3~4 로 고정됐다 — 36M행 cast_info 프로브와 7행 kind_type 프로브가 같은 값으로 평가됐다. 이것이 JOB divergence 2순위 원인으로 10c(57.7s) 8c(37.3s) 18a(58.9s) 19a-c 의 주범이었고, 브랜치 커밋 c31d3b2f6 에서 object_IO 를 PG 의 무상관 가정 `MIN(heap_rows, opages)` 로 바꿔 총 683→455.2초(-33%), 8c 96.9→8.7, 8d 103→3.3, 10c 65→5.3 으로 개선됐다(PK 프로브는 카디널리티 MAX(1.0) 바닥 때문에 불변). 회귀도 동반됐다: 19c/d +4~5s, 9c/5c/13b/13c/7a +2~3s, 1a 0.03→0.59(소형 쿼리의 해시 오버헤드). develop 은 위의 FETCH_HEAP_COST 서차지 형태로 흡수했다.
- ✅ **리뷰 체크포인트**: 인덱스 스캔/NL 프로브 비용식 변경은 (1) 프로브 비용이 inner 크기·fanout 에 단조 증가하는지, (2) 클러스터링 가정이 PG(무상관)에서 임의로 벗어나지 않았는지, (3) PK/유니크 단건 프로브가 MAX(1.0) 바닥으로 여전히 불변인지, (4) 1a 류 소형 쿼리 회귀는 없는지 확인할 것.

**iscan 힙 fetch 비용의 MAX(1.0) 플로어가 페이지 비용 계수를 삼킨다** — `QO_RANDOM_PAGE_COST 4.0` 실험 결과 두 배치 모두 실패했다: (i) MAX(1.0) 플로어 **이전**에 곱하면 완전히 무력하다 — 선택적 probe 는 `opages × sel ≪ 1` 이라 플로어가 계수를 통째로 삼킨다(19d 만 순서가 흔들림). (ii) 플로어 **이후**에 적용해 probe 당 최소 4.0 을 강제하면 order-match v2 가 40→35 로 회귀했다(3a/3c/5c/7a/9d 상실) — 균일한 probe 패널티가 driver-vs-seqscan 균형을 PG 에서 멀어지게 만들기 때문. 둘 다 되돌렸고, 결론은 probe 비용 구조에 PG 식 per-tuple 비용 세분화가 선행돼야 한다는 것이다(`QO_RANDOM_PAGE_COST` 심볼은 현재 소스에 없음).
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

### qo_mackert_lohman_pages (develop 에 없음 — CBRD-27094/PR#7622 계열)

**T>b 분기에는 캡이 없어 N 에 선형·무상한으로 커진다** — `qo_mackert_lohman_pages(T, N)`(브랜치 query_planner.c:3608-3636)은 PG `costsize.c` 의 `index_pages_fetched()` 이식본이고, 구조적 비대칭이 있다: `T <= b` 분기에는 `if (pages_fetched > T) pages_fetched = T;` 캡이 있으나 `T > b` 분기(`b + (N-lim)*(T-b)/T`)에는 캡이 없다. 이 함수는 `qo_iscan_cost` 의 단일 스캔 object_IO(브랜치 :2480)와 `qo_nljoin_cost` 의 반복 프로브 포화(브랜치 :3741-3742) 양쪽에서 쓰인다. 실측: cast_info(힙 129,909 페이지)에서 N=3,018,730 일 때 2,262,020 페이지 = 힙 전체의 17.41배가 나오며, 동일 입력에서 develop 의 `MIN(heap_rows, opages)` 캡은 129,909 로 상한을 지킨다. 버퍼 크기 `b` 는 하드코딩된 `QO_EFFECTIVE_CACHE_PAGES`(비용 상수 절 참조).
- ✅ **리뷰 체크포인트**: 단일 스캔에서 힙 페이지 수를 초과하는 fetch 추정이 나오면 T>b 분기의 캡 부재가 의도된 것인지(재읽기 포함 의미인지) 검토를 요구할 것.

### qo_nljoin_cost (query_planner.c:3548)

inner 반복 프로브의 IO 는 `ISCAN_IO_HIT_RATIO 0.5` 할인(develop :3619) 또는 `SSCAN_DEFAULT_CARD` 가산(:3625)으로 계산되고, 서브쿼리 CPU 보정이 :3675-3676 에 있다.

**NL 프로브 비용 과소평가 — 300버킷 통계에서 q19 플랜이 정반대로 뒤집힌다** — 4버킷 통계에서는 lineitem 구동(sscan → part PK 프로브, 추정 2.88M, 실측 ~5s)을 고르지만, 300버킷 히스토그램에서는 part 구동(part 2M 무필터 sscan → fk_lineitem_partsupp 인덱스 프로브 2M회, 추정 1.91M 으로 더 싸 보임, 실측 25~48s)으로 뒤집힌다. 추정 순위가 실측과 정반대이며(플랜 덤프 cubrid-tpch/plans/q19_b572_16G_300bk.raw vs q19_b572_16G_defbk.raw), 이는 NL 프로브 비용 과소 계열 문제다. 즉 통계 정밀도 향상이 잘못된 비용 모델 아래에서는 오히려 나쁜 플랜을 고르게 만든다.
- ✅ **리뷰 체크포인트**: 통계 정밀도(버킷 수) 변경 후 플랜 플립이 생기면 통계가 아니라 비용 모델을 먼저 의심하고, 대량 프로브(수백만 회) 플랜의 추정 비용이 sscan-구동 플랜보다 싸게 나오지 않는지 확인할 것.

**PR#7453 계열 프로브 IO 상한이 q19 플랜 플립을 막는다 (동시에 여러 질의를 움직인다)** — PR#7453 계열의 비용 모델 수정(프로브 object_IO 를 `MIN(heap_rows, opages)` 로 제한)을 담은 overhaul 브랜치는 동일 SSOT 조건(8G·300버킷)에서 q19 가 뒤집히지 않고 lineitem 구동을 유지해 5.34s 로 끝난다(develop 46.96s 대비 8.8배) — 잘못된 프로브 IO 비용이 만든 '가짜 박빙'을 벌려놓은 실증이다. 다만 전체는 250.3s(develop 281.2s 대비 -11%)로, q19 -41.6s·q5 -7.4s·q22 개선인 반면 q3 +57%·q7 +21%·q13 +21%·q18 +17% 회귀가 남는다(results/ssot_34748fed7_0805_161834.tsv vs results/ssot_b572177a1_0805_152020.tsv).
- ✅ **리뷰 체크포인트**: 프로브 IO 비용 상한 관련 코드를 수정할 때는 q19 뿐 아니라 q3/q7/q13/q18 회귀를 함께 확인할 것 — 이 상한은 여러 질의의 플랜 선택을 동시에 움직인다.

**M-L 포화가 물리 I/O 만 줄이고 프로브당 버퍼접근을 지우는 문제 (hash-join → idx-join 역전) (develop 에 없음 — CBRD-27094/PR#7622 계열)** — 반복 프로브 보정(M-L 포화)은 프로브가 많아지면 힙 I/O 를 포화시켜 상수에 수렴시키는데, 실제로 남는 프로브당 버퍼 접근(실측 약 24 pgbuf_fix/프로브)이 비용에 반영되지 않았다. 그 결과 hash-join(sscan/sscan)이 idx-join 으로 뒤집혔고 실측이 `time 933, fetch 240904, ioread 130` — 서버시간 8.8배, 버퍼 페치 65배 퇴행했다(sql/_35_fig_cake/cbrd_24044/cbrd_25060/cases/cbrd_25060_2.sql 5번 블록 두 번째 쿼리, 힌트 없는 ordered 4컬럼 등가조인). 브랜치 head 는 힙/리프를 각자 객체 크기로 따로 포화시키고(브랜치 :3739-3745) 잔여 프로브당 비용을 `iscan_descent_cpu`(:3709)로 남기는 형태이며, 이 결함은 descent 비대칭과 같은 함수 계열이라 서로 간섭할 수 있어 반드시 분리해 측정해야 한다.
- ✅ **리뷰 체크포인트**: NL 반복 프로브 보정(포화)을 손댈 때 포화 후에도 프로브당 최소 버퍼접근 비용이 남는지, hash-join 대비 역전이 생기지 않는지 확인하고, descent 관련 수정과 같은 커밋에 섞지 말 것.

**해시 조인 활성화가 NL 프로브 저가 버그를 증폭시킨다 (8d 재앙 사례)** — 8d 가 5.4→103.1초로 터진 원인은, 해시 조인이 1행짜리 rt 를 늦게 붙일 자유를 주자 옵티마이저가 `cn⋈mc⋈t⋈ci`(추정 30.2M행) 프리픽스를 만들고 rt 를 해시로 필터하는 플랜을 골랐기 때문이다. 카디널리티 추정치는 30M 으로 정확했는데 비용이 싸게 나온 것이 문제였다 — NL 프로브 저가 평가(ci 프로브 cost 4) 버그를 해시 조인이 더 공격적으로 악용하는 복합 문제다. 결론: 해시 조인 도입은 2순위 갭을 해소하지만 `qo_nljoin_cost` 가 inner 크기/fanout 을 반영하도록 고치지 않으면 8c/8d 형 악용이 계속 나온다.
- ✅ **리뷰 체크포인트**: 조인 방식 선택 변경이 '추정 카디널리티는 큰데 비용은 작게 나오는' 프리픽스를 새로 만들지 않는지, 특히 1행짜리 필터 테이블을 뒤로 미루는 플랜이 생기지 않는지 확인하고, 카디널리티가 맞는데 느려졌다면 비용식을 의심할 것.

### qo_mjoin_cost (query_planner.c:3705)

**mergejoinscansel 미구현** — 머지 조인에서 양쪽 입력을 어디까지 스캔하게 되는지(PG 의 `mergejoinscansel`)를 히스토그램으로 추정하는 로직이 없다. 즉 머지 조인은 항상 양쪽 전체 스캔 비용으로 계산되어, 한쪽이 조기 종료되는 경우를 과대 비용으로 본다.
- ✅ **리뷰 체크포인트**: 머지 조인 비용 변경은 스캔 범위 추정 부재를 전제하는지 확인하고, 새로 도입한다면 히스토그램 경계와 조인 키 범위의 교집합을 기준으로 할 것.

### qo_hjoin_cost / qo_examine_hash_join (query_planner.c:3784 / :6818)

**해시 조인 게이트는 뒤집혔다 — 옛 default-disable 이 아니라 현재는 force-enable 디버그 스위치** — 과거 분석 시점에는 `TEST_HASH_JOIN_ENABLE 0` 으로 해시 조인 선택이 컴파일 아웃되어 있었고, `qo_examine_hash_join` 이 기본 차단하여 옵티마이저가 좌편향(left-deep) 인덱스-NL 체인만 만들 수 있었다 — JOB 113 질의에서 CUBRID 는 864 조인 전부 idx-join(hash 0/merge 0), PG 는 NL 791 + Hash 65 + Merge 8 이었고, 8c 의 `rt⋈ci`(role='writer')는 추정이 사실상 일치(CUBRID ~3.01M / PG ~3.02M / 실제 2.73M)하는데도 플랜 모양이 갈렸다. PR CUBRID#6782(CBRD-26475, 머지 커밋 1608d670e)가 default-disable 게이트를 제거해 `qo_hjoin_cost` 가 활성화됐고, 현재 매크로는 의미가 반대다 — `TEST_HASH_JOIN_FORCE_ENABLE 0`(develop :63)이 1 이면 vtbl 이 `qo_zero_cost` 로 바뀌어 해시 조인을 **강제**한다(develop :397-403). 활성화 당시 전체 측정은 615.5→749.2초(+21.7%), PG 대비 2.48→2.52x, 순서 매칭 31→33 으로 결과가 극명히 갈렸다(18a 61.5→22.5s 개선 vs 8c 44→96.9s, 8d 5.4→103.1s).
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

### 히스토그램 일반 (histogram/)

**현재 히스토그램이 커버하는 범위 (equi-depth + MCV + HLL NDV)** — `feature/reservoir-sampling`(0b84bbaac, CBRD-26936) 계열 기준으로 equi-depth 히스토그램(HST2 blob, 카탈로그 `_db_histogram`) + MCV(1% 임계) + HLL 기반 NDV + 정확한 null_frequency 가 구현돼 있다(통계 수집 후속은 develop 532ce4b6d CBRD-26959 #7476). 선택도 함수는 eqsel(MCV 매칭 + 잔여 분산, `histogram_get_equal_selectivity` :1032), scalarineqsel(버킷 보간 — 템플릿 `comp_parts()` develop histogram_cl.cpp:908, :1299-1311 에서 int64/double/string_view/uint64 인스턴스화), LIKE(:1824), nulltestsel 까지 PG 상당 수준이다.
- ✅ **리뷰 체크포인트**: 새 선택도 경로 추가 시 기존 eqsel/scalarineqsel/LIKE/nulltestsel 과 중복 구현하지 말고, 버킷 보간이 필요하면 `comp_parts()` 를 재사용할 것.

**표현식 f(col) 에는 히스토그램이 적용되지 않는다 (PT_NAME 만 인정)** — 히스토그램 조회는 피연산자가 `PT_NAME` 인 경우에만 성립한다(`if (lhs == NULL || lhs->node_type != PT_NAME)` develop histogram_cl.cpp:598, :2524). `UPPER(col) = 'X'`, `col + 1 > 10` 같은 표현식은 히스토그램을 못 타고 기본 상수로 떨어진다(PG 의 expression statistics 상당 기능 없음).
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

**Duj1(Haas-Stokes) NDV 추정기의 구현 위치와 계약** — Duj1 은 전적으로 `HISTOGRAM_WITH_SAMPLING_SCAN_QUERY_TEMPLATE`(histogram_cl.hpp) 안에서 SQL 로 구현돼 있다: `sampq` CTE 가 `q = LEAST(1, sample_rows / <클래스 행수>)` 를 계산하고, hist_grouped 의 approx_ndv = `CAST(ROUND(LEAST(n/q, GREATEST(d, n*d/(n - f1 + f1*q)))) AS BIGINT)`, 여기서 f1 = SUM(count=1 케이스). C 쪽(histogram_cl.cpp `get_histogram`)은 `sm_find_class` + `sm_get_class_with_statistics` → `stats->heap_num_objects` 로 클래스 카디널리티를 추가 `%lld` 인자로 전달하며, 이를 위해 query_buf 를 3072+ 로 키웠다. FULLSCAN 템플릿은 q=1 이면 Duj1 이 d 로 자연 퇴화하므로 손대지 않았고, PG 가드(f1==n, f1==0, clamp)가 필요하다는 점이 설계 전제다. *(행번호·상세는 CBRD-27094 @ faf5a3b2a 기준 재검증 — develop 반영 여부/위치 재확인 필요)*
- ✅ **리뷰 체크포인트**: 템플릿 문자열에 포맷 인자를 추가/변경했다면 query_buf 크기, 모든 호출부의 %lld 개수·순서, fullscan 템플릿과의 인자 불일치, 그리고 `sm_get_class_with_statistics` 로 얻은 통계 포인터의 수명/해제를 함께 확인할 것.

**Duj1 의 보정 한계 — 페이지 단위 SAMPLING_SCAN 클러스터링** — Duj1 적용으로 NDV(mc.company_id)가 160,692 → 199,557 로 올라갔으나 실제값 234,997 에는 못 미친다(sum bucket ndv 160,656 vs 234,997 @50% sample). 원인은 페이지 단위 SAMPLING_SCAN 이라 같은 페이지 내 값들이 클러스터링되어 f1(1회 등장 값) 통계가 실제 무작위 표본과 다르기 때문이다. 즉 추정기를 고쳐도 표본 추출 방식이 남은 오차의 상한을 결정한다.
- ✅ **리뷰 체크포인트**: NDV 추정 정확도 개선 주장은 표본 추출 방식(페이지 단위 vs 행 단위)을 함께 볼 것 — 무작위 표본을 전제한 추정기 공식을 페이지 샘플에 그대로 적용하는 코드에는 그 전제 위반을 지적할 것.

### comp_parts (histogram_cl.cpp:908)

**min/max·avg_width 미저장 → 첫 버킷 하한이 없어 근사 핵을 쓴다** — 히스토그램에 컬럼 min/max 와 avg_width 를 저장하지 않아 첫 버킷의 하한 경계값을 알 수 없고, 이는 범위 조건의 하단 경계 근처 선택도가 원리적으로 부정확한 원인이다. develop 주석이 문제를 그대로 서술한다: "The first bucket has no previous endpoint stored (its lower bound is unknown), so bucket_hi (b - 1) would read bucket record (uint) -1 -> assert in debug / out-of-bounds in release"(develop histogram_cl.cpp:923-930). 우회 방식: 옛 half-mass(절반 질량) 근사는 두 번째 버킷 폭을 아래로 미러링하는 방식으로 대체됐다("instead of half the first bucket's mass"). 근본 해결은 여전히 min/max 수집·저장이라 통계 수집 포맷 변경이 선행돼야 한다. *(원 메모의 histogram_cl.cpp:756-759 / 커밋 56e3aabf8 half-mass 는 행 번호 확인 필요 — 현재 소스와 불일치)*
- ✅ **리뷰 체크포인트**: 범위 선택도(scalarineqsel) 버그는 histogram_cl.cpp:918-935 의 첫 버킷 하한 근사가 원인인지 먼저 의심할 것.

### histogram_get_join_selectivity (histogram_cl.cpp:1528)

**PG eqjoinsel_inner 이식본 — develop 머지됨(10d0aa0e7, CBRD-26746 #7508)** — 양쪽 MCV 를 정렬해 투포인터로 매칭 → 매칭 MCV 기여분 + 잔여 확률을 `잔여/(nd - nmatches)` 로 분배(develop :1619-1639; many-to-many collation-aware 매칭은 양측 분모에서 각자의 matched distinct 를 제외한다는 주석 포함) → 최종적으로 `min(totalsel1, totalsel2)` 선택(:1641, 주석 "the smaller estimate is the view from the larger-NDV side") → 양쪽 (1-nf) 로 나눠 반환(:1643-1656, qo_expr_selectivity 절 참조) → 0 이면 `1/(total_rows1*total_rows2)` 바닥(:1660-1663). 히스토그램/MCV 부재 시 폴백은 기존 `1/max(icard)`. 검증: `t.kind_id=mc.company_type_id` sel 0.147469(손계산 일치), `cn.id=ci.person_role_id` 카디널리티 17.57M(null 제외 실제치 부합), `n.id=ci.person_id` 2.40e-7 이 PG 수치와 일치.
- ✅ **리뷰 체크포인트**: 조인 선택도 변경 시 세 단계(MCV 투포인터 / 잔여를 nd-nmatches 로 분배 / min(totalsel1,totalsel2))가 모두 보존되고 MCV·히스토그램 부재 시 폴백 경로가 살아있는지 확인할 것.

**eqjoinsel 에 NDV clamp 가 없어 조인 선택도가 과대 계산된다 (20a 회귀)** — eqjoinsel 도입(ba0d955ee) 후 17a/17d/20a 가 base 에서는 PG 와 일치하던 조인 순서를 이탈했다 — per-term 선택도 값 자체는 PG 에 더 가까워졌으나(`n.id=ci.person_id` 2.4e-7 등) 평평한 비용 모델과 결합되어 순서가 악화됐다. 20a 의 직접 원인은 mk-cc 선택도가 3.53e-6→6.81e-6 으로 배증한 것이고, 그 원인은 `cc.movie_id` 의 NDV 가 93,514 인데 조인 상대인 title 도메인은 2.5M 이라 NDV clamp(작은 쪽 NDV 를 상대 도메인/조인 대상 크기로 제한)가 없기 때문이다(develop 코드에도 clamp 없음 — 재확인).
- ✅ **리뷰 체크포인트**: eqjoinsel 관련 변경은 양쪽 NDV clamp 적용 여부를 확인하고, per-term 선택도가 PG 에 가까워졌다는 것만으로 성공 판정하지 말고 최종 조인 순서/시간까지 확인할 것.

**histogram_get_eqjoin_selectivity Stage 3 의 버킷 오버랩 MIN 언더컷 (Card-cost defect #2) (develop 에 없음 — CBRD-27094 이전 실험 계열)** — `histogram_get_eqjoin_selectivity`(실험 브랜치 histogram_cl.cpp Stage 3)는 버킷쌍 기반 `overlap_residual_mass` 를 계산해 건전한 전역 fallback 값과 MIN 을 취했고, 이 때문에 선택도가 부당하게 낮아졌다. 17a 에서 `mc.company_id=cn.id`(FK→PK) sel 이 오버랩값 3.065e-6 로 전역 fallback 3.58e-6 을 언더컷했고(uniform 4.26e-6), 그 결과 t-vs-mc 부착 결정이 비용 1915 vs 1915 완전 동률이 되어 tie-break 가 순서를 결정했다 — PG 의 eqjoinsel 에는 버킷 오버랩 메커니즘 자체가 없다. 오버랩 MIN 을 제거하자 attachment-order 매치 34→38/113, leaf 27→31/113, 회귀 0 이며 16b/17a/17e/2d(pattern-C 계열)가 새로 일치했다(검증: `SHOW HISTOGRAM movie_companies ON company_id` / `company_name ON id` 덤프). *(이 심볼은 CBRD-27094 브랜치에도 develop 에도 없다 — `histogram_get_join_selectivity` 만 존재)*
- ✅ **리뷰 체크포인트**: eqjoin 선택도 경로에 PG 에 없는 보정항(오버랩/잔여질량 등)을 MIN/MAX 로 끼워넣는 변경은 거부하고, 추가 항이 건전한 전역 추정을 아래로 끌어내리지 않는지 확인할 것.

**한쪽만 MCV 리스트가 있는 eqjoin fallback 이 MCV 행의 조인 질량을 통째로 누락 (Card-cost defect #3) (실험 브랜치 계열)** — 기존 fallback 은 `non_mcv_frac_l × non_mcv_frac_r / max(ndv)` 였는데, 이는 MCV 에 속한 행들의 조인 기여를 0 으로 만든다(mc 의 MCV 15.8% 행이 아무 기여도 안 함) → term sel 3.58e-6. PG 의 `eqjoinsel_inner` 은 양쪽 MCV 리스트가 없을 때 NULL 비율만 곱한 뒤 **전체 모집단 기준 `1/max(nd1,nd2)`** 를 쓴다. Stage 3 에서 `!has_both_mcv_lists` 일 때 `selectivity_mass = 1/max(lhs_total_ndv, rhs_total_ndv)` 로 고치자 1/234,997 = 4.255e-6(이상값)이 나오고, max 를 쓰므로 정확한 PK 쪽 NDV 가 채택되어 LHS NDV 잡음에 강건해진다(17a 검증 mc⋈cn sel = 4.25537e-6).
- ✅ **리뷰 체크포인트**: MCV 경로 밖(non-MCV) 잔여 비율만 곱해 선택도를 만드는 코드가 보이면 MCV 행의 조인 질량이 사라지지 않는지 확인 — 분모는 min 이 아니라 max(NDV) 여야 하고 분자에 non_mcv_frac 곱이 남으면 재발이다.

**양쪽 모두 MCV 가 있는 many-to-many 조인은 여전히 과대추정 (위 두 수정과 무관)** — C-1(오버랩 언더컷 제거)/C-3(PG 한쪽-MCV fallback) 수정은 `company_id=cn.id` 류의 한쪽-MCV/오버랩 케이스만 고친다. movie_id 계열의 many-to-many 조인은 양쪽에 MCV 리스트가 있어 both-MCV `pg_mcv_mass`/overlap 경로로 들어가고 uniform(1/max(NDV)) 대비 과대추정이 남는다. 실측으로 stash(C-1+C-3+Duj1) 복원 시 movie_id 조인 4건의 선택도가 origin 과 바이트 단위로 동일했다(31b `mi_idx.movie_id=mk.movie_id` 2.174e-6 고정) — 즉 이 회귀들에 대해 두 수정은 완전히 무력(inert)이다.
- ✅ **리뷰 체크포인트**: eqjoin 선택도 수정이 특정 회귀를 고친다고 주장하면 그 조인이 both-MCV 경로인지 one-sided 경로인지부터 확인할 것 — 선택도 값이 그대로인지 비교하면 즉시 반증 가능하다.

### histogram_get_like_selectivity (histogram_cl.cpp:1824)

**LIKE prefix 를 (선택도 추정에서) 범위로 변환하지 않고 버킷 경계값 매칭만 한다 (편향)** — PG 는 `make_greater_string` 으로 LIKE 접두사를 `[prefix, prefix+)` 범위 조건으로 바꿔 히스토그램 보간을 쓰지만, CUBRID 의 이 함수는 그 변환 없이 MCV 매칭 + 버킷 경계값 매칭(`matched_non_mcv_buckets`, develop :1909-1920) + 휴리스틱만 쓴다. 경계값에만 의존하므로 접두사가 버킷 경계와 어긋나면 선택도가 편향된다. (인덱스 스캔용으로는 rewriter 가 prefix LIKE 에서 파생 BETWEEN 범위를 만들지만 — CBRD-27036, qo_iscan_cost 절 참조 — 그것은 스캔 범위이지 히스토그램 보간 선택도가 아니다.)
- ✅ **리뷰 체크포인트**: LIKE 선택도 개선 PR 은 접두사→범위 변환(make_greater_string 상당)을 도입했는지 아니면 또 다른 휴리스틱을 얹었는지 구분할 것 — 후자는 편향을 다른 방향으로 옮길 뿐이다.

**develop 의 혼합식: 크기 기반 블렌드 + 클램프 (disagreement_boost 는 develop 에 없음)** — develop 은 비-MCV 추정을 히스토그램 크기로 가중한다: 버킷 100개 이상이면 경계값 매칭 비율을 전적으로 신뢰, 10~99개면 `w = size/100` 으로 패턴 휴리스틱과 블렌드, 10개 미만이면 휴리스틱 단독(:1931-1946). 결과는 [0.0001, 0.9999] 로 클램프(:1947-1955)하고, (1-nullfrac) 나눗셈 규약 후 `max(1/total_rows, sel)` 바닥을 적용한다(:1965-1975). 패턴 휴리스틱 `pattern_heuristic_selectivity`(:1670)는 PG 와 동일 상수(FIXED_CHAR 0.20 / ANY_CHAR 0.9 / WILDCARD 5.0)를 쓴다.

**disagreement_boost 가 매칭 버킷 0개일 때 패턴 휴리스틱을 0으로 지운다 (Card-cost defect #1) (develop 에 없음 — 실험 브랜치 계열)** — 패턴에 매칭되는 히스토그램 버킷이 0개일 때(희귀 패턴에서는 정상 — 샘플된 bucket_hi 값이 수백 개뿐) `disagreement_boost` 가 boosted_weight 를 1 로 밀어 `pattern_heuristic_selectivity` 를 0 으로 만든다. 그 결과 sel 이 1/NCARD 로 클램프되어 `k.keyword LIKE '%sequel%'` 가 정확히 1행으로 추정된다(실제 30, PG 추정 13). 패턴 휴리스틱 자체는 단독으로 ~43행으로 PG 보다도 낫다 — 수정 방향은 `matched_non_mcv_buckets == 0` 이면 boost 를 적용하지 말고 pattern_sel 로 폴백하는 것. *(`disagreement_boost` 심볼은 CBRD-27094 브랜치에도 develop 에도 없음 — 실험 브랜치 한정)*
- ✅ **리뷰 체크포인트**: 패턴 선택도 코드에서 '매칭 버킷 0개'가 에러가 아니라 정상 경로로 처리되고 휴리스틱 폴백이 살아 있는지, 가중치 혼합식이 한쪽 항을 0으로 만들 수 있는 구조인지 확인할 것.

### HistogramReader::reset (histogram_reader.cpp:72)

**구버전 히스토그램 blob 은 v2 리더가 조용히 거부하고 폴백한다 (단, per-term 진단 플래그가 있다)** — `reset()` 은 크기(develop :75), `HST2` 매직(:82), 버전==2(:86), `total_size_ != blob_.size()`(:98-104) 가드를 갖고, 불일치 blob 을 에러 없이 `ER_FAILED` 로 돌려보낸다. 주석이 의도를 명시한다: "an old-format (HST1) or corrupt record. Reject it gracefully so callers fall back to default estimates". 즉 새 통계 코드는 '동작하지 않는' 게 아니라 '아무 말 없이 옛 경로로 도는' 형태로 실패하므로, 통계를 재생성하지 않은 DB 에서는 개선 효과가 0 으로 측정된다. 진단 훅: `env->sel_hist_used`/`env->sel_hist_fallback`(query_graph.h:977-978)과 `QO_TERM_SEL_FROM_HISTOGRAM`(qo_analyze_term 절 참조)으로 어느 term 이 히스토그램을 실제로 탔는지 구분할 수 있다.
- ✅ **리뷰 체크포인트**: 히스토그램 포맷/버전 변경 PR 은 리더의 버전 불일치가 `sel_hist_fallback` 등으로 관측 가능한지, 그리고 성능·정확도 검증 전에 히스토그램을 재생성했는지 확인할 것.

### qo_extract_or_restrictions (rewriter/query_rewrite_term.c:4795)

**멀티 spec OR 에서 단일 spec 제약 추출 — develop 머지됨(c283e799d, CBRD-27171 #7613)** — join-OR 의 모든 분기가 한 릴레이션 전용 조건을 가지면 그 OR 를 해당 릴레이션의 중복 제약으로 WHERE 에 추가한다(TPC-H q19 가 canonical shape 라고 함수 주석이 명시). rewriter 레벨 구현이며 호출부는 query_rewrite.c:480. 검토 당시 후보 위치로 CNF 변환/term 분류부(query_graph.c 의 `qo_analyze_term`)도 거론됐으므로 동일 기능이 여러 레이어에 중복 추가되지 않는지 주의해야 한다.
- ✅ **리뷰 체크포인트**: OR 추출 변경이 rewriter 와 query_graph.c/qo_analyze_term 양쪽에 중복으로 들어가지 않았는지, '모든 분기가 해당 릴레이션 전용 조건을 가진다'는 전제를 정확히 검사하는지(한 분기라도 조건이 없으면 부정확한 제약) 확인할 것.

**location != 0 (outer join ON 유래) 팩터는 반드시 제외해야 한다** — outer join 의 ON 절에서 유래한 팩터(location != 0)를 OR 추출 대상에 포함하면 outer join 의 null-확장 행이 사라져 결과가 달라진다. develop 머지본은 이 가드를 내장했다: "a factor that came from an outer join's ON condition (location > 0) is evaluated at its join level and does not reject the null-padded rows, while the derived filter would run at WHERE level and wrongly reject them"(develop :4824-4830). PR#7613 개발 중 커밋 4f6e24024 로 추가됐고, LEFT JOIN 항등식(4097 = 4074 + 23)으로 검증했다. 추가 가드: `or_next` 체인이 달린 팩터는 flatten 이 disjunct 일부만 모아 과강한 제약을 만들 수 있어 스킵(:4815-4820), disjunct 수 상한 `QO_OR_EXTRACT_MAX_DISJUNCTS 8`.
- ✅ **리뷰 체크포인트**: 제약을 WHERE 로 끌어올리는(pull-up) 모든 변형에서 term 의 location 값 가드가 있는지, LEFT/RIGHT JOIN 회귀 케이스(전체 행수 = 매칭 행수 + null-확장 행수)로 검증됐는지 확인할 것.

**선택도 이중계상은 머지본이 PT_EXPR_INFO_OR_DERIVED 마크로 보정한다** — 추출된 OR 를 원래 join term 과 함께 남긴 채 단일 릴레이션 제약으로 추가하면 같은 조건이 두 번 곱해져 선택도가 이중 계산된다(PG 는 `consider_new_or_clause()` 로 보정; PR#7613 draft 시점에는 '남은 개선 ①'). develop 머지본은 파생 팩터를 `PT_EXPR_INFO_OR_DERIVED`(모양에 따라 `_EXPENSIVE` 추가)로 마크하고, 이 마크가 QO_TERM 플래그로 전달되어 `qo_node_add_sarg()` 가 행수 이중계상을 스킵하고 `make_pred_from_plan()` 이 인덱스가 채택하지 않은 비싼 복사본을 드랍한다(함수 주석 :4788-4794).
- ✅ **리뷰 체크포인트**: 중복 제약을 추가하는 변경에 선택도 보정(추출 절을 원 절의 선택도에서 나누거나 계산에서 제외)이 함께 들어갔는지 확인할 것 — 없으면 카디널리티 과소추정으로 다른 질의에 회귀가 생긴다.

**추출된 OR 가 하류에서 재전개되어 27-conjunct 로 풀리면 추가 1.3x 손해** — 추출 결과를 단일 term 형태로 유지하지 못하면 하류 처리에서 다시 전개되어 27-conjunct 형태가 되고, 단일 term 유지 대비 약 1.3배 느려진다(IMP-027 실측 0.293s vs 당시 출력 0.383s). draft 시점 '남은 개선 ②' 였다 — **develop 머지본이 단일 term 을 유지하는지는 미확인(재검증 필요)**.
- ✅ **리뷰 체크포인트**: 추출한 OR 절이 하류 CNF/term 전개에서 다시 분해되지 않고 하나의 term 으로 유지되는지 플랜/term 덤프로 확인할 것.

**소형 인덱스 캡은 JOB 조인 순서를 바꾼다 — JOB 차원 테이블이 캡 구간에 들어간다** (2026-08-28 실측, `.51`)
— 위 '평탄 페널티' 를 고치는 방법으로 평탄항을 `MIN (descent, MAX (1, NCARD) * QO_CPU_WEIGHT)` 로
상한하는 안을 시도했는데, **JOB 플랜 10건이 바뀌고 그중 2건이 회귀**였다. JOB 은 대형 팩트 테이블만
있는 벤치가 아니다 — `ct`(company_type 4행), `cct1/cct2`(comp_cast_type 4행), `kt`(kind_type 6행),
`lt`(link_type 18행), `it`(info_type 113행) 같은 차원 테이블이 있고, 캡은 NCARD 가
`MAX(1, height) * BTREE_DESCENT_PAGE_OVERHEAD` (단층 50, 2층 100) 미만일 때 물리므로 **4~18행 차원
테이블의 인덱스 스캔이 거의 공짜가 되어 조인 순서 앞으로 끌려온다.**

가장 나쁜 결과는 **PG 순서 일치의 상실**이다. `1a`·`1b` 는 수정 전 PG 조인 순서와 정확히 일치했는데
(1a: `it mi_idx mc ct t`) 캡 투입 후 어긋났다(`mc ct mi_idx it t`). 1a 는 시간도 0.014s → 0.242s.
인터리브 median-of-5(rep 마다 팔 교대) + MAD 판정으로 1a +1629%, 27c +75%, 23c +8.7%, 15d +9.1%
회귀 대 개선 8건. 지표가 'PG 와의 조인 순서 일치' 이므로 이건 다툴 여지 없는 회귀다.

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

## 3. 예비 이슈 사항

> 미수정 버그·의심·문서 정정 후보·구조적 한계. 해소되면 삭제가 아니라 "해소됨(커밋/PR)"로 갱신.

- **[문서 결함]** `src/optimizer/AGENTS.md` Where-to-Look 의 "Fix cost estimation = plan_generation.c"는 오안내 — 실제는 query_planner.c 의 `qo_*_cost` 계열. develop 95b79e7ed 에 여전히 존재(재확인). 정정 PR 은 사용자 판단 대기.
- 조인 카디널리티 `MAX(1.0)` 바닥 — 분수 카디널리티 소거로 조인 순서가 코스트 노이즈에 좌우. develop planner_visit_node :8124/:8134/:8158/:8160 에 존재(재확인).
- eqjoinsel NDV clamp 부재 — 조인 선택도 과대(20a 회귀). develop histogram_get_join_selectivity 에 clamp 없음(재확인).
- 구조적 미구현 4종: `scalararraysel`(IN 원소별 MCV 프로브) 미구현(develop cap 0.5 유지 재확인) / correlation 미수집(ISCAN_OID_ACCESS_OVERHEAD 5 로 땜질, develop :82-84 TODO 재확인) / 히스토그램 min·max 미저장(첫 버킷 하한 근사, develop :923 주석 재확인) / LIKE prefix→범위 변환 없음(선택도 측, develop 재확인).
- 기본 선택도 상수 PG 불일치(EQ 0.001 vs 0.005, COMP 0.1 vs 0.3333) — 폴백 경로 체계적 과소추정. develop query_planner.h:116/:118 재확인.
- descent_cpu 비대칭 — **해소됨(PR#7622 `54b1b44d6`, inner 전용 과금)**. 잔여 두 축은 위 §2 캘리브레이션 절: `HJ_MEM_ALLOC_CONSTANT` 800 은 두 벤치 사이의 타협값(별건: 필터된 차원 테이블을 거친 조인 카디널리티), `qo_plan_cmp` 1.2배 밴드 안 "term 많은 인덱스 우선" 규칙(cbrd_25382_1, 별건 후보).
- (구 서술) descent_cpu 비대칭(iscan 전용 고정 CPU 항) — PR#7622 27건 회귀 근본 원인. develop 미머지(develop 에 descent_cpu 없음). **.50 수정 시도는 사용자 지시로 종결(2026-08-26, 미적용)** — 수정안(`iscan_descent_cpu` 필드 분리, nljoin inner 전용 과금)은 .50 `~/dev/cbrd27094-descent-fix.patch` 로 보존. 산식 검증 완료(구동측 0.2575→0, inner 과금 불변), 19a 플랜 유지 확인. JOB 순효과는 세션 오프셋(+5.76% 균일 시프트)으로 미확정 — 재개 시 동일 세션 A/B 필수.
- `qo_mackert_lohman_pages` T>b 분기 캡 부재 — 단일 스캔 fetch 추정이 힙 전체의 17.4배까지 발산. develop 미머지(PR#7622 계열 브랜치 한정).
- `QO_GET_HIST_STATS` 매크로가 여전히 캐시 원본 포인터를 반환(query_graph.h:203-204) — dangling 자체는 주석 사이트 복사(937d09feb)로 해소됐으나, 매크로 신규 사용처는 같은 결함을 재생산할 수 있음(부분 해소).
- 파스 트리 histogram dangling 결함 — **해소됨(develop 937d09feb, CBRD-27279 #7761)**.
- OR 제약 추출 부재(q19) — **해소됨(develop c283e799d, CBRD-27171 #7613)**. 단, 추출 term 의 단일 term 유지(27-conjunct 재전개) 여부는 머지본에서 미확인.
  잔여 개선 후보(.50 프로젝트 md 이관, 2026-08-26): ① 추출 절의 **선택도 이중계상 보정**(PG `consider_new_or_clause` 상당 — 추출 OR 를 중복 제약으로 더할 때 선택도를 나눠 보정) 미구현 ② 단일 term 형태 유지 시 추가 ~1.3x 여지(IMP-027 실측 0.293 vs 0.383) ③ CTP sql/medium 회귀 확인 미수행. 참고: 동일 발견이 주영진 IMP-027 캠페인에 있음(필터플랜 코스트 29,357까지 일치) — 중복 구현 방지 조율은 사용자 몫.

## 4. 진행중인 작업

> 각 컨테이너가 자기 소절을 직접 관리한다. 완료되면 지우지 말고 "완료(PR/커밋)"로 갱신.

### .50
- CBRD-27140: `qo_index_cardinality` 계열·`QO_ATTR_CUM_STATS` INT64 승격 (PR#7856, 2026-09-02 리뷰 대기).
- descent_cpu 회귀(PR#7622 근본 원인) 코드 수정 진행 중 — (a) inner-only 우선, 이후 (c) 페이지 비례 검토. 완료 시 .51의 재블레스 8건 진행 가능.
- PR#7613 (qo_extract_or_restrictions OR 제약 추출) — **완료(머지 c283e799d, CBRD-27171)**. 선택도 이중계상은 머지본이 PT_EXPR_INFO_OR_DERIVED 마크로 처리; 단일 term 유지(27-conjunct) 여부는 머지본에서 재확인 필요.
- CBRD-27094 히스토그램 조인 선택도 계열 브랜치 작업 — eqjoinsel 이식(10d0aa0e7, CBRD-26746 #7508)과 histogram dangling 수정(937d09feb, CBRD-27279 #7761)은 develop 에 이미 머지됨; M-L/descent_cpu 계열(PR#7622)은 미머지.
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
  검증 대상 = PR#7622 잔여 회귀 4건(9c/5c/13c/7a). 설계 참고 = 이 모듈 §2·§3의 .50 축적분 +
  PG cost_index csquared. [보드 #75]