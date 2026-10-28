# src/compat

> 기준: upstream/develop 95b79e7ed (2026-08-27)

## 1. 소스 목적 및 사용처 (함수별)

공개 API 층 — 클라이언트/서버를 잇는 `db_*` API와 `DB_VALUE`(union 컨테이너, `dbtype_def.h`).
`db_macro.c`/`dbtype_function.i`(생성·접근·정리), `db_vdb.c`(세션·컴파일·실행), `db_set.c`, `db_obj.c`,
`db_date.c`, `db_json.cpp`, `db_elo.c`(LOB), `dbi_compat.h`(클라이언트 노출 에러 코드 —
`error_code.h` 미러). 접두사: `db_`(공개 API), `pr_`(내부 primitive).

| 함수 | 파일 | 목적 | 주요 사용처(호출자) |
|---|---|---|---|
| `db_make_null` / `db_make_int` | dbtype_function.i:1132/1152 | 스칼라 DB_VALUE 생성 | 전 모듈(query, object, broker …) |
| `db_make_string` | dbtype_function.i:1902 | 문자열 DB_VALUE 생성 — **참조만**(복사 안 함) | 전 모듈; 상수·수명 보장 버퍼용 |
| `db_make_string_copy` | dbtype_function.i:1935 | 문자열 복사본으로 생성 — need_clear=true | 호출측 버퍼가 먼저 죽는 경로 |
| `db_make_varchar` | dbtype_function.i:1792 | 길이·코드셋 지정 문자열 생성 | 카탈로그·질의 결과 조립 |
| `db_get_int` / `db_get_string` | dbtype_function.i:156/207 | DB_VALUE 값 접근 | 전 모듈 |
| `db_value_domain_init` | db_macro.c:155 | 타입·정밀도로 DB_VALUE 초기화 | db_make_* 내부, loaddb, 질의 처리 |
| `db_value_clone` | db_macro.c:1460 | 깊은 복사(대상은 need_clear 소유) | 값 보존이 필요한 경로 |
| `db_value_clear` | db_macro.c:1484 | 내부 데이터 해제 — `pr_clear_value()` 위임 | broker/cas_execute.c 등 클라 전반 |
| `db_value_free` | db_macro.c:1506 | 내부 데이터+컨테이너 해제(`pr_free_ext_value`) | 힙 할당된 DB_VALUE 정리 |
| `db_open_buffer` | db_vdb.c:494 | SQL 문자열→DB_SESSION(내부 parser_parse_string 계열) | executables/csql.c, broker/cas_execute.c, base/tz_compile.c |
| `db_compile_statement` | db_vdb.c:1140 | 세션 문장 컴파일(pt_compile→XASL 생성 경로) | csql.c, cas_execute.c |
| `db_execute_statement` | db_vdb.c:3997 | 컴파일된 문장 실행 | csql.c, cas_function.c, loaddb/load_db.c |
| `db_date_encode` | db_date.c:278 | 연/월/일→DB_DATE 인코딩 | query/arithmetic.c, parser/xasl_generation.c, broker |

## 2. 분석 내용 (함수별)

> 항목은 함수 단위로 기술한다. 새 분석도 함수명을 앞세워 추가할 것.

### 모듈 일반

- `need_clear` 플래그: 세팅돼 있으면 `db_value_clear()`가 데이터를 해제, 아니면 빌린(borrowed) 데이터.
- `db_make_*()` 중 일부는 데이터를 복사하고 일부는 참조만 — **타입별로 확인 필요**.
- `DB_VALUE`는 클라이언트·서버 양쪽에서 쓰이지만 접근 패턴이 다르다.
- LOB 값은 인라인이 아닌 외부 저장(`db_elo.c`) — 특별 처리 필요.
- `dbi_compat.h`와 `error_code.h`는 항상 동기화 — 클라이언트 노출 에러는 양쪽에 추가.
- ✅ **리뷰 체크포인트**: 생성한 DB_VALUE의 소유권(복사 vs 참조)이 해당 `db_make_*()`의 실제 동작과
  일치하는가?
- ✅ **리뷰 체크포인트**: `need_clear`가 빌린 데이터에 잘못 세팅되거나, 소유 데이터에 누락되지 않는가?
- ✅ **리뷰 체크포인트**: 클라이언트 노출 에러가 `dbi_compat.h`에도 추가됐는가?

