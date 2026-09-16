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

## 3. 예비 이슈 사항

> 미수정 버그·의심·문서 정정 후보·구조적 한계. 해소되면 삭제가 아니라 "해소됨(커밋/PR)"로 갱신.

- (현재 등록된 예비 이슈 없음)

## 4. 진행중인 작업

> 각 컨테이너가 자기 소절을 직접 관리한다. 완료되면 지우지 말고 "완료(PR/커밋)"로 갱신.

### .50
- (해당 없음 또는 미기입)
### .51
- (해당 없음 또는 미기입)
### .52
- (해당 없음 또는 미기입)
