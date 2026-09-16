# src/xasl

> 기준: upstream/develop 95b79e7ed (2026-08-27)

## 1. 소스 목적 및 사용처 (함수별)

파서(클라이언트)와 실행기(서버)가 공유하는 XASL 플랜 타입 정의 — 헤더 중심 모듈.
`xasl_predicate.hpp`(`PRED_EXPR`, `COMP_EVAL_TERM`), `xasl_aggregate.hpp`, `xasl_analytic.hpp`,
`xasl_stream.hpp`(직렬화 포맷 상수), `xasl_unpack_info.hpp`(역직렬화 컨텍스트), `xasl_sp.hpp`.
파이프라인: parser/가 XASL_NODE 트리 생성 → `query/xasl_to_stream.c`로 직렬화 →
`query/stream_to_xasl.c`로 역직렬화 → `query/query_executor.c`가 실행. 직렬화/역직렬화 진입점은
query 모듈에 있지만 이 모듈의 타입·스트림 유틸이 그 경계를 정의하므로 함께 표에 둔다.

| 함수 | 파일 | 목적 | 주요 사용처(호출자) |
|---|---|---|---|
| `xts_map_xasl_to_stream` | query/xasl_to_stream.c:278 | XASL 트리 → 바이트 스트림 직렬화(클라이언트) | query/execute_statement.c:9147·:9999·:10843 |
| `xts_map_filter_pred_to_stream` | query/xasl_to_stream.c:380 | 필터 인덱스 술어 직렬화 | query/execute_schema.c:3422·:15913 |
| `stx_map_stream_to_xasl` | query/stream_to_xasl.c:212 | 바이트 스트림 → XASL 역직렬화(서버) | query/query_manager.c:1214, query/xasl_cache.c:1133, parallel/px_scan/px_scan_task.cpp:597 |
| `stx_map_stream_to_xasl_node_header` | query/stream_to_xasl.c:176 | 스트림에서 XASL 노드 헤더만 역직렬화 | query/list_file.c:1145 |
| `stx_map_stream_to_filter_pred` | query/stream_to_xasl.c:291 | 필터 인덱스 술어 역직렬화 | query/filter_pred_cache.c:409, storage/btree_load.c:957·:1147 |
| `stx_init_xasl_unpack_info` | xasl_stream.cpp:74 | 역직렬화 컨텍스트(XASL_UNPACK_INFO) 초기화 | stream_to_xasl.c 진입 경로 |
| `stx_alloc_struct` | xasl_stream.cpp:221 | unpack 버퍼 내 구조체 할당(개별 free 없음) | stream_to_xasl.c 전역 |
| `stx_mark_struct_visited` / `stx_get_struct_visited_ptr` | xasl_stream.cpp:119 / :167 | 공유 노드 중복 역직렬화 방지(방문 표시/조회) | stream_to_xasl.c 전역 |
| `stx_build_db_value` / `stx_build_string` | xasl_stream.cpp:279 / :287 | 기본 타입 역직렬화 유틸 | stream_to_xasl.c |
| `get_xasl_unpack_info_ptr` / `set_xasl_unpack_info_ptr` | xasl_unpack_info.cpp:37 / :52 | 스레드별 unpack info 컨텍스트 접근 | stream_to_xasl.c, xasl_stream.cpp |
| `free_xasl_unpack_info` | xasl_unpack_info.cpp:69 | unpack 버퍼 일괄 해제 | query_manager, xasl_cache 클론 해제 경로 |
| `cubxasl::pred_expr::clear_xasl` | xasl_predicate.cpp:32 | 술어 트리 내 DB_VALUE 정리(재귀) | query/regu_var.cpp:155, qexec_clear_pred 계열 |
| `cubxasl::spawner::spawn` (오버로드 다수) | xasl_spawner.cpp:37~ | 병렬 실행용 PRED_EXPR/REGU_VARIABLE 깊은 복제 | parallel/px_hash_join/px_hash_join_spawn_manager.cpp:132~146 |
| `cubxasl::iterate_xasl_tree` / `iterate_regu_var` | xasl_iteration.hpp:32 / :34 | XASL 트리/REGU 트리 순회 유틸(std::function) | parallel/px_query_execute/px_query_executor.cpp:319·:357 |
| `analytic_list_node::init` | xasl_analytic.cpp:32 | 분석 함수 노드 초기화 | query_analytic 실행 경로 |

## 2. 분석 내용 (함수별)

> 항목은 함수 단위로 기술한다 — 각 항목의 제목/선두가 함수·파일명이다. 새 분석도 함수명을 앞세워 추가할 것.

### 모듈 일반

- CS_MODE와 SERVER_MODE가 공유 — **모드별 가드 사용 불가**.
- `REGU_VARIABLE`이 가장 복잡한 타입 — 깊이 중첩된 union.
- 여기 변경은 보통 `parser/xasl_generation.c`, `query/xasl_to_stream.c`,
  `query/stream_to_xasl.c`의 연쇄 수정을 요구한다.
- ✅ **리뷰 체크포인트**: `#if defined(SERVER_MODE)` 류 모드 가드가 이 모듈에 들어오지 않았는가?
- ✅ **리뷰 체크포인트**: union 멤버 접근이 해당 노드 타입과 일치하는가?

(원본: src/xasl/AGENTS.md)

### xts_map_xasl_to_stream / stx_map_stream_to_xasl (query/xasl_to_stream.c:278 / query/stream_to_xasl.c:212)

- 구조체는 클라이언트(직렬화기)와 서버(역직렬화기) 간 일치 필수. **XASL 구조체에 필드를 추가하면
  직렬화 그리고 역직렬화 양쪽을 갱신해야 한다 — 불일치는 크래시**(스트림 오프셋이 밀려 이후 필드
  전체가 오염된다). 버전 불일치도 같은 이유로 크래시.
- 필터 술어 경로(`xts_map_filter_pred_to_stream` / `stx_map_stream_to_filter_pred`)도 같은 대칭
  규약을 따른다 — 술어 타입(`xasl_predicate.hpp`) 변경 시 함께 볼 것.
- ✅ **리뷰 체크포인트**: 필드 추가/변경이 xasl_generation·xasl_to_stream·stream_to_xasl 3곳에 모두 반영됐는가?

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
