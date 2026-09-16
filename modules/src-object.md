# src/object

> 기준: upstream/develop 95b79e7ed (2026-08-27)

## 1. 소스 목적 및 사용처 (함수별)

스키마 관리, 시스템 카탈로그, 권한, 트리거, information_schema, 클라이언트 객체 캐시(workspace),
primitive 타입 연산, 디스크↔메모리 변환. 접두사: `sm_`(schema), `au_`(auth), `tr_`(trigger),
`ws_`(workspace), `pr_`/`mr_`(primitive), `tp_`(type/domain), `tf_`(transform), `classobj_`.

| 함수 | 파일 | 목적 | 주요 사용처(호출자) |
|---|---|---|---|
| `pr_clear_value` | object_primitive.c:1866 | DB_VALUE 내부 데이터 해제(need_clear 등 타입별 정리) | 전 모듈 서버/클라 공통; compat `db_value_clear()`의 실체 |
| `mr_data_readval_int` | object_primitive.c:2411 | INTEGER 레코드 디스크→DB_VALUE (static, PR_TYPE 함수포인터) | `tp_Integer`의 `f_data_readval` 경유 — 힙 레코드 읽기 경로 |
| `mr_index_readval_int` | object_primitive.c:2443 | INTEGER 인덱스 키 디스크→DB_VALUE (static) | `tp_Integer`의 `f_index_readval` 경유 — btree 키 읽기 경로 |
| `tp_value_cast` | object_domain.c:10081 | DB_VALUE를 목적 도메인으로 캐스트(암묵/명시) | object_template.c, loaddb(load_db_value_converter.cpp), compat/db_json.cpp |
| `tp_domain_resolve_default` | object_domain.c:3080 | DB_TYPE→기본 캐시 TP_DOMAIN | compat/db_macro.c, base/object_representation_sr.c |
| `sm_find_class` | schema_manager.c:5503 | 클래스 이름→MOP 해석 | compat(db_admin.c, db_obj.c 등), executables |
| `smt_edit_class_mop` | schema_template.c:753 | 기존 클래스의 스키마 편집 템플릿 시작 | compat/db_class.c·db_virt.c, query/execute_schema.c |
| `sm_update_class` | schema_manager.c:13536 | 편집 템플릿을 커밋(실제 스키마 반영) | compat/db_class.c·db_virt.c, schema_information_schema_builder.cpp |
| `au_login` | authenticate.c:90 | 사용자 인증(로그인) | compat/db_admin.c, broker/cas_execute.c, api/cubrid_log.c |
| `au_fetch_class` | authenticate_access_class.cpp:618 | 권한 검사 + 클래스 객체 fetch | compat 전반(db_set.c, db_info.c 등), executables/unload_object.c |
| `AU_SAVE_AND_DISABLE` / `AU_RESTORE` | authenticate.h:115/122 | 권한 검사 일시 중단/복원 매크로 쌍(지역변수 `save` 공유) | schema_manager.c, trigger_manager.c 등 다수 |
| `ws_mop` | work_space.c:617 | OID→MOP 매핑(워크스페이스 캐시 조회/생성) | transaction/locator_cl.c, communication/network_interface_cl.c |
| `ws_find` | work_space.c:3139 | MOP→메모리 객체 포인터 | executables(compactdb.c, unload_object.c 등) |
| `ws_decache` | work_space.c:2725 | MOP의 캐시 객체 해제 | transaction/locator_cl.c, query/execute_statement.c |
| `tr_prepare_statement` | trigger_manager.c:5347 | 문장 이벤트에 걸린 트리거 실행 준비 | query/execute_statement.c |
| `tf_disk_to_class` / `tf_class_to_disk` | transform_cl.c:4377/4451 | 클래스 객체 디스크↔메모리 변환 | transaction/locator_cl.c |

## 2. 분석 내용 (함수별)

> 항목은 함수 단위로 기술한다. 새 분석도 함수명을 앞세워 추가할 것.

### 모듈 일반

- **Information Schema 쿼리 스펙 포맷은 CI 강제(STRICT)** (`schema_system_catalog_install_query_spec.cpp`):
  문장 들여쓰기 1탭+2칸(CASE는 2칸), 줄 끝 공백( `)` 앞·`(` 뒤 제외), `(` 앞·`)` `{` `}` 뒤 공백,
  `SELECT`/`FROM`/`WHERE`/`ORDER BY` 뒤와 `AND`/`OR` 앞 줄바꿈, `WHEN`+`THEN` 120자 미만 시 한 줄,
  별칭에 항상 `AS`, 타입 변환 주석 `CAST (x AS VARCHAR(255)) /* string -> varchar(255) */`,
  포맷 지정자 주석 `"[%s] AS [cls] " /* CT_CLASS_NAME */`, auth 매크로(`AUTH_CHECK_CLASS()`,
  `AUTH_CHECK_OWNER()`, `AUTH_CHECK_DBA`, `CURRENT_USER_GROUPS_SUBQUERY`) 사용.
- 카탈로그 테이블 이름은 상수 사용: `CT_CLASS_NAME`(`_db_class`), `CT_ATTRIBUTE_NAME`, `CT_INDEX_NAME`,
  `CT_SERIAL_NAME`, `AU_USER_CLASS_NAME` 등 (`schema_system_catalog_constants.h`).
