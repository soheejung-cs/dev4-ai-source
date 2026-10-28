# src/parser

> 기준: upstream/develop 95b79e7ed (2026-08-27)

## 1. 소스 목적 및 사용처 (함수별)

SQL 파싱·분석, 클라이언트 전용(`#if !defined(SERVER_MODE)`). 파이프라인:
SQL 텍스트 → `csql_lexer.l` → `csql_grammar.y`(646KB bison) → PT_NODE 트리 →
`name_resolution.c` → `semantic_check.c` → `type_checking.c` → `xasl_generation.c` → XASL_NODE.

| 함수 | 파일 | 목적 | 주요 사용처(호출자) |
|---|---|---|---|
| `parser_create_parser` / `parser_free_parser` | parse_tree.c:1172/1253 | PARSER_CONTEXT 생성/파괴(파괴 시 parser_alloc 메모리 일괄 해제) | compat/db_vdb.c(db_open_buffer), executables/unload_schema.c |
| `parser_parse_string` (+`_with_escapes`, `_use_sys_charset`) | parse_tree_cl.c:1961/1974/1943 | SQL 문자열→PT_NODE 문장 리스트 | compat/db_vdb.c:477·4499, object/trigger_description.cpp |
| `parser_new_node` | parse_tree_cl.c:2447 | PT_NODE 할당+node_type 초기화 | 문법 액션·트리 변환 전반 |
| `parser_alloc` | parse_tree.c:954 | 파서 수명 메모리 할당 | parser 내부 전반, pt_append_string |
| `pt_append_string` | parse_tree.c:983 | 파서 수명 문자열 이어붙이기/복제 | 이름 조작·SQL 재생성 경로 |
| `parser_walk_tree` | parse_tree_cl.c:1207 | pre/post 콜백 트리 순회 | parser·optimizer 전반 (수동 재귀 대신 필수) |
| `parser_copy_tree` / `parser_free_tree` | parse_tree_cl.c:1370/1699 | 트리 복사/해제 | view_transform, xasl_generation 등 |
| `parser_append_node` | parse_tree_cl.c:3589 | next 리스트에 노드 추가 | 문법 액션·리스트 조립 전반 |
| `pt_compile` | compile.c:382 | 문장 컴파일 오케스트레이션(현재는 pt_semantic_check 래퍼) | compat/db_vdb.c(db_compile_statement_local), query/execute_schema.c |
| `pt_resolve_names` | name_resolution.c:9319 | 식별자→스키마 객체 해석 | compat/db_vdb.c, query/execute_schema.c |
| `pt_semantic_check` | semantic_check.c:12775 | 의미 분석·검증(타입 검사 포함) | pt_compile, query/execute_schema.c |
| `pt_semantic_type` | type_checking.c:19327 | 식 타입 추론·함수 시그니처 해석 | semantic_check 경로 |
| `mq_translate` | view_transform.c:9525 | 뷰 확장·질의 재작성 | compat/db_vdb.c, query/execute_statement.c |
| `parser_generate_xasl` | xasl_generation.c:23556 | PT_NODE 트리→XASL_NODE 트리 | query/execute_statement.c |

## 2. 분석 내용 (함수별)

> 항목은 함수 단위로 기술한다. 새 분석도 함수명을 앞세워 추가할 것.

### 모듈 일반

- `csql_grammar.y`는 최대급 bison 문법 — 수정에 극도 주의, bison 재생성이 느림. 문법 변경 후
  `y.output`으로 shift/reduce 충돌 확인.
- 클라이언트 측 — `THREAD_ENTRY *` 없음, 서버 측 API 사용 불가.
- `PT_NODE`는 union 기반 연결 리스트(`node_type` + `info` union + `next`) — 잘못된 `info` 멤버 접근은
  미정의 동작.
- 식별자 비교는 전부 `intl_identifier_casecmp()`(대소문자 무시, base/intl_support.c).
- **빌드/검증 관점**: **csql은 클라이언트 코드를 정적 포함**한다(ldd에 libcubridcs 없음) —
  parser/db_vdb 수정 검증 시 so 교체로는 반영 안 됨, csql 재링크 필요. cub_cas는 동적이지만 RPATH가
  빌드트리 `_install`을 가리킴.
- ✅ **리뷰 체크포인트**: `node_type`과 접근하는 `info` union 멤버가 일치하는가?
- ✅ **리뷰 체크포인트**: 식별자 비교에 `strcmp`류 대신 `intl_identifier_casecmp()`를 쓰는가?
- ✅ **리뷰 체크포인트**: 문법 변경 후 shift/reduce 충돌이 늘지 않았는가(`y.output`)?
- ✅ **리뷰 체크포인트**: 서버 전용 헤더/API 의존이 새로 생기지 않았는가?

### parser_alloc / pt_append_string (parse_tree.c)

- 파서 메모리는 `parser_alloc(parser, size)` — 파서 파괴 시 일괄 해제, **수동 해제 금지**.
  문자열 복제는 `pt_append_string()` 또는 `parser_alloc` + 복사.