### db_make_string / db_make_string_copy (dbtype_function.i)

- `db_make_string`은 `strlen` 후 `db_make_db_char`로 **포인터만 저장**(need_clear 미설정) —
  호출자 버퍼 수명이 값 수명보다 길어야 한다. `db_make_string_copy`는 `db_private_strdup` 후
  `db_make_string` + need_clear=true(함수 주석 명시) — 복사본 소유.
- **`db_make_varchar()` 등 `db_make_<type>` 문자열 계열은 버퍼를 복사하지 않고 빌린다** (.50, `051d5f61d`, 2026-09-18; develop `2d925cb86`
  재확인): `db_make_varchar()`(dbtype_function.i:1792) → `db_make_db_char()`(:1095)가 `value->data.ch.medium.buf = str` 로 호출자의 포인터를
  그대로 넣고 `value->need_clear = false` 로 둔다 — `db_make_char`·`db_make_string`·`db_make_bit`/`db_make_varbit` 도 같은 함수를 거친다(위 줄의
  `db_make_string` 과 같은 계약). 즉 DB_VALUE 의 수명은 원본 버퍼의 수명에 묶인다 — 지역 버퍼를 가리키게 만들었으면 그 버퍼가 살아 있는 동안
  소비를 끝내야 한다. 복사가 필요하면 호출자가 `std::string`·`db_private_alloc` 으로 따로 뜨거나 `db_make_string_copy` 를 쓴다. 이 계약을
  반대로 적은 주석이 있었다(`fd030f826` CBRD-27251 에서 정정). — 정소희(.50) 2026-10-28

### db_value_clear / db_value_free (db_macro.c)

- 문자열·셋·JSON 등 non-trivial DB_VALUE는 사용 후 반드시 `db_value_clear()` — 서버 측 별칭이자
  실체는 `pr_clear_value()`(object/object_primitive.c; 내부 캐베트는 src-object.md 참조).
- `db_value_free()`는 `pr_free_ext_value()`로 **컨테이너 자체까지 해제** — 스택 DB_VALUE에 쓰면 안 됨.
- ✅ **리뷰 체크포인트**: non-trivial 값의 모든 경로(에러 포함)에서 `db_value_clear()`가 호출되는가?

### db_open_buffer / db_compile_statement / db_execute_statement (db_vdb.c)

- 클라이언트 문장 처리 3단: `db_open_buffer`(파싱, 내부 `parser_parse_string_with_escapes` L477) →
  `db_compile_statement`(의미 분석·XASL 생성, `db_compile_statement_local` L820) →
  `db_execute_statement`(실행). csql·CAS가 이 경로를 그대로 쓴다.

### do_cast_host_variables_to_expected_domain / `parser->flag.set_host_var` (db_vdb.c:3806)

- **`parser->flag.set_host_var` 는 바인드 값을 기대 도메인으로 캐스팅한 뒤에만 1 이 된다 — XASL 캐시 키를 만드는 시점에 PREPARE·SELECT
  compile-first 는 0, peek 재플랜·bind-first(DML 등)는 1** (.50, 87b25579e, 2026-09-22; develop `2d925cb86` 재확인): 1 로 세우는 곳은
  `do_cast_host_variables_to_expected_domain()`(db_vdb.c:3806, :3847)와 CAS 의 `db_push_values()` 가 부르는 `pt_set_host_variables()`
  (parse_dbi.c:3072, :3136). `do_recompile_and_execute_prepared_statement()` 의 SELECT compile-first 는 `is_subsession_for_prepared=false` 로
  컴파일 중 캐스트(`db_compile_statement` 의 서브세션 블록, db_vdb.c:1642)를 피하고(:4338), bind-first(DML, `bind_before_compile`, RECOMPILE
  — :4308)는 그 블록이 캐스트해 1 로 컴파일한다. 값 바인드 컴파일과 값 없는 컴파일을 이 플래그로 구분할 수 있다. 캐스팅이 타입을 기대
  도메인으로 정규화하므로(UNKNOWN/ENUM 도메인 :3824·CHAR 도메인의 VARCHAR 값 :3831·NULL 만 예외) 키 시점의 바인드 타입은 대부분 기대 도메인과
  같다. — 정소희(.50) 2026-10-28

### do_replan_statement_with_bind_peek / do_replan_statement_internal (db_vdb.c:4095/4108)