- SERIAL 범위: MINVALUE = -10^36, MAXVALUE = 10^37 (**±10^38 아님**).
- ✅ **리뷰 체크포인트**: info schema 쿼리 스펙이 9개 포맷 규칙을 전부 지키는가(특히 줄 끝 공백·AS·주석)?
- ✅ **리뷰 체크포인트**: 뷰에 권한 필터(auth 매크로)가 들어갔는가?
- ✅ **리뷰 체크포인트**: 카탈로그 테이블 이름을 리터럴 대신 `CT_*` 상수로 참조하는가? 상수 추가 시
  `schema_system_catalog_constants.h`도 갱신됐는가?
- ✅ **리뷰 체크포인트**: SERIAL 경계값을 ±10^38로 잘못 쓰지 않았는가?

### pr_clear_value (object_primitive.c)

- 함수로컬 `static bool oracle_style_empty_string = prm_get_bool_value (...)` (L1873) → 호출마다
  C++ static 가드 검사가 `value == NULL` 검사(L1875)보다 먼저 실행된다. 같은 패턴 5개가 .bss에 인접.
  INTEGER 값 정리는 27명령어로 2바이트를 쓴다(실측).
- 올바른 가드 선례: fetch.c:4906의 `DB_NEED_CLEAR` 선검사.
- **주의**: `DB_NEED_CLEAR`만으로는 대체 불가 — SET 계열은 `set_free`, OBJECT는 `op=NULL`, ENUM 등
  need_clear=false여도 구조 작업이 있다.
- compat `db_value_clear()`가 이 함수를 그대로 호출한다(db_macro.c:1484). `db_value_free()`는
  `pr_free_ext_value()`로 컨테이너까지 해제 — 별개 함수.

### mr_data_readval_int / mr_index_readval_int (object_primitive.c)

- static 함수(선언 L372/L375), `tp_Integer` 등 PR_TYPE 인스턴스의 함수 포인터로만 호출된다.
- PR_TYPE이 .bss 동적 초기화(`pr_type` 생성자가 non-constexpr, object_primitive.h:114~) →
  disksize/함수포인터 상수폴딩 불가. `mr_index_readval_int` 39명령어 + memcpy@plt(4바이트!) vs
  `mr_data_readval_int` 21명령어. 실측 1.02% vs 0.29%. 개선안: constexpr화 또는 `OR_*_SIZE` 리터럴 사용.

### smt_edit_class_mop / sm_update_class (schema_template.c / schema_manager.c)

- 스키마 변경은 템플릿 패턴: `smt_edit_class_mop()` → 수정 → `sm_update_class()`.
  클래스 타입 상수: `SM_CLASS_CT`(테이블), `SM_VCLASS_CT`(뷰).
- ✅ **리뷰 체크포인트**: 스키마 DDL이 템플릿 패턴(smt_edit → sm_update_class)을 따르는가?

### AU_SAVE_AND_DISABLE / AU_RESTORE (authenticate.h)

- `Au_disable`은 `au_ctx ()->disable_auth_check`의 별칭(L62). 매크로 쌍이 지역변수 `save`를 공유하며,
  헤더 주석이 직접 경고한다(L105~106): "Pair every AU_SAVE_AND_* with AU_RESTORE on each exit path
  or the state leaks."
- 리팩터·squash 충돌 해소에서 쌍의 한쪽만 남으면 **빌드 브레이크**가 날 수도, 권한 상태가 조용히
  어긋날 수도 있다. 충돌 해소 후 쌍 대칭을 눈으로 확인할 것. (2026-08 squash-merge 빌드 브레이크
  실사례 — 당시 매크로 이름은 `AU_DISABLE`/`AU_ENABLE`; develop 95b79e7ed에서는
  `AU_SAVE_AND_ENABLE`/`AU_SAVE_AND_DISABLE`/`AU_RESTORE`로 대체되어 옛 이름은 grep 0건.)
- ✅ **리뷰 체크포인트**: `AU_SAVE_AND_*`와 `AU_RESTORE`가 모든 exit 경로에서 쌍을 이루는가?
  충돌 해소 커밋이라면 특히 쌍 대칭부터 확인.

## 3. 예비 이슈 사항

> 미수정 버그·의심·문서 정정 후보·구조적 한계. 해소되면 삭제가 아니라 "해소됨(커밋/PR)"로 갱신.

- PR_TYPE .bss 동적 초기화 — disksize/함수포인터 상수폴딩 불가(`mr_index_readval_int`에 4바이트
  memcpy@plt, 실측 1.02%). 95b79e7ed에서 미수정 확인(`pr_type` 생성자 non-constexpr 유지).
- `pr_clear_value` 함수로컬 static 가드가 NULL 검사보다 먼저 실행 — 단 `DB_NEED_CLEAR`만으로 대체
  불가(SET/OBJECT/ENUM 예외). 95b79e7ed에서 미수정 확인(L1873).

## 4. 진행중인 작업

> 각 컨테이너가 자기 소절을 직접 관리한다. 완료되면 지우지 말고 "완료(PR/커밋)"로 갱신.

### .50
- (해당 없음 또는 미기입)
### .51
- (해당 없음 또는 미기입)
### .52
- (해당 없음 또는 미기입)
