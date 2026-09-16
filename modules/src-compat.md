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

### db_value_clear / db_value_free (db_macro.c)

- 문자열·셋·JSON 등 non-trivial DB_VALUE는 사용 후 반드시 `db_value_clear()` — 서버 측 별칭이자
  실체는 `pr_clear_value()`(object/object_primitive.c; 내부 캐베트는 src-object.md 참조).
- `db_value_free()`는 `pr_free_ext_value()`로 **컨테이너 자체까지 해제** — 스택 DB_VALUE에 쓰면 안 됨.
- ✅ **리뷰 체크포인트**: non-trivial 값의 모든 경로(에러 포함)에서 `db_value_clear()`가 호출되는가?

### db_open_buffer / db_compile_statement / db_execute_statement (db_vdb.c)

- 클라이언트 문장 처리 3단: `db_open_buffer`(파싱, 내부 `parser_parse_string_with_escapes` L477) →
  `db_compile_statement`(의미 분석·XASL 생성, `db_compile_statement_local` L820) →
  `db_execute_statement`(실행). csql·CAS가 이 경로를 그대로 쓴다.

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