- **peek 재플랜은 `xasl_id` 해제 + `recompile=1` 로 `do_prepare_statement` 를 다시 돌려 키를 재계산하고 같은 sha1 엔트리를 교체한다** (.50,
  87b25579e, 2026-09-22; develop `2d925cb86` 재확인 — `do_replan_statement_with_bind_peek ()` 가 `do_replan_statement_internal (…,
  force_compile=true)` 를 부르고, 그 머리 주석 :4100-4106 이 "compile and replace the cache entry"): 그래서 첫 커넥션의 값-고정 플랜을 다른
  커넥션이 물려받는다(`plan_cache_bind_sensitivity` OFF 의 의미). 바인드 지문 `histogram_bind_fingerprint`(histogram_cl.cpp:2877)는 EQ
  `sel×1e12`·범위 `sel×100` 양자화 성분을 접으며 재플랜 판정에만 쓰이고 캐시 키에는 없었다 **(develop `620ceaf6a` 이전)**. **바뀐 내용
  (`620ceaf6a`, CBRD-27490 #8013, 2026-10-21)**: 지문은 술어마다 "예상 스캔 행 수" 를 담는 벡터가 되었고(밴드 비교 `BIND_WATCH_BAND` 1.5배·
  힌트 `BIND_WATCH_HINT_BAND` 1.1배, 1,000행 바닥 — histogram_cl.hpp:181-189), 대상 선정(실 클래스 spec 둘 이상 + MCV 컬럼 + 유니크 키 고정
  없음)을 통과한 SELECT·서버측 UPDATE/DELETE 는 `plan_cache_bind_variants`(기본 5)만큼 플랜 변형을 두며 변형 키를 해시 텍스트 뒤에 붙여
  (`do_append_bind_variant_key ()` execute_statement.c:15279) 변형마다 별도 캐시 엔트리를 쓴다. 힌트(`BIND_SENSITIVE`/
  `plan_cache_bind_sensitivity`) 경로는 여전히 제자리 재플랜이다(histogram_cl.hpp:124). — 정소희(.50) 2026-10-28

### SQL PREPARE/EXECUTE 의 kept tree — db_prepared_tree_register / do_reexecute_prepared_statement_from_kept_tree (db_vdb.c:861/4188)

- **`BIND_SENSITIVE`/`plan_cache_bind_sensitivity` 의 재플랜 검사는 SQL PREPARE/EXECUTE 에서 kept tree 위에서만 돌아, csql 에서 EXECUTE 를
  줄마다 따로 치면(입력 버퍼 = DB_SESSION 이 줄마다 새로 생김) 관측되지 않고 한 줄에 이어 쓰면 관측된다** (.52, `c76ac823d`, 2026-09-22 —
  `a = ?` 대조군; develop `2d925cb86` 정적 재확인): kept tree 는 소유 DB_SESSION 의 `kept_trees` 목록에 매달려 세션이 닫히면 함께 풀리고
  (등록부 주석 db_vdb.c:746-760, `db_prepared_tree_register ()` :861, 첫 실행 뒤 등록 :4418), 나중 EXECUTE 는 `db_prepared_tree_lookup ()`
  (:2715) → `do_reexecute_prepared_statement_from_kept_tree ()`(:4188)에서만 검사한다(`db_execute_and_keep_statement_local ()` 의 같은 검사는
  `set_host_var` 로 막혀 kept tree 에선 안 돈다 — :4226-4230 주석). kept tree 범위 확대는 CBRD-27231(develop 미반영). CTP(JDBC 문장별 실행)
  에서도 관측 불가 — CBRD-26959·27143 TC 가 첫 peek 만 검증하는 이유. — 정소희(.50) 2026-10-28

### show trace 의 `Query Plan:` 블록 — plan_trace (query_planner.c, execute_statement.c)

