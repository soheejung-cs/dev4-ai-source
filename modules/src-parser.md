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

### pt_to_insert_xasl / pt_append_assignment_references — ODKU 가 읽는 소스 컬럼 (xasl_generation.c)

- **ODKU 가 읽는 소스 컬럼은 SELECT 목록의 숨은 컬럼이 된다** (.51, develop `1684945ed`, 2026-11-02): `pt_to_insert_xasl ()` 이 aptr XASL 을 만들기 전에 `pt_append_assignment_references ()` 로 붙인다(trace rewritten query `select max(s.g)+1, s.c from … where s.g=?`). 사용자가 쓰면 "not single valued" 로 거절되는 "집계 옆 비집계 컬럼" 이 여기서만 생긴다. 실행기가 그 값을 어디서 읽는지는 src-query §2 「qexec_execute_mainblock」, 채우지 않는 경로는 src-query §3(CBRD-27870). — 정소희(.50) 2026-11-03
- **집계 옆 숨은 컬럼을 만드는 두 번째 재작성: SELECT 목록 상관 서브쿼리** (.51, develop `1684945ed`, 비교 `ad7a255c5`, PR#8364 `756c19e28`, 2026-11-03): 집계 SELECT 의 SELECT 목록에 상관 서브쿼리가 있으면 `mq_translate_local ()` 이(`mq_has_class_methods_corr_subqueries ()`) `mq_rewrite_aggregate_as_derived ()` 로 집계 부분을 파생 테이블로 만들고, 서브쿼리가 읽는 소스 컬럼을 그 파생 테이블의 숨은 컬럼으로 싣는다(rewritten query `select a_?, ?, (select count(a_?) from dual dual) from (select count(...), t?.a from t? t? where ...) t? (a_?, a_?)`). 의미 검사를 통과하는 것은 외부 컬럼을 집계로 감싼 서브쿼리뿐이다(`(select max(s3.c))`, `(select count(a))`); `(select s3.c from db_root)` 와 분석 함수의 비집계 컬럼(`first_value(c) over ()`)은 "not single valued". 실측(release SA): `SELECT COUNT(*), (SELECT MAX(s3.c)) FROM s3 WHERE g = 2`(s3 = (1,'g1',1),(2,'g2',2),(1,'g1b',3))가 `ad7a255c5` 1·'g2', develop 1·NULL(페이지 배치), `756c19e28` 1·'g2'; `(SELECT COUNT(s3.c))` 는 1 / 0 / 1. — 정소희(.51) 2026-11-03, 환류 정소희(.52) 2026-11-03

### pt_to_update_xasl / pt_to_delete_xasl — UPDATE·DELETE 의 MVCC 재평가는 꺼져 있다 (xasl_generation.c)

- **UPDATE·DELETE 의 MVCC 재평가는 XASL 생성에서 무조건 꺼져 있다 — 재평가 경로의 PEEK(src-transaction §3)·락 대기 UPDATE 가 재평가 대입을 안 탐(src-query §2)의 이유, 그 경로는 지금 죽은 코드** (.52, 226352283 · PR#8378 head f3bac6bdc debug, 2026-11-05, 정적 + gdb): `pt_to_update_xasl ()`(xasl_generation.c ~26377)·`pt_to_delete_xasl ()`(~25624)가 "These two lines disable reevaluation on UPDATE. To activate it just remove them" 아래에서 `PT_SELECT_INFO_MVCC_LOCK_NEEDED` 를 켜고 `abort_reevaluation = true` — 모든 spec 의 `PT_SPEC_FLAG_MVCC_COND_REEV`·`PT_SPEC_FLAG_MVCC_ASSIGN_REEV` 를 지우고 갱신 대상 spec 에 FOR UPDATE 플래그를 붙여 select 단계에서 잠근다. MERGE 갱신 질의(`pt_to_merge_update_query ()`)도 `MVCC_LOCK_NEEDED` + GROUP BY. 두 클래스를 고쳐 잠금 정책이 `LOCATOR_LOCK_AT_FORCE` 인 `update t1, t3, t2 set t1.v = t2.w, t3.y = t2.w …` 와 한 클래스 `update t1, t2 set …` 를 세션 A 의 미커밋 갱신 뒤에 돌려도 `locator_mvcc_reev_cond_assigns`(:13820)·`locator_mvcc_reeval_scan_filters`(:13946) 입구 0회(gdb). PR#8378 의 codex 지적(빌린 문자열이 놓인 페이지를 가리킴)은 이 때문에 도달 불가 — 재평가를 다시 켜면 `locator_mvcc_reev_cond_assigns ()` 가 우변 문자열을 복사해 넘겨야 한다. **미수정**(현재 동작 기록). — 정소희(.52) 2026-11-09

### pt_bind_names / pt_get_attr_list_of_derived_table — 파생 테이블 열의 형과 위치 (name_resolution.c)

- **이름 해석은 파생 테이블을 접기 없이 형 검사하고 그 형으로 열을 정한다** (.51, develop `953e83256`, 2026-11-06): `pt_bind_names ()`(name_resolution.c:1358-1361)가 `sc_info->donot_fold = true` 로 `pt_semantic_type ()` → `pt_bind_spec_attrs ()` 가 as_attr_list 형을 선택 목록 형으로. 바깥 질의의 이름은 이 형에 묶인다. 뒤 의미 검사(접기 켬)가 항목 형을 바꿔도 맞추지 않는다. CTE 는 `pt_bind_names_in_cte ()` 가 접은 뒤 형으로, 뷰는 `mq_set_types ()`(view_transform.c:8739)가 열 형으로 CAST 해 어긋나지 않는다. 어긋나는 사례는 §3(CBRD-27962). — 정소희(.52) 2026-11-09
- **파생 테이블 열은 부질의 선택 목록에 위치로 묶인다 — 숨은 항목 포함** (.51, develop `953e83256`, 2026-11-06): XASL 은 `spec.as_attr_list` 의 i 번째를 부질의 리스트 파일의 i 번째 열(숨은 열 포함)로 읽는다(`pt_to_position_regu_variable_list ()` xasl_generation.c:16075 계열). 사용자가 쓴 파생 테이블은 이름 해석(`pt_get_attr_list_of_derived_table ()` name_resolution.c:11702)이 숨은 항목이 붙기 전에 열을 만들고, ORDER BY 숨은 항목은 모두 끝에 덧붙으므로(semantic_check.c:15520, view_transform.c:2714·16626) 마지막 열 뒤로 빠진다. 반면 세션 변수 대입 + 선택 목록 밖 열의 ORDER BY 를 바꾸는 `mq_rewrite_order_dependent_query ()`(view_transform.c:15943)의 `dt_sort` 는 순서 무관 항목(숨은 정렬 항목 포함)마다 as_attr 를 만들고 뒤에 `sx` 항목을 덧붙여, **숨은 항목이 앞에 오고 그 항목에도 열이 있다**. 선택 목록과 as_attr_list 를 짝짓는 코드가 숨은 항목을 건너뛰면 이 꼴에서 짝이 밀린다(PR#8435 첫 커밋 — 첫 CI 의 `bug_bts_17424`·`cbrd_27510/03_session_variable_types` 가 `-181`, NUMERIC 은 조용히 반올림; `cfdef8ea8` 에서 고침). — 정소희(.52) 2026-11-09

### stats_option_list — `UPDATE STATISTICS` 옵션 문법 (csql_grammar.y)

- **UPDATE STATISTICS 의 옵션은 WITH 하나 뒤 쉼표 목록이다** (.51, develop `69ffb9aaf`, 2026-11-05): `with fullscan, no histogram`(csql_grammar.y `stats_option_list`). `with fullscan with no histogram` 은 문법 오류(-493). 같은 옵션 반복·`NO HISTOGRAM`+`DROP HISTOGRAM` 은 0x10 독 플래그로 거부. — 정소희(.52) 2026-11-09

### 환류 2026-11-18 — 대기소(staging)에서 옮긴 사실
- **[src-parser §2] `/*+ index (t idx) */` 는 CUBRID 힌트가 아니다 — 파서가 오류 없이 버린다** (.52, develop `6a54287e7`, 2026-11-17): 인덱스를 고르려면 `USING INDEX idx` 절(또는 `INDEX_SS` 등 정해진 힌트)을 쓴다. `USE_IDX` 는 인덱스 조인 힌트다(parse_tree.h `PT_HINT_USE_IDX`). 측정에서 이 꼴의 질의가 배치 전체 스캔이었다(경로 확인 claude-workspace `projects/CBRD-27843/repro/review2/t1_path.summary.txt`). — 정소희(.52 환류) 2026-11-18
- **[src-parser §2] PR#8590 의 CNF 걷기는 AND·OR 노드에서만 피연산자로 내려가고 그 밖은 `PT_LIST_WALK` 로 원자째 둔다 — AND·OR 에서 `PT_CONTINUE_WALK` 로 되돌리는 줄이 필요하고, 그 줄의 효과는 세 단계 중첩에서만 드러난다** (.52, PR#8590 `d2f562e58`, 2026-11-18): 앞 형제 원자가 남긴 `PT_LIST_WALK` 를 `pt_walk_private ()` 가 다음 형제의 pre 까지 가져가므로 되돌림이 없으면 뒤 AND 아래로 못 내려간다. 다만 걷지 않은 노드에도 post 가 불려 두 단계 꼴(`x = 1 and (y = 1 and z = 1)`)은 post 만으로 목록이 되어 차이가 없다 — `x = 1 and (y = 1 and (z = 1 and w = 1))` 처럼 걷지 않은 AND 아래에 AND 가 있어야 4항 대신 3항이 된다. 단위 suite dev4 `unit/parser/cnf.atom_whole`(head 12/12, base 5/12, 되돌림 제거 변이는 C2c·C2d·C2f 실패). `count_and_or ()` 도 원자를 1 로 세어 모드 판정과 맞는다. 머지 전 — PR#8590. — 정소희(.52 환류) 2026-11-18
- **[parser §2] `parser_walk_tree ()` 는 pre 가 PT_LIST_WALK 를 준 노드에도 post 를 부른다 — PT_LIST_WALK 는 그 노드의 자식으로 내려가는 것만 막고(or_next·next 는 걷는다), 남긴 값은 다음 형제의 pre 까지 이어진다** (.52, 41ca53ce7·c8e8d4f7f, 2026-11-17): `pt_walk_private ()`(parse_tree_cl.c) — pre → 자식(CONTINUE/LEAF 일 때만) → or_next(CONTINUE/LEAF/LIST) → next(CONTINUE/LIST) → `walk->continue_walk = save_continue` → post. `pt_eval_type_pre ()` 는 들어오자마자 PT_CONTINUE_WALK 로 되돌리지만 `pt_fold_constants_pre ()` 는 되돌리지 않는다(F_BENCHMARK 의 PT_LIST_WALK 는 `pt_fold_constants_post ()` 가 되돌린다). 그래서 "질의 노드는 건너뛴다" 를 pre 의 PT_LIST_WALK 로만 하면 post 인 `pt_eval_type ()` 의 PT_SELECT 갈래(`pt_where_type ()`)는 그대로 돈다. — 정소희(.52 환류) 2026-11-18
- **[parser §2] Oracle 식 `(+)` 항이 ON 으로 가는 조건은 CNF 항 머리의 표시뿐이다** (.52, c8e8d4f7f, 2026-11-17): `pt_bind_names ()` 는 `PT_SELECT_INFO_ORACLE_OUTER` 일 때만 WHERE 를 `pt_cnf_where ()` 로 바꾸고(name_resolution.c:2464), 항의 머리 노드에 (+) 표시가 있을 때만 ON 으로 옮긴다(2484-2495) — 머리가 표시 없는 통째 트리면 or_next 의 (+) 갈래가 있어도 WHERE 에 남는다. — 정소희(.52 환류) 2026-11-18

### 환류 2026-11-20 — 대기소(staging)에서 옮긴 사실
- **[src-parser §2] `mq_rewrite_query_as_derived ()`(view_transform.c) 는 넘긴 질의를 `parser_copy_tree ()` 로 복사해 파생 표에 넣고 원본은 건드리지 않는다(id 만 옮김) — 원본 해제는 호출자 몫** (.50, PR#8489 `0416d6596`, 2026-11-18): `copy_node_in_tree_pre ()` 가 PT_VALUE 의 DB_VALUE·XASL_ID 를 깊게 복제하므로 원본 해제가 복사본을 망가뜨리지 않는다 [PR#8489 `23fb540d8` 에서 `pt_fold_union_as_derived ()` 가 원본 해제]. — 정소희(.51 환류) 2026-11-20

### pt_coerce_expr_arguments — 집합 피연산자의 원소 타입을 식 노드에 올린다 (type_checking.c:5907)
- 두 피연산자의 공통 타입이 집합이면 `pt_propagate_types ()` 로 원소 `data_type` 들을 식 노드의 `data_type` 으로 올린다 — 결과가 논리값인 비교(`{…} = {…}`)에도. 집합 아닌 노드에 `data_type` 이 있으면 `pt_node_to_db_domain ()` 은 `type_enum`(LOGICAL)이 아니라 그 `data_type` 으로 도메인을 만든다(parse_dbi.c:2324) — 결과 열의 질의 타입이 INTEGER 인데 도메인은 원소의 CHAR 가 된다. 원소 콜레이션이 바인드가 정하는 ENFORCE 면 `db_cp_query_type_helper ()` 의 assert(db_query.c:1483)로 debug 클라이언트가 멈춘다(`{1, NVL (?, 'x')} = {1, 'zz'}`). develop release 는 CBRD-28066(-1383)이 먼저. 미수정(PR#8625 5d4d00006 이 논리값 결과면 올리지 않게). (.50, develop de4bb116e, 2026-11-20)
- 타입 검사는 MAYBE 원소(`?`, `- ?`)를 집합의 원소 도메인 목록에서 빼지만 그 값은 집합에 넣는다 — 원소 도메인이 하나 남으면 값이 도메인 표시 없이 저장돼 다른 타입으로 읽힌다(`SET{?, 1}` 에 2.5 → `{1, 67240217}`, `SET (SELECT c0, (- ?))` 크래시). 미수정(PR#8625 594d76feb: MAYBE 피연산자면 원소 도메인을 두지 않음). (.50, develop de4bb116e, 2026-11-20)
- ✅ 리뷰: 집합 도메인을 다루는 PR 은 MAYBE 원소·부질의 집합(F_TABLE_*, 피연산자가 부질의 하나)·결과가 논리값인 집합 비교를 따로 본다.

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
- **[미수정 — develop 선재(CBRD-25984 PR#6466 리뷰에서 발견)] MRO + WHERE 에만 있는 함수식 + 비커버링이면 XASL 생성이 assert 한다** (.51, 4e389935d, 2026-11-04):
  - `pt_ordbynum_to_key_limit_multiple_ranges ()`(xasl_generation.c:29248)의 `assert (0)`(29318)에서 debug 가 플랜 출력 전에 abort 한다.
  - 실측(debug SA): `(i, j, sqrt(d), k)` 에 `select j, k from t where i in (1, 2) and sqrt(d) > 0 using index idx(+) order by j limit 5`. develop 은 힌트가 없어도, PR#6466 `d7ce3af72` 는 `NO_COVERING_IDX` 일 때 abort 한다. release 동작은 보지 않았다.
  - **미수정**(develop 선재) — PR#6466 머지본 `21b58704d`(2026-11-10)에서의 동작은 미확인(리뷰 헤드 `d7ce3af72` 는 `NO_COVERING_IDX` 일 때만 abort). 재현 claude-workspace `projects/CBRD-25984/repro/MRO-c` ④. — 정소희(.52) 2026-11-09, 머지 반영 2026-11-10
- **[계약 — develop 은 지킴] `pt_split_join_preds ()` 는 WHERE 목록이 완전한 CNF 라고 가정한다** (.52, develop `99fa309ca` 정적 + PR#8375 head `8831911fb` 동적, 2026-11-06):
  - parser_support.c:2918-2920 의 assert("It is either fully CNF or not at all"). `next` 를 가진 PT_OR 원소(통째로 둔 OR-of-AND 뒤에 다른 conjunct)가 계층 질의 경로로 들어오면 debug 가 abort 한다.
  - develop 은 분배하므로 그런 원소가 없다. OR-of-AND 를 CNF 에서 통째로 두는 변경(CBRD-27855 PR#8375 리뷰)이 이 가정에 걸린다. — 정소희(.52) 2026-11-09
- **[계약 — develop 은 지킴] (+) 표기의 ON 이동은 술어의 최상위 표시만 본다** (.52, develop `99fa309ca`·PR#8375 head `8831911fb` 동적, 2026-11-06):
  - OR-of-AND 안의 `i.y(+) = 10` 이 통째 PT_OR 아래에 있으면 ON 으로 옮겨지지 않고 WHERE 에 남아 NULL 확장행이 빠진다. develop 은 분배된 절마다 표시가 있어 2행(정답) — CBRD-27855 PR#8375 리뷰, 재현 claude-workspace `projects/CBRD-27855/repro/g4` 2번. — 정소희(.52) 2026-11-09
- **[미수정 — develop 선재(CBRD-27855 PR#8375 리뷰 G4-06)] 한 열 OR-of-AND 는 비결정 함수가 있어도 분배된다** (.52, 정적, develop `99fa309ca` 동일 — 리뷰 G4-06, 2026-11-06):
  - DRAND·NEXT_VALUE·세션 변수·메서드 호출이 든 인자도 분배되어 복제 평가된다. 동적으로 확인하지 않았다. **미수정**. — 정소희(.52) 2026-11-09
- **[해소됨 — CBRD-27957, PR#8429 develop `867265344` 2026-11-10] 항상 거짓인 부질의 위 EXISTS 가 NULL 형으로 접힌다** (.51, develop `953e83256`, 2026-11-06 — 동적 확인 `MALLOC_CHECK_=3 MALLOC_PERTURB_=165`):
  - **`pt_eval_expr_type ()` 의 PT_EXISTS(type_checking.c:10560)는 피연산자 타입이 NULL·NA 면 식 타입을 NULL 로 둔다**: `pt_to_false_subquery ()` 가 거짓 WHERE 부질의를 `is_false_where` NULL 값으로 바꾼 뒤라 EXISTS 가 NULL 형이 된다.
  - **`pt_fold_const_expr ()` 끝(type_checking.c:~19460)은 접은 값이 NULL·NA 가 아니면 형을 식 형으로 덮는다** → 정수 0 이 NULL 형이 되어 `null` 로 출력되고, sql hash text 가 진짜 NULL 식(`c0 <= NULL`)과 같아져 XASL 캐시를 공유한다.
  - **`pt_fold_union ()` 의 FOLD_AS_NULL 값에는 `is_false_where` 가 없다** → EXISTS 가 참으로 계산(`pt_evaluate_db_value_expr ()` PT_EXISTS 는 is_false_where 일 때만 거짓), NOT IN 은 NULL(PT_IS_NOT_IN 은 is_false_where 일 때만 참). 실측: 두 갈래가 모두 거짓인 UNION ALL 위 `WHERE NOT EXISTS`·`NOT IN` 이 3행 대신 0행.
  - **수정됨 — PR#8429(머지됨 `867265344`)**: EXISTS 형 LOGICAL(피연산자가 is_false_where 일 때), NULL 로 접힌 집합 연산에 is_false_where. — 정소희(.52) 2026-11-09, 머지 표기 11-10
- **[해소됨 — CBRD-27961, PR#8428 머지 `6a54287e7`(2026-11-12)] 집합 연산 접기가 문장 텍스트를 옮기지 않아 바인드 재컴파일이 실패한다** (.51, develop `953e83256`, 2026-11-06 — 동적 확인 `MALLOC_CHECK_=3 MALLOC_PERTURB_=165`):
  - **문장 텍스트 길이는 맨 위 노드에만 있다**: `parser_new_node ()`(parse_tree_cl.c:2501)는 모든 노드에 `g_query_string` 과 그때의 `g_query_string_len`(직전 문장 길이)을 넣고, 문장 끝 액션(csql_grammar.y:1921)이 맨 위 노드에만 진짜 길이를 넣는다. `parser_reinit_node ()` 는 텍스트를 지킨다.
  - **`pt_fold_union ()`(semantic_check.c:19106)은 접은 노드에 줄·칸·alias_print·next 만 옮겼다** → 문장이던 UNION 을 남은 갈래로 바꾸면 길이 0 인 문장이 된다. 그 결과(-452)는 src-compat §2 「db_recompile_for_bind_signature」.
  - 수정 PR#8428 `35b022896`(머지 `6a54287e7`, 2026-11-12): 접은 노드에 sql_user_text·len 도 옮김. — 정소희(.52) 2026-11-09
- **[미수정 — CBRD-27962, 수정 PR#8435 `73ae5c347`·`cfdef8ea8` 미머지] `COALESCE (정수, NULL)` 은 VARCHAR, `COALESCE (NULL, 정수)` 는 INTEGER** (.51, develop `953e83256`, 2026-11-06 — 동적 확인 `MALLOC_CHECK_=3 MALLOC_PERTURB_=165`): 오버로드 `(number, ANY) → VARCHAR` 에서 ANY 가 NULL 과도 '같은 형'(`pt_are_equivalent_types ()` func_type.cpp:1344)이라 `(number, number)` 보다 많이 맞는다. NVL·IFNULL 도 같다. 파생 테이블 열 형은 접기 전에 정해지므로(§2 「pt_bind_names / pt_get_attr_list_of_derived_table」) 접기가 바꾼 항목 형과 어긋난다.
  - 실측(JDBC): develop 의 파생 열이 825373492(문자열 '1234' 바이트), `a + 1` 1100836660, UNION ALL 파생은 형 통합이 DOUBLE 이 되어 1072693248·8.
  - 수정 PR#8435 `73ae5c347`·`cfdef8ea8`(미머지): 바깥 SELECT 형 검사 끝에서 형 열거값이 바뀐 파생 열 항목에 열 형 CAST(항목과 열은 숨은 항목 포함 위치로 짝 — §2). 오버로드 규칙은 그대로(바꾸면 비파생 SELECT·CTAS 형까지 바뀜). — 정소희(.52) 2026-11-09

- **[src-parser §3] develop 의 CNF 변환은 원자(IS [NOT] TRUE/FALSE·CASE·IF·XOR·비교·함수) 아래로도 걸어 내려가 그 피연산자 안의 AND 를 next 목록으로 바꾼다 — OR 공통 인수 추출이 출력 문자열로 비교하므로 첫 항만 같은 두 갈래를 같다고 보고 한쪽을 버린다** (.52, develop `8b9e7fd01`, 2026-11-17): `pt_transform_cnf_pre ()`(cnf.c)가 AND·OR 밖의 노드에서 `continue_walk` 를 건드리지 않아 `pt_transform_cnf_post ()` 가 원자 안의 AND 를 목록으로 만든다. 공통 판정(`pt_str_compare (lhs_str, rhs_str)`) 때 그 목록의 머리는 아직 `is_cnf_start` 가 없어 `pt_print_expr ()` 가 첫 conjunct 만 찍는다(debug gdb 로 두 쪽 모두 `"t.a>0 is true"` 확인, parse_tree_cl.c:2622 부근). `((a > 0 and a = 1) is true) or ((a > 0 and a = 2) is true)` 가 1행(정답 2). HAVING·START WITH 처럼 `pt_cnf ()`(분배 모드)를 쓰는 절에서는 원자 안의 OR-of-AND 가 곱으로 펼쳐져 `((a = 1 and 10 / b > 1) or (a = 3 and b = 0)) is true` 의 가드가 깨져 `Attempt to divide by zero`(-539). XOR·NOT(CASE …)·UPDATE·MERGE 의 WHERE 도 같다. 재현 claude-workspace `projects/CBRD-28027/review-8590/adv.sql`. **미수정**(develop) — PR#8590 이 고침(미머지). — 정소희(.52 환류) 2026-11-18
- **[src-parser §3] `pt_fold_const_expr ()` 는 AND/OR 한쪽이 NULL 상수면 `NULL AND x → NULL`, `NULL OR x → x` 로 접는다 — 필터 맨 위에서만 맞다** (.50, develop `3421d763b`, 2026-11-18): 선택 목록 `((n < 0) AND (1 = NULL)) IS NULL` 이 n = 1 에서 1(정답 0), `((n < 0) OR (1 = NULL)) IS NULL` 이 0(정답 1). CBRD-28027 수정(#8590, CNF 를 AND·OR 안으로만)이 들어가면 WHERE 의 IS 피연산자도 트리로 남아 같은 길을 탄다. CBRD-27904 계열(그 PR #8437 은 11-10 머지 없이 닫힘). **미수정** — PR#8609(CBRD-28029) 미머지. — 정소희(.52 환류) 2026-11-18
- **[src-parser §3] `pt_to_pred_expr_local_with_arg ()` 는 술어 자리의 NULL 상수를 `0 = 1`(FALSE)로 만든다** (.50, develop `3421d763b`): 필터 맨 위에서는 결과가 같지만 IS·NOT·XOR·CAST(T_PREDICATE 값) 아래에서는 UNKNOWN 이 FALSE 가 된다. `et_comp->type = DB_TYPE_NULL` 은 이미 쓰이는 값(위치 변수)이고 NULL 피연산자는 타입을 보기 전에 V_UNKNOWN. **미수정** — PR#8609(CBRD-28029) 미머지. — 정소희(.52 환류) 2026-11-18
- **[src-parser §3] LIKE/NOT LIKE 상수 접기(`pt_evaluate_db_value_expr ()`)는 `no_backslash_escapes=no` 면 역슬래시를 암묵 이스케이프로 쓰지만, 실행·재작성은 `require_like_escape_character` 로만 정한다** (.50, develop `3421d763b`): =no·require=no 에서 `'a_c' LIKE 'a\_c'` 접기 1, 열 0. 이 접기가 키에 없는 파라미터를 읽어, `no_backslash_escapes` 가 XASL 캐시 키(`PRM_FOR_QRY_STRING`)에 없던 동안 같은 문장이 옛 설정의 계획을 재사용했다. UPDATE·DELETE·INSERT·MERGE 의 키(`CUSTOM_PRINT_4_SHA_COMPUTE`)는 키 파라미터를 하나도 담지 않았다(SELECT 만 `PT_PRINT_DIFFERENT_SYSTEM_PARAMETERS`). **미수정** — PR#8609(CBRD-28029) 미머지. — 정소희(.52 환류) 2026-11-18
- **[parser §3] `pt_fold_const_expr ()` 는 바꿔 끼우는 노드의 `next` 만 옮긴다 — AND/OR 노드가 피연산자 하나로 접히면 or_next 사슬이 사라진다** (.52, c8e8d4f7f, 2026-11-17): type_checking.c:18494(next 만 저장)·19232(피연산자 사본 반환)·19468(or_next 째 해제). or_next 를 잇는 분기(19313-19340)는 결과가 값일 때만 탄다. 그래서 or_next 를 단 PT_OR/PT_AND 트리가 CNF 목록에 있으면 상수 접기에서 뒤 갈래를 잃는다(PR#8517 1차 지적 Case 20, c8e8d4f7f 커밋 메시지). — 정소희(.52 환류) 2026-11-18
- **[parser §3] `pt_cnf_where ()` 는 c8e8d4f7f 부터 피연산자에 통째 트리가 있는 OR 도 통째로 두지만, `(+)` 술어가 든 OR 은 예외로 분배해(cnf.c:957 `!outer_mark`) 1032-1043 특수 경우가 다른 갈래를 통째 트리의 or_next 에 매단다** (.52, c8e8d4f7f, 2026-11-17): 바로 위 사실과 겹쳐 Oracle 식 외부 조인에서 행이 빠진다 — `o.id = i.id(+) AND (((CAST(5 AS VARCHAR) <> '6') AND (CAST(5 AS VARCHAR) = '6')) OR (CAST(7 AS VARCHAR) IS NULL) OR (i.c(+) > 0))` 이 0행(9f9f9d715 는 1행). 단위 suite dev4-review-workspace `unit/parser/cnf.or_tree_chain`(F1a~F1d), 재현 `repro/r6_plus.sql`. **PR#8517 c8e8d4f7f 미수정.** — 정소희(.52 환류) 2026-11-18
- **[parser §3] PR#8517 의 `pt_to_pred_expr_factor_dnf ()`(xasl_generation.c:2620, 호출 `pt_to_pred_expr_with_arg ()` 2246)는 통째로 둔 OR-of-AND 인수를 실행용 술어에서 DNF 로 펴는데, 안전 검사 `pt_factor_dnf_is_unsafe ()`(2333-2378)는 부질의·난수·두 spec 만 거절하고 실패할 수 있는 잎(나눗셈·CAST)은 보지 않는다** (.52, c8e8d4f7f, 2026-11-17): `((b = 0 or 10 / b > 1) and a = 1) or a = 3` 이 `(b = 0 and a = 1) or (10 / b > 1 and a = 1) or a = 3` 이 되어 써 둔 갈래 순서가 막던 `10 / b` 를 평가 — `Attempt to divide by zero.`(41ca53ce7·9f9f9d715 는 0행). 게이트가 PT_OR(or_next 없음)만 보므로 WHERE·ON·EXISTS·CASE·IF·SELECT 목록·UPDATE SET 조건 모두 해당. 재현 claude-workspace `projects/CBRD-28076/repro/g5/e6.sql`, 단위 suite `unit/parser/xasl_generation.factor_dnf`. **PR#8517 c8e8d4f7f 미수정.** — 정소희(.52 환류) 2026-11-18
- **[src-parser §3] `pt_false_where ()`(type_checking.c) 는 맨 바깥 SELECT 에도 불리고, START WITH·after_cb_filter 의 상수 거짓을 `pt_is_single_tuple ()` 보다 먼저 본다** (.50, develop `25b933925`, 2026-11-18): `do_select_internal ()`·`do_prepare_select ()` 가 참이면 실행 없이 빈 결과를 내서 `SELECT COUNT (*) … START WITH 1 = 0` 이 0행(정답 1행 0). [CS·SA, develop **미수정**, PR#8609 `3a69da257` 에서 순서 바꿈] — 정소희(.51 환류) 2026-11-20

- **[미수정] 집합 생성자·IN 목록 안에서 문자열이 아닌 값에 붙인 COLLATE 가 오류로 걸러지지 않고 클라이언트가 SIGSEGV** (.50, develop de4bb116e, 2026-11-20) — CBRD-28295: `SELECT {CAST ((c1 COLLATE utf8_bin) AS CHAR(3))} FROM t1`(c1 INT)은 `pt_check_cast_op ()` 가 cast_type 이 NULL 인 안쪽 CAST 를 읽고(semantic_check.c:1177), `SELECT {'x', 'x' + (COALESCE (1, ?) COLLATE utf8_bin)}` 는 `pt_coerce_node_collation ()` 이 data_type 없는 MAYBE 식에 쓴다. 집합 밖이면 같은 식이 Semantic 오류다. release·debug 모두.

## 4. 진행중인 작업

> 각 컨테이너가 자기 소절을 직접 관리한다. 완료되면 지우지 말고 "완료(PR/커밋)"로 갱신.

### .50
- (해당 없음 또는 미기입)
### .51
- (해당 없음 또는 미기입)
### .52
- (해당 없음 또는 미기입)