- ✅ **리뷰 체크포인트**: `parser_alloc` 메모리를 free하거나, 반대로 malloc 메모리를 파서에 맡기지
  않는가?

### parser_walk_tree (parse_tree_cl.c)

- 트리 순회는 수동 재귀가 아니라 항상 `parser_walk_tree()`(pre/post 콜백).
- ✅ **리뷰 체크포인트**: 트리 순회가 `parser_walk_tree()`를 쓰는가?

### pt_compile (compile.c)

- 95b79e7ed 기준 본문은 `PT_SET_JMP_ENV` 가드 안에서 `pt_semantic_check()`를 호출하는 얇은 래퍼
  (next 링크를 떼었다 복원). 이름 해석·뷰 변환은 호출자 경로(db_vdb.c 등)에서 별도 단계로 수행된다.

### parser_print_tree — XASL 캐시 키 문자열 (parse_tree_cl.c:3103)

- **`CUSTOM_PRINT_4_SHA_COMPUTE` = `PT_CONVERT_RANGE|PT_PRINT_QUOTES|PT_PRINT_USER|PT_PRINT_HOST_VAR_COUNT|PT_PRINT_DBLINK_INFO`
  (execute_statement.c:109)이고 `PT_PRINT_HOST_VAR_COUNT` 는 캐시 키 출력에서만 쓰여 `parser_print_tree` 가 `;bind_var_cnt=N` 을 붙인다**
  (.50, 87b25579e, 2026-09-22; develop `2d925cb86` 재확인 — parse_tree_cl.c:3134-3155): `custom_print` 는 32비트 전부 사용 중
  (`enum pt_custom_print` parse_tree.h:902-967 이 `0x1`~`PT_PRINT_LOWER=1<<30`, :974 `PT_PRINT_SUPPRESS_DBLINK_PUSHED`=`0x80000000U` 는 enum
  밖 매크로) — 새 출력 플래그 비트가 없다. — 정소희(.50) 2026-10-28
- **`print_type_ambiguity` 는 호스트 변수 타입 모호성이 아니라 `pt_print_value` 의 MONETARY(통화 NULL)·미지 값 타입에서 세워진다** (.50,
  87b25579e, 2026-09-22; develop `2d925cb86` 재확인): parse_tree_cl.c:17299-17302(`DB_CURRENCY_NULL`), :17341-17344(`-- Unknown value type --`).
  세워지면 캐시 키를 만드는 준비 함수가 `cannot_prepare=1`(캐시 포기 — 예: `do_prepare_select` execute_statement.c:15393). — 정소희(.50) 2026-10-28

### pt_coerce_value_internal — 호스트 변수의 타입 강제 (type_checking.c:19607)

- **타입 검사기는 `set_host_var==0` 이면 호스트 변수를 무타입으로 보고 원하는 타입으로 강제하고, `==1` 이면 PT_VALUE 로 fallthrough 해 값의
  타입으로 판단한다** (.50, 87b25579e, 2026-09-22; develop `2d925cb86` 재확인 — `pt_coerce_value_internal` type_checking.c:19689): 값 바인드
  컴파일 플랜은 타입 의존이다. 플래그가 언제 1 인지는 src-compat §2 「do_cast_host_variables_to_expected_domain」. — 정소희(.50) 2026-10-28

### pt_coerce_expr_arguments — 비교 피연산자의 문자열 타입 (type_checking.c:5390)