- **`show trace` 의 `Query Plan:` 블록은 그 세션 파서가 컴파일/재플랜하며 `plan_trace` 를 남긴 실행에만 나타난다 — 첫 peek 재플랜과 한 줄
  형태의 kept-tree 재플랜에서 보이고, 캐시 히트 실행에서는 없다** (.52, `c76ac823d`, 2026-09-22; develop `2d925cb86` 정적 재확인): 플랜 생성 때
  `qo_top_plan_print_json/text ()` 가 `parser->plan_trace` 에 쌓고(query_planner.c:15848·16201) `do_send_plan_trace_to_session ()`
  (execute_statement.c:21414)이 세션 trace 로 보낸다. 재플랜은 마커 컴파일이 쌓은 plan_trace 를 버리고 실제로 도는 플랜만 남긴다
  (`do_replan_statement_internal ()` db_vdb.c:4133-4159). TC 에서 "재플랜이 일어났나" 의 판정 신호로 쓸 수 있다. 한 줄 형태의 첫
  `show trace` 가 `TABLE SCAN (dual)`(`trace_stats()` 자신의 플랜)을 보이는 것은 표기 잡음. — 정소희(.50) 2026-10-28

## 3. 예비 이슈 사항

> 미수정 버그·의심·문서 정정 후보·구조적 한계. 해소되면 삭제가 아니라 "해소됨(커밋/PR)"로 갱신.

- **히스토그램 없는 컬럼의 `col = ?` 같은, 히스토그램으로 가격 매길 술어가 없는 prepared SELECT 가 `HV_PRED_PLAN_UNPEEKED` 를 달면 kept tree
  가 등록되지 않아 SQL EXECUTE 마다 새 서브세션에서 다시 파싱·컴파일된다** — **미수정** (develop `2d925cb86` 재확인 2026-10-28 — 정적) (.52,
  `c76ac823d` strace 실측 113 vs 64 왕복, 2026-09-22): 표시를 다는 조건(xasl_generation.c:18556-18565 — 값 없이 컴파일 + 호스트 변수
  + `histogram_stmt_has_hv_predicate ()`)의 `hv_pred_walk ()`(histogram_cl.cpp:3020)가 히스토그램 존재를 보지 않는 구조 검사이고, `do_get_prepared_statement_info ()` 는 그 표시가 있으면 XASL_ID 를 무조건 비운다
  (db_vdb.c:3735). `do_recompile_and_execute_prepared_statement ()` 의 판정은 가격 매길 술어가 없어(`histogram_get_total_rows ()` 실패 →
  `bind_term_vector ()` 0개) `BIND_WATCH_STOP`(:293)이라 재플랜도 kept tree 등록도 없이 끝나고(:4403·:4418), 캐시의 마커 플랜은 표시를 그대로
  지녀 다음 EXECUTE 도 같은 길을 탄다. 재컴파일은 trace·`optimization level 513` 덤프(서브세션 컴파일은 덤프 안 함)·`cubrid statdump`(카운터
  미갱신)로는 안 보이고 strace 왕복 수로만 관측됐다(`projects/CBRD-27143/repro/g2_strace_count.md`). 고치는 안: `hv_pred_walk ()` 가 후보
  컬럼의 히스토그램 존재를 함께 요구(열린 PR#8006 `1d5858374`, develop 미반영). — 정소희(.50) 2026-10-28
- **한 줄 형태의 kept-tree 경로에서 `plan_cache_bind_sensitivity` OFF 인데도 두 번째 EXECUTE 가 한 번 더 재플랜되고(값에 맞춰 플랜이 바뀜)
  세 번째부터 유지된다 — EQ 술어** — **미수정(재확인 못 함)** (develop `2d925cb86` 정적: 추정 경로는 남아 있으나 `620ceaf6a` 가 이 경로를 크게
  바꿔 동적 재확인 필요) (.52, `c76ac823d`, 2026-09-22): 재현 `projects/CBRD-27143/repro/oneline_off.sql`. 추정 원인: prepared 정보의 마커
  XASL 이 `HV_PRED_PLAN_UNPEEKED` 를 계속 지녀 `do_get_prepared_statement_info()` 가 xasl_id 를 비우고(db_vdb.c:3735) `do_recompile` →
  `do_reexecute_prepared_statement_from_kept_tree(force_replan=true)`(:2727, :4188). "OFF = 첫값 플랜 고정" 계약과 어긋남. CBRD-27231 과 함께
  볼 것. — 정소희(.50) 2026-10-28

## 4. 진행중인 작업

> 각 컨테이너가 자기 소절을 직접 관리한다. 완료되면 지우지 말고 "완료(PR/커밋)"로 갱신.

### .50
- (해당 없음 또는 미기입)
### .51
- (해당 없음 또는 미기입)
### .52
- (해당 없음 또는 미기입)
