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
  (auth 매크로 규칙은 information_schema 파일에만 맞다 — 바로 아래 항목.)
- **권한 필터 매크로(`AUTH_CHECK_<x>`·`CURRENT_USER_GROUPS_SUBQUERY`)는 `schema_information_schema_install_query_spec.cpp` 에만 정의돼 있고,
  시스템 카탈로그 뷰 파일 `schema_system_catalog_install_query_spec.cpp` 의 권한 필터는 인라인 텍스트다** (.50, 6497720ec, 2026-09-17;
  develop `2d925cb86` 재확인 2026-10-28): 매크로 정의는 information_schema 파일 :65-107(`AUTH_CHECK_DBA`·`_OWNER`·`_GRANT`·`_OBJECT`·
  `_SCHEMA`·`_PRIVILEGE`·`_SYNONYM`)뿐이고 시스템 카탈로그 뷰 파일은 하나도 쓰지 않는다 — db_index·db_partition·db_attribute·db_histogram
  이 인라인 서브쿼리 3개(DBA 그룹 / 소유자 / SELECT 피부여자)를 반복한다. 위 줄과 src/object/AGENTS.md 「Information Schema Rules」 9 의
  "Use auth macros" 는 information_schema 파일 기준이고, 거기 적힌 `AUTH_CHECK_CLASS()` 는 소스 어디에도 정의돼 있지 않다(grep 0건).
  문서 불일치는 §3. — 정소희(.50) 2026-10-28
- 카탈로그 테이블 이름은 상수 사용: `CT_CLASS_NAME`(`_db_class`), `CT_ATTRIBUTE_NAME`, `CT_INDEX_NAME`,
  `CT_SERIAL_NAME`, `AU_USER_CLASS_NAME` 등 (`schema_system_catalog_constants.h`).
- SERIAL 범위: MINVALUE = -10^36, MAXVALUE = 10^37 (**±10^38 아님**).
- ✅ **리뷰 체크포인트**: info schema 쿼리 스펙이 9개 포맷 규칙을 전부 지키는가(특히 줄 끝 공백·AS·주석)?
- ✅ **리뷰 체크포인트**: 뷰에 권한 필터가 들어갔는가? (information_schema 뷰는 auth 매크로, 시스템 카탈로그 뷰는
  db_index 와 같은 인라인 서브쿼리 3개 — 정소희(.50) 2026-10-28 보완)
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

### 시스템 카탈로그 테이블·뷰 — `_db_histogram` / `db_histogram` / `statistics_strategy` (schema_system_catalog_install.cpp, schema_system_catalog_install_query_spec.cpp)

- **`_db_histogram.class_of` 는 `_db_class` 행이 아니라 클래스 MOP 자체다** (.50, 6497720ec, 2026-09-17; develop `2d925cb86` 재확인):
  `smt_add_histogram`(schema_template.c:2072, :2100)·`get_histogram_for_write`(histogram_cl.cpp:189, :206)·`db_get_histogram`
  (histogram_cl.cpp:2469, :2486)가 `db_make_object (&value, classop)` 으로 키를 만든다. 그래서 뷰에서 이름을 얻으려면 `db_index` 식
  경로식(`[i].[class_of].[class_name]`)이 아니라 `_db_class [c]` 조인 `[h].[class_of] = [c].[class_of]` 이 필요하고, `_db_auth.object_of`
  와는 바로 비교된다(db_attribute 스펙의 `{[c].[class_of]}` 자리에 `[h].[class_of]`). develop 의 `sm_define_view_histogram_spec ()`
  (schema_system_catalog_install_query_spec.cpp:1720-1790)이 이 조인과 db_index 와 같은 권한 필터를 쓴다(수정됨: `880a17338` CBRD-27043).
  — 정소희(.50) 2026-10-28
- **시스템 뷰의 컬럼 도메인(`get_view_<name>` 의 columns)이 query spec 의 결과 타입을 덮어쓴다** (.50, 6497720ec, 2026-09-17; develop
  `2d925cb86` 재확인): `db_histogram` 스펙이 `CAST (… AS NUMERIC(18, 12))` 를 해도 도메인이 `double` 이면 `0.000000000000000e+00` 로
  나오고, `{"class_name", "object"}` 면 문자열 비교가 `'=' operator is not defined on types object and char` 가 된다(재현
  `projects/CBRD-27043/repro/repro_27043.out`). 스펙과 도메인은 1:1 로 맞춰야 한다. develop 의 `get_view_db_histogram ()`
  (schema_system_catalog_install.cpp:2262)은 도메인을 `format_varchar (255)`·`format_numeric (18, 12)` 로 맞추고 이 규칙을 주석(:2269-2270)
  으로 남겼다(수정됨: `880a17338` CBRD-27043). — 정소희(.50) 2026-10-28