- **타입체커는 `col <op> 'lit'` 에서 CHAR↔VARCHAR 를 `PT_ARE_COMPARABLE_CHAR_TYPE` 로 보고 리터럴을 컬럼 타입으로 강제변환하지 않는다**
  (.50, 6497720ec, type_checking.c:5511, 2026-09-17; develop `2d925cb86` 같은 줄, 비교 연산자 분기 :5559 "do not cast between numeric types or
  char types"): 그래서 옵티마이저가 받는 상수 DB_VALUE 의 타입은 리터럴 타입(CHAR)이지 컬럼 타입이 아니다. 호스트변수는 컬럼 타입으로
  coerce 된다(6497720ec :9601 — develop `pt_eval_expr_type` :9571·:9594). 명시 `CAST(...)` 는 `PT_EXPR_INFO_CAST_SHOULD_FOLD` 없이는 접히지 않아
  `qo_classify` 가 `PC_OTHER` → 히스토그램 경로를 안 탄다(1/NDV 폴백). — 정소희(.50) 2026-10-28

### pt_check_cast_op — CAST 허용 표 (semantic_check.c:1050)

- **`CAST(<date 컬럼> AS INT)` 는 실행이 아니라 시맨틱 검사에서 거부된다** (.52, `a7a1db84b`, 2026-09-16 실측; develop `2d925cb86` 정적
  재확인 — `pt_check_cast_op ()` 의 DATE → INTEGER·BIGINT·FLOAT·DOUBLE·SMALLINT·MONETARY·NUMERIC … `PT_CAST_INVALID`(:1159-1178) →
  `MSGCAT_SEMANTIC_CANT_COERCE_TO`(:1399)): "Semantic: Cannot coerce [dba.hc].dt to type integer"(-494), prepare 자체가 실패. 런타임 변환 오류를
  시험하려면 `CAST(<varchar 컬럼> AS INT)`(-181)를 쓴다. `1/0` 리터럴도 파서가 접으므로 `1/?` 에 0 바인드. ✅ "실행 시 오류 순서" TC 가 시맨틱
  오류로 통과하는 것처럼 보이면 이 함정. — 정소희(.50) 2026-10-28

### mq_rewrite_order_dependent_query / pt_has_analytic — 세션 변수 대입의 순서 의존 재작성 (view_transform.c:15579, parser_support.c:3428)

- **ORDER BY + SELECT 목록의 세션 변수 대입은 `mq_rewrite_order_dependent_query()`(view_transform.c:15579) 가 정렬 파생 테이블 `dt_sort` 위로
  그 항목을 올린다** (.52, 58b49b39f, 2026-10-12; develop `2d925cb86` 재확인): `mq_translate_select ()` 가 ORDER BY 가 있을 때 select 목록을
  훑어(:6978-7012) 판정 `mq_is_order_dependent_node()`(:15238)는 PT_DEFINE_VARIABLE, 표시 `mq_mark_order_dependent_nodes()`(:15310)는
  DEFINE/EVALUATE 를 찾고 함수는 `arg_list` 만 걷는다(분석 함수의 PARTITION/ORDER 키는 안 봄). 대상 항목이 ORDER BY 위치에 직접 있으면
  올리지 않는다. `e7b1605f5`(CBRD-27503) 이후 두 함수는 분석 함수 노드에서 멈추고 순서 독립으로 본다 — 분석 함수는 파생 테이블에 남고, 곁에
  있는 대입(`sum(i) over () + (@u := i)`)만 올라간다. — 정소희(.50) 2026-10-28
- **`pt_has_analytic()` 은 SELECT 에 `PT_SELECT_INFO_HAS_ANALYTIC` 를 캐시한다** (.52, 58b49b39f, 2026-10-12; develop `2d925cb86` 재확인 —
  parser_support.c:3428): 재작성이 분석 함수를 다른 SELECT 로 옮겨도 원래 SELECT 의 플래그는 남는다 → `pt_to_buildlist_proc` 가 분석 경로에
  들어가 head_list NULL·a_eval_list NULL. `e7b1605f5`(CBRD-27503 PR#8141) 는 분석 노드를 재작성에서 빼고(위 항목) a_eval_list NULL 을 내부
  오류로 막는다(xasl_generation.c:17280) — 플래그 캐시 자체는 그대로다. — 정소희(.50) 2026-10-28

## 3. 예비 이슈 사항

> 미수정 버그·의심·문서 정정 후보·구조적 한계. 해소되면 삭제가 아니라 "해소됨(커밋/PR)"로 갱신.

- **host variable 이 섞인 다분기 OR 에서 `pt_cnf()` 의 공통항 추출이 상수 판과 다르게 동작한다** — **미수정**(별건 후보, develop `2d925cb86`
  재확인 2026-10-28 — 정적: src/parser/cnf.c 는 2026-09-01 이후 변경 없음) (.52, 9ee8bac8b·27171-off 빌드 동일, 2026-09-28): Q19 형태(3분기,
  brand·quantity 를 `?`)에서 `(shipmode and shipinstruct and ((br1) or (br2))) or (br3)` 로 분기 1·2 만 묶이고 `p_partkey = l_partkey` 조인
  에지가 OR 안에 남는다; 상수 판은 세 분기의 조인 에지·shipmode·shipinstruct 를 모두 빼낸다. 그 결과 `qo_extract_or_restrictions()` 가 part
  전용 conjunct 를 찾지 못해(첫 분기의 conjunct 가 중첩 OR) part 제약이 추출되지 않고 lineitem 제약만 추출된다. CBRD-27171 이전
  빌드에서는 nl-join sscan×sscan(cost 26,205,655)으로 EXECUTE 가 10분 내 끝나지 않고, develop 은 53.9 s(part 285,560,000행). 재현
  `projects/CBRD-27171/testcases-20260928/02_tc_hv.sql`. — 정소희(.50) 2026-10-28
- **`select p, sum(@u := i) from tm group by p order by p` 가 한 행만 돌려준다** — **미수정** (develop `2d925cb86` 재확인 2026-10-28 — 정적:
  `e7b1605f5` 이후 순서 의존 재작성 함수에 변경 없음, 그 커밋 설명도 범위 밖으로 명시) (.52, develop 07aec2c5c·58b49b39f, 2026-10-12): GROUP BY
  만 있으면 두 행 정답. 같은 순서 의존 재작성이 비분석 집계를 GROUP BY 위로 올리는 것으로 추정(미확인). 재현
  `claude-workspace/projects/CBRD-27503/repro/groupby_preexisting.sql`. — 정소희(.50) 2026-10-28

## 4. 진행중인 작업

> 각 컨테이너가 자기 소절을 직접 관리한다. 완료되면 지우지 말고 "완료(PR/커밋)"로 갱신.

### .50
- (해당 없음 또는 미기입)
### .51
- (해당 없음 또는 미기입)
### .52
- (해당 없음 또는 미기입)