- **`_db_histogram` 스키마 = class_of/key_attr/with_fullscan/null_frequency/histogram_values, 타임스탬프 없음** (.51, PR#7900
  `f79eda483`~`66bfd071d`, 2026-09-09~17; develop `2d925cb86` 재확인 — `system_catalog_initializer::get_histogram ()`
  schema_system_catalog_install.cpp:1280-1292): 기존 행 재빌드(`store_one_histogram`, histogram_cl.cpp:231)는 `null_frequency`·
  `histogram_values` 만 갱신하고 **`with_fullscan` 은 안 바꾼다**(`sm_add_histogram` 이 `ER_LC_CLASSNAME_EXIST` 로 건너뜀,
  schema_manager.c:15587) — 재빌드 여부 신호로 `with_fullscan` 을 쓰면 오판. 신호는 행 chn 또는 `null_frequency`. — 정소희(.50) 2026-10-28
- **`_db_histogram` 의 제약은 `UNIQUE (class_of, key_attr)` 하나뿐이다** (.50, static, `2d5a35d24`, 2026-09-18; develop `2d925cb86`
  재확인 — `system_catalog_initializer::get_histogram ()` schema_system_catalog_install.cpp:1295): `_db_histogram` 삽입의
  `ER_BTREE_UNIQUE_FAILED` 는 그 키로만 발생한다는 뜻이다. `sm_add_histogram ()`(schema_manager.c:15617-15634)이 이것을 근거로 동시 첫
  수집의 유니크 위반을 "이미 있음"(`ER_LC_CLASSNAME_EXIST`)으로 번역한다(`0d0809963` CBRD-27369). — 정소희(.50) 2026-10-28
- **`_db_class.statistics_strategy` 는 `db_class`/information_schema 뷰에서 0·1 만 이름으로 바꿔 노출한다 — 비트를 더 실으면 뷰가 NULL 을
  낸다(뷰 정의를 함께 바꿔야 하고, 기존 DB 반영은 §3 「시스템 뷰 정의 변경」의 제약을 받는다)** (.51, PR#7900, 2026-09-09~17; develop
  `2d925cb86` 재확인): `db_class` 는 `CASE [c].[statistics_strategy] WHEN 0 THEN 'SAMPLING' WHEN 1 THEN 'FULLSCAN' ELSE NULL END`
  (schema_system_catalog_install_query_spec.cpp:75-79), information_schema 는 `DECODE (…, 0, 'SAMPLING', 1, 'FULLSCAN')`
  (schema_information_schema_install_query_spec.cpp:997). — 정소희(.50) 2026-10-28

### CNT_CATCLS_OBJECTS / class_truncate_context — TRUNCATE 의 참조 판정 (schema_system_catalog_constants.h:134, schema_class_truncator.cpp)

- **`CNT_CATCLS_OBJECTS`(schema_system_catalog_constants.h:134) 는 시스템 클래스의 일반 object 도메인 개수이고 TRUNCATE 의 참조 판정
  기준선이다 — 시스템 뷰 컬럼의 타입을 바꾸면 이 값이 움직인다** (.50, PR#7976 `15279602e`, 2026-09-18; develop `2d925cb86` 재확인):
  `schema_class_truncator.cpp` 는 `SELECT COUNT(*) FROM _db_domain WHERE data_type=5 AND (class_of.unique_name='<대상>' OR class_of IS NULL)
  AND ROWNUM <= CNT_CATCLS_OBJECTS + 1` 로 세어(:558) **기준선을 넘으면**(:614) "사용자 클래스가 참조한다" 로 보고 행 삭제
  (`sm_truncate_using_delete`, heap 보존), 아니면 heap 파괴 경로(`sm_truncate_using_destroy_heap`, :621)를 탄다. `db_histogram.class_name` 을
  OBJECT→VARCHAR 로 바꾸니 실제 개수가 하나 줄었고, 상수를 안 내리자 참조가 있는 `DONT_REUSE_OID` 테이블도 기준선을 못 넘어 **heap 이
  파괴·재생성돼 OID 재사용 방지가 풀렸다**. 값의 이력: `1c5f1fd26`(CBRD-27382) 9→10, `880a17338`(CBRD-27043) 10→9, `5a3e7a14b`(CBRD-27302)
  9→6 — develop 은 상수·CAUTION 주석(:102-132) 모두 6. — 정소희(.50) 2026-10-28
- **이 결합을 감시하는 TC 가 세 층으로 있다** (.50, 2026-09-18): ① `shell cbrd_23954/catcls_general_object` 가 개수 자체를 세고(주석에
  "이 값이 바뀌면 `truncate_heap()` 을 같이 고쳐라" 명시, CBRD-23983 — develop 의 CAUTION 주석도 이 케이스를 가리킨다) ②
  `shell cbrd_23954/use_delete` 가 8종 참조 타입 각각에 대해 TRUNCATE 전후 heap `vfid` 동일성을 보고 ③ `sql bug_3339`(CUBRIDSUS-3339) 가
  TRUNCATE 후 dangling OID 역참조가 NULL 인지 본다. 상수 누락 시 ①은 출력차, ②③은 **동작 차이**로 나타난다 — ②③ 을 답안
  재블레싱하면 회귀를 통과시키므로 정렬 대상이 아니다. `shell cbrd_20149_xasl` 의 truncate 답안 5건은 플랜 덤프가 truncator 질의문을
  그대로 실어 `ROWNUM <= CNT+1` 이 노출되므로 상수 변경 시 함께 정렬해야 한다. — 정소희(.50) 2026-10-28

### obj_find_multi_attr / _committed / _for_update — 객체계층 유니크 조회의 잠금 (object_accessor.c:3873/3899/3922)

- **객체계층 유니크 조회의 잠금 두 겹**: `obj_find_multi_attr` → 클라이언트 `btree_find_unique` → 서버 `sbtree_find_unique` 가
  **`S_SELECT_WITH_LOCK` 고정**(행 S, network_interface_sr.cpp:4938) + `au_fetch_instance_force(..., LC_FETCH_DIRTY_VERSION)`(다시 S).
  op_type 을 실어 보내려면 `btree_find_multi_uniques(…, op_type)` 를 써야 한다 (.51, PR#7900 `f79eda483`~`66bfd071d`, 2026-09-09~17;
  develop `2d925cb86` 재확인 — `obj_find_multi_attr_internal ()` object_accessor.c:3692 의 `OBJ_FIND_LOCKED_READ` 분기).
  `0d0809963`(CBRD-27369) 이후 develop 에는 `btree_find_multi_uniques ()` 로 잠금을 고르는 두 변형이 있다: `obj_find_multi_attr_committed ()`
  (:3899 — `S_SELECT` + `LC_FETCH_COMMITTED_VERSION`, 서버가 무잠금 조회를 허용하는 클래스에서만 무잠금)와 `obj_find_multi_attr_for_update ()`
  (:3922 — `S_UPDATE` 로 조회 시점에 X). 두 변형은 파티션 가지치기를 하지 않아(`DB_NOT_PARTITIONED_CLASS`) `_db_histogram` 같은 비분할
  클래스 전용이다(분할 클래스면 루트 인덱스만 찾아 "없음"). — 정소희(.50) 2026-10-28
- **`DB_FETCH_WRITE` 는 X-first 가 아니다 — 위 "잠금 두 겹" 의 실측 확인** (.50, `bc988f0ab`, 2026-09-17 동적): `db_find_multi_unique(…,
  DB_FETCH_WRITE)` → `obj_find_multi_attr(AU_FETCH_UPDATE)` 도 조회는 `btree_find_unique`(= `S_SELECT_WITH_LOCK` 고정)를 타므로 **행 S 를
  먼저 잡고 fetch 에서 X 로 승급**한다. 게이트가 없는 `UPDATE STATISTICS ON ALL CLASSES` 8세션×5회에서 `_db_histogram` 행에 **S 홀더 2 +
  S 대기**(lockdb)와 **데드락 104건**으로 재현. writer 를 X-first 로 만들려면 **`btree_find_multi_uniques(…, S_UPDATE)`** 까지 내려가야 한다 —
  `obj_find_multi_attr_for_update` / `db_find_multi_unique_for_update`(db_obj.c:1252)가 그 경로이고 히스토그램 저장
  (`get_histogram_for_write ()` histogram_cl.cpp:189)이 이것을 쓴다(수정됨: `0d0809963` CBRD-27369 PR#7900; develop `2d925cb86` 재확인).
  `db_find_multi_unique (…, DB_FETCH_WRITE)`(db_obj.c:1171) 자체는 여전히 S 먼저다. — 정소희(.50) 2026-10-28

### ws_decache (work_space.c:2724)

- **`ws_decache` 는 dirty(미flush) 객체에 쓰면 안 된다** — work_space.c 함수 머리 주석의 명시 규약(:2720-2721 "You must not decache an
  object if it is dirty and has not been flushed to the server"). 카탈로그 객체를 읽고 버릴 때 `ws_is_dirty()` 먼저 (.51, PR#7900 작업 중
  `a910e8e6e` 에서 실제로 걸림, 2026-09-16; develop `2d925cb86` 재확인). — 정소희(.50) 2026-10-28

### tp_value_convert_number — 수 → 정수 좁힘과 비교 변환 (object_domain_convert.cpp:275, develop `2d925cb86`)

> object_domain_convert.cpp 는 SERVER·SA·CS 세 빌드 모두에 들어간다.

- **비-strict 수 → 정수 변환은 범위를 "원래 값" 으로 보고 "반올림한 값" 을 좁혔다 (develop `e07b3b09a` 이전)** (.52, `b8199438e`,
  2026-10-16 단위 실측): `tp_numeric_overflow<DST> (number)` 로 검사한 뒤(object_domain_convert.cpp:359 문자열 원천, :397 수 원천)
  `ROUND (number)`(:73, `x + .5` / `x - .5`)를 정수로 캐스트한다(:376 `tp_numeric_value<DST>::make (target, ROUND (number))`, :427
  `static_cast<target_type> (ROUND (number))`). INTEGER 의 부동소수 검사가 `OR_CHECK_INT_OVERFLOW_FROM_FP`(`v < 2^31`,
  object_representation.h:138)라 **[2147483647.5, 2^31) 이 검사를 통과하고 반올림 뒤 2^31 이 되어** int 좁힘이 범위를 벗어났다(UB, x86 에서
  INT_MIN). :427 의 `OR_CHECK_ASSIGN_OVERFLOW` 가드는 BIGINT 와 FLOAT→INTEGER 에만 걸려 DOUBLE·MONETARY→INTEGER 는 빠진다. SMALLINT 는
  `OR_CHECK_SHORT_OVERFLOW`(> 32767)라 해당 없음. 결함 도입은 `16eb8474d`(CBRD-26726) — 그 전엔 `OR_CHECK_INT_OVERFLOW`(> 2147483647)가 먼저
  걸러 OVERFLOW 였고, 16eb8474d 를 담은 release 브랜치는 없다(2026-10-23 확인). CAST 경로: `fetch_cast_operand`(fetch_arith_ops.c:293) →
  `tp_value_cast_with_converter` / `tp_value_cast(_force)` → `tp_value_cast_internal`(object_domain.c:5505) → `tp_value_convert_number`
  (object_domain_convert.cpp:261). **바뀐 내용(`e07b3b09a`, CBRD-27660 PR#8253)**: INTEGER 의 실수 검사 경계가 2^31 이 아니라 `DB_INT32_MAX`
  자체이고 안쪽 꼴이다(`tp_double_int_overflow ()` = `! (v >= DB_INT32_MIN && v <= DB_INT32_MAX)`, :151, `tp_numeric_overflow` :174) — 통과한
  값의 `ROUND` 뒤 0 쪽 절단은 언제나 범위 안이라 좁힘이 안전하고, 출시본 11.4(`object_domain.c:7593` `OR_CHECK_INT_OVERFLOW (db_get_double
  (src))`)·NUMERIC·SMALLINT·음수 끝과 같은 규칙이 된다(2147483647.4 → overflow). — 정소희(.50) 2026-10-28
- **NaN 은 `OR_CHECK_SHORT_OVERFLOW` 를 통과해 SMALLINT 좁힘 UB 에 닿았다 (develop `e07b3b09a` 이전)** (.50, `eb88ab4ea`, 2026-10-23 SA
  실측 — 실측 빌드 `57e11b9d0` 는 develop 동치): Linux 의 `string_to_double` 은 `strtod`(porting.h:1022)라 `tp_atof`(object_domain.c:4695)가
  `'nan'` 을 NaN 으로 받고, `OR_CHECK_SHORT_OVERFLOW(i)` = `(i) > DB_INT16_MAX || (i) < DB_INT16_MIN`(object_representation.h:119)은 NaN 에
  거짓이다 → `CAST('nan' AS SMALLINT)`·`CAST(CAST('nan' AS DOUBLE) AS SMALLINT)` 가 오류 없이 **0**. INTEGER·BIGINT 는 `_FROM_FP`
  (`!(v >= -B && v < B)`)가 NaN 을 오버플로로 본다. strict(COMPARE/OPERAND)는 `modf` 가 NaN 을 걸러 `DOMAIN_INCOMPATIBLE`. 16eb8474d 이전부터
  있던 동작. 같은 구멍이 DOUBLE·MONETARY → TIME(`tp_value_convert_double_to_time`·`tp_value_convert_monetary_to_time`,
  `OR_CHECK_INT_OVERFLOW`)에도 있어 NaN 이 `12:00:0/ AM`(깨진 TIME)으로 나왔다(FLOAT → TIME 은 `_FROM_FP` 라 overflow). **바뀐 내용
  (`e07b3b09a`)**: SMALLINT 의 실수 검사가 안쪽 꼴(`! (number >= DB_INT16_MIN && number <= DB_INT16_MAX)`, :166)이고 TIME 두 변환기가
  `tp_double_int_overflow ()` 를 쓴다(:2164·:2192) — NaN → SMALLINT·TIME 은 `DOMAIN_OVERFLOW`, strict 도 범위 검사(:411)가 `modf` 보다 먼저라
  `DOMAIN_OVERFLOW`. — 정소희(.50) 2026-10-28
- **비교는 실수·문자열을 정수 타입으로 좁히지 않는다** (.50, `eb88ab4ea`, 2026-10-23 정적): 비교 변환기 `domain_compare_converter`
  (domain_rules.c:1350)는 strict 가 아니라 **ASSIGN 변환기**를 쓰지만, 방향을 정하는 `tp_value_compare_common_domain`(object_domain.c)이
  문자열 대 수는 양쪽 DOUBLE(`TP_COMPARE_COERCE_TO_DOUBLE`), 수 대 수는 `db_type_rank`(object_domain.c:107: SHORT < INTEGER < BIGINT <
  NUMERIC < FLOAT < DOUBLE < MONETARY)가 높은 쪽으로 올린다 → 변환기의 실수 → 정수 좁힘 분기에는 닿지 않는다. 인덱스 키 strict 변환
  (scan_manager.c:1739)과 `tp_value_coerce_strict`(object_domain.c:5415)는 결과가 `DOMAIN_COMPATIBLE` 인지만 본다. 상태를 구분하는 호출자:
  파서 상수 강제 변환(type_checking.c:19734 OVERFLOW → ER_IT_DATA_OVERFLOW, INCOMPATIBLE → ER_IT_INCOMPATIBLE_DATATYPE), 연산자 피연산자 변환
  (query_opfunc.c `qdata_operand_coercion_error` → `tp_domain_status_er_set`), ORDER BY LIMIT(query_executor.c:4031 OVERFLOW 면 한계를 버린다),
  inst_num 경계(fetch.c:2557, BIGINT). — 정소희(.50) 2026-10-28

## 3. 예비 이슈 사항

> 미수정 버그·의심·문서 정정 후보·구조적 한계. 해소되면 삭제가 아니라 "해소됨(커밋/PR)"로 갱신.

- PR_TYPE .bss 동적 초기화 — disksize/함수포인터 상수폴딩 불가(`mr_index_readval_int`에 4바이트
  memcpy@plt, 실측 1.02%). 95b79e7ed에서 미수정 확인(`pr_type` 생성자 non-constexpr 유지).
- `pr_clear_value` 함수로컬 static 가드가 NULL 검사보다 먼저 실행 — 단 `DB_NEED_CLEAR`만으로 대체
  불가(SET/OBJECT/ENUM 예외). 95b79e7ed에서 미수정 확인(L1873).
- **[문서 정정 후보] src/object/AGENTS.md 「Information Schema Rules」 9 "Use auth macros" 가 시스템 카탈로그 뷰 파일
  (`schema_system_catalog_install_query_spec.cpp`) 기준으로 적혀 있지만 매크로는 information_schema 파일에만 있다** — **미수정**(문서 불일치,
  develop `2d925cb86` 재확인 2026-10-28) (.50, 6497720ec, 2026-09-17): 규칙 절 머리가 "Query specs in `schema_system_catalog_install_query_spec.cpp`"
  이고, 9 의 `AUTH_CHECK_CLASS()` 는 정의가 없다. 사실은 §2 「모듈 일반」. — 정소희(.50) 2026-10-28
- **[구조적 한계] 시스템 뷰 정의 변경은 같은 메타데이터 버전의 기존 DB 에 반영되지 않는다** — **미수정**(설계상 한계, develop `2d925cb86`
  재확인 2026-10-28, 부분 변화 있음) (.50, 2026-09-17): 뷰 정의는 createdb 의 `catcls_init`(schema_system_catalog_install.cpp:266)/
  `install_system_metadata`(boot_cl.c:219) 경로에서 `_db_class` 에 저장된다. #7791(CBRD-27258 뷰 스펙 개편)·#7976(db_histogram)도 같은 조건이라
  그 전에 만든 DB 는 옛 정의를 유지했다. **바뀐 점**: `9ee8bac8b`(CBRD-26459, 2026-09-22)의 `cubrid upgradedb` 가 버전 스크립트를 돌린 뒤
  카탈로그 vclass 를 실행 바이너리의 정의로 다시 만든다(`upgradedb_rebuild_catalog_vclasses ()` util_sa.c:5468 → `catcls_rebuild_vclasses ()`·
  `info_schema_rebuild_vclasses ()`). 다만 이 경로는 디스크의 메타데이터 버전이 `SYSTEM_METADATA_VERSION`(system_metadata_version.h, 지금 1,
  릴리스 때 올림)과 다를 때만 돈다 — 같으면 부팅도 통과하고 upgradedb 도 바로 끝난다(util_sa.c:5877). 그래서 버전을 올리지 않은 개발 중 뷰
  정의 변경은 여전히 기존 DB 에 닿지 않는다. — 정소희(.50) 2026-10-28
- **`ROUND (x)` = `x + .5` 가 정확하지 않아 정수 좁힘이 1 어긋난다 — CBRD-27769** — **미수정** (develop `2d925cb86` 재확인 2026-10-28 —
  object_domain_convert.cpp:73 그대로) (.50, `eb88ab4ea`·11.4 동일, 2026-10-23 SA 실측): [2^52, 2^53) 의 홀수에 0.5 를 더하면 짝수로 반올림돼
  DOUBLE·MONETARY → BIGINT 가 1 크고(`CAST(4503599627370497e0 AS BIGINT)` = 4503599627370498, BIGINT 열 대입도), 0.49999999999999994 + 0.5 = 1.0
  이라 `CAST(0.49999999999999994e0 AS INT)` = 1. 문자열·NUMERIC 원천은 정확. 안: C 표준 `round ()`. — 정소희(.50) 2026-10-28
- **음수 → TIME 이 깨진 TIME(`12:00:0/ AM`)이 된다 — CBRD-27770** — **미수정** (develop `2d925cb86` 재확인 2026-10-28 —
  `tp_value_convert_integer_to_time ()` object_domain_convert.cpp:2093 그대로) (.50, develop 동치 빌드·PR#8253 `30d7e7c27`·11.4 같음, 2026-10-23
  SA 실측 + 정적): INT·SMALLINT·BIGINT·FLOAT·DOUBLE·MONETARY 의 -1, -86401 모두. `v_time = db_get_int (src) % SECONDS_IN_A_DAY`
  (`tp_value_convert_integer_to_time` 등)가 음수 나머지를 내고 `DB_TIME` 은 `unsigned int`(dbtype_def.h:835)라 0xFFFFFFFF →
  `db_time_decode` 가 24 이상의 시 → `db_time_encode_core`(db_date.c)가 값을 쓰지 않고 `ER_TIME_CONVERSION` 을 돌려주는데 변환기가 반환값
  (`tp_make_time_conversion ()` :769)을 버리고 `DOMAIN_COMPATIBLE`. 스펙(오류 vs 하루 안으로 감기) 결정 필요. — 정소희(.50) 2026-10-28

## 4. 진행중인 작업

> 각 컨테이너가 자기 소절을 직접 관리한다. 완료되면 지우지 말고 "완료(PR/커밋)"로 갱신.

### .50
- (해당 없음 또는 미기입)
### .51
- (해당 없음 또는 미기입)
### .52
- (해당 없음 또는 미기입)
