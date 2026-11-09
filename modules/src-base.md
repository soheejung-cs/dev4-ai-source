# src/base

> 기준: upstream/develop 95b79e7ed (2026-08-27)

## 1. 소스 목적 및 사용처 (함수별)

전 모듈이 쓰는 기반층: 메모리 관리(`memory_alloc.c`), 에러 처리(`error_code.h` ~1700개 코드,
`error_manager.c`), 락프리 자료구조(`lock_free.c` 레거시 / `lockfree_hashmap.hpp` 현대),
시스템 설정(`system_parameter.c` — base 최대 파일, ~400개 `PRM_ID_*`, cubrid.conf),
직렬화(`packer.hpp`, `object_representation.h`), i18n/타임존, 성능 모니터링, fault injection.

| 함수 | 파일 | 목적 | 주요 사용처(호출자) |
|---|---|---|---|
| `er_set` | error_manager.c:1229 | 스레드별 에러 스택에 에러 세팅+로깅 | 전 모듈(storage, transaction, broker …) |
| `er_errid` | error_manager.c:1826 | 현재 스레드의 마지막 에러 코드 조회 | 전 모듈 — 실패 반환 후 원인 확인 |
| `er_clear` / `er_has_error` | error_manager.c:1202/1918 | 에러 상태 초기화/존재 검사 | 재시도 경로, ASSERT_ERROR 계열 |
| `db_private_alloc` / `db_private_free` | memory_alloc.h 매크로 → memory_alloc.c:420~ | 스레드 사설 힙 할당/해제(NDEBUG 여부로 debug/release 구현 분기) | 서버 측 전 모듈 |
| `free_and_init` / `db_private_free_and_init` | memory_alloc.h:132/124(디버그)·154/148(릴리스) | 해제 후 포인터 NULL 세팅 매크로 | 전 모듈 관용구 |
| `prm_get_integer_value` / `prm_get_bool_value` | system_parameter.c:12358/12373 | `PRM_ID_*` 파라미터 값 조회 | 전 모듈 |
| `sysprm_load_and_init` | system_parameter.c:6471 | cubrid.conf 로드·파라미터 초기화 | boot 경로, broker/broker.c, network_sr.c |
| `fi_test` (`FI_TEST` 매크로) | fault_injection.c / fault_injection.h:37 | 지정 지점에서 fault 주입 실행 | storage/btree.c, 로그·디스크 관리 경로 |
| `fi_handler_random_exit` | fault_injection.c:44(선언)/414(정의) | 확률적 abort/_exit 핸들러 (FI 복구 테스트용) | fi_Handlers 테이블(L59~) 경유 |
| `lf_hash_find` | lock_free.c:2024 | 레거시 락프리 해시 조회 | storage/heap_file.c, transaction/log_tran_table.c |
| `mht_get` / `mht_put` | memory_hash.c:1443/1842 | 범용 체이닝 해시(MHT_TABLE) | object/work_space.c, trigger_manager.c, parser/name_resolution.c |
| `intl_identifier_casecmp` | intl_support.c:2863 | 식별자 대소문자 무시 비교 | parser 전역, 스키마 이름 비교 |
| `restrack_assert` | resource_tracker.hpp:446 | 디버그 자원(페이지 fix·락·메모리) 불균형 assert | resource_tracker 내부 — 디버그 빌드 한정 |

## 2. 분석 내용 (함수별)

> 항목은 함수 단위로 기술한다. 새 분석도 함수명을 앞세워 추가할 것.

### 모듈 일반

- `memory_wrapper.hpp`는 **헤더 파일에 include 금지**, .c/.cpp의 마지막 include만 허용(CI 강제).
  반면 `memory_cwrapper.h`는 헤더에 넣어도 안전(SERVER_MODE에서 malloc/free를 추적 함수로 재정의).
- 새 에러 코드는 6곳 갱신 세트(루트 AGENTS.md 절차).
- 레거시(`lock_free.c`, `perf_monitor.c`)와 현대(C++ hpp — `lockfree_hashmap.hpp`, `perf.hpp`) 계열이
  공존 — 수정 대상이 어느 계열인지 먼저 확인.
- ✅ **리뷰 체크포인트**: 헤더에 `memory_wrapper.hpp`를 include하지 않았는가? .c/.cpp에서는 마지막
  include + 주석인가?
- ✅ **리뷰 체크포인트**: 새 에러 코드가 6곳 모두 갱신됐는가?
- ✅ **리뷰 체크포인트**: 레거시/현대 어느 계열에 맞춰야 하는지 확인했는가?

### er_set / er_errid (error_manager.c)

- `er_set()` 2번째 인자는 항상 `ARG_FILE_LINE` (`__FILE__, __LINE__`로 확장).
- 심각도 순서: `ER_FATAL_ERROR_SEVERITY` > `ER_ERROR_SEVERITY` > `ER_SYNTAX_ERROR_SEVERITY` >
  `ER_WARNING_SEVERITY` > `ER_NOTIFICATION_SEVERITY`.
- 에러를 세팅해야 하는 연산 뒤에는 `ASSERT_ERROR()` / `ASSERT_ERROR_AND_SET(error_code)`.
- ✅ **리뷰 체크포인트**: `er_set()` 호출에 `ARG_FILE_LINE`이 빠지지 않았는가? 실패 경로마다 에러가
  실제로 세팅되는가?

### db_private_alloc / free_and_init (memory_alloc.c/h)

- 실제 백엔드는 모드별로 다름: SERVER는 스레드별 LEA 힙, CS는 `db_ws_alloc` 워크스페이스, SA는 조건부.
- 매크로가 NDEBUG 여부로 `db_private_alloc_debug`(caller file/line 추적) /
  `db_private_alloc_release`로 분기(memory_alloc.c:420~438).

### prm_get_integer_value / sysprm_load_and_init (system_parameter.c)

- 시스템 파라미터 추가는 `PRM_ID_*` 추가 + `prm_Def` 엔트리 + `PRM_LAST_ID` 갱신 세트.
  **`prm_Def[]`(와 `enum param_id`)는 끝에만 추가한다 — PL 서버(SysParam.java)가 ordinal 을 하드코딩** (.50, 4f0f90b62, 2026-09-21; develop
  `2d925cb86` 재확인): system_parameter.h:93-96 "insert it before PRM_LAST_ID and change PRM_LAST_ID to it". `xsysprm_get_pl_context_parameters ()`
  (system_parameter.c:8604)가 파라미터를 `prm_Def[]` 인덱스로 보내고 `pl_engine/pl_server/.../SysParam.java` 가 ordinal 8개를 상수로 박아 둔다 —
  그 위에 넣거나 빼면 ordinal 이 밀려 PL 서버 조회가 빗나가고 SP 컴파일이 전부 중단된다. 배열 뒤 주석과 `static_assert` 8개(:5701-5715, 마지막
  `PRM_ID_STORED_PROCEDURE_DUMP_ICODE == 353`)가 빌드를 깨뜨려 알려 주며, 고칠 곳은 assert 가 아니라 SysParam.java 다(중간 삭제 실례
  `5de66400a` CBRD-27324 가 354→353 으로 함께 고침). — 정소희(.50) 2026-10-28
- **`prm_get_<type>_value()` 는 클라이언트(비 SERVER_MODE)에서 `ALWAYS_INLINE` 배열 인덱스 1회다** (.50, 4f0f90b62, 2026-09-21; develop
  `2d925cb86` 재확인): system_parameter.h:847-852 선언, :862 `prm_get_integer_value` 본문 `PRM_GET_INT (GET_PRM (prm_id)->value)`
  (`GET_PRM(id)` = `&prm_Def[(id)]`, :715) — SERVER_MODE 만 `PRM_SERVER_SESSION` 이면 `prm_get_value ()` 를 거치고, Windows 는 inline 이
  꺼져 있다. 비용 함수가 매번 이렇게 읽는다: `qo_sort_cost` SR_NBUFFERS(query_planner.c:3251), `qo_hjoin_cost` MAX_HASH_LIST_SCAN_SIZE(:4713),
  `qo_follow_cost` PB_NBUFFERS(:4998), `fa551431b`(CBRD-27126) 이후 비용 단가 `cost_*` 매크로(:95-160, 근거 주석 :90-94). 비용 함수용
  캐시 계층은 근거 없는 전역 상태. — 정소희(.50) 2026-10-28
- **병렬 관련 기본값과 CI 빌드 모드**: `parallelism` 기본 **4**(develop `2d925cb86` system_parameter.c:5148), `parallel_scan_page_threshold`
  256. gha-ci 의 suites(shell/sql/medium)는 **debug 빌드**로 돈다(`.github/workflows/gha-ci.yml`) — debug 의 `page_validation_level` 은 모든
  `pgbuf_fix` 를 검사해 release 와 실패 양상이 다를 수 있다(src-storage §2). 텍스트 trace 의 `parallel workers: N` 은 query_dump.c
  (develop :4479·:4502·:4520), JSON 은 `"parallel workers"`(:3784·:3908·:3945) (.52, PR#8034 head `db66b7879`·TC PR#4266, 2026-10-01).
  — 정소희(.50) 2026-10-28
- ✅ **리뷰 체크포인트**: 새 `PRM_ID_*`가 `prm_Def`와 `PRM_LAST_ID`까지 함께 갱신됐는가?

### sysprm_print_parameters_for_qry_string — `PRM_FOR_QRY_STRING` 과 XASL 캐시 키 (system_parameter.c:12222)

- **플랜에 영향 주는 클라이언트 파라미터는 `PRM_FOR_QRY_STRING` 이 있어야 XASL 캐시 키에 들어간다** (.50, 87b25579e, 2026-09-21; develop
  `2d925cb86` 재확인): `sysprm_print_parameters_for_qry_string()`(system_parameter.c:12222, 클라이언트 전용)이 `PRM_PRINT_QRY_STRING`(:984-988 —
  CS 는 `PRM_IS_DIFFERENT && PRM_IS_FOR_QRY_STRING`, SA 는 FOR_QRY_STRING 전부)인 것만 출력 → `parser_print_tree ()` 가
  `PT_PRINT_DIFFERENT_SYSTEM_PARAMETERS` 일 때 `?` 뒤에 붙임(parse_tree_cl.c:3119-3124) → `execute_statement.c` SHA1. `PRM_DIFFERENT` 는 모든
  `prm_set_*_value()` 끝의 `sysprm_update_flag_different()`(:11088 — CS_MODE 에서 FOR_QRY_STRING·FOR_HA_CONTEXT 파라미터만)로 갱신. 루프 상한
  `MAX_SYSTEM_PARAMS = prm_Def_size`(:5719-5720, 동적). 전례 `max_hash_list_scan_size`(:3567-3569), `fa551431b` 의 `cost_*` 도 이 플래그를 단다.
  없으면 단가를 바꾼 세션이 옛 플랜을 재사용(재현 `projects/CBRD-27126/repro/cache_repro.sql`). 이 출력 플래그를 켜는 곳은 SELECT 준비
  (`do_prepare_select`, execute_statement.c:15376) 하나다. — 정소희(.50) 2026-10-28

### lf_hash_find (lock_free.c) — 락프리 공통 규칙

- 접근 전 반드시 트랜잭션 시작, 끝나면 종료. retire된 노드는 모든 동시 리더가 retirement ID를
  지나야 회수된다. 현대 구조는 `lockfree::tran::system`, 레거시는 `LF_TRAN_SYSTEM`/`LF_TRAN_ENTRY` —
  같은 개념의 C API.
- ✅ **리뷰 체크포인트**: 락프리 자료구조 접근이 트랜잭션 시작/종료로 감싸져 있는가?

### fi_handler_random_exit / fi_test (fault_injection.c)

- `fi_handler_random_exit`: fault_injection.c:44 선언, L414 정의. `rand () % mod_factor`(인자 없으면
  기본 20000)가 0이면 `er_print_callstack ("FAULT INJECTION: RANDOM EXIT")` 후
  `PRM_ID_FAULT_INJECTION_ACTION_PREFER_ABORT_TO_EXIT`가 켜져 있으면 `abort ()`, 아니면 `_exit (0)`.
- `fault_injection_test` 파라미터는 system_parameter.c에 실재(`PRM_NAME_FAULT_INJECTION_TEST` L645,
  `PRM_ID_FAULT_INJECTION_TEST` prm_Def L4008).
- `FI_TEST`/`FI_TEST_ARG` 매크로는 릴리스(NDEBUG) 빌드에서 `(NO_ERROR)` no-op(fault_injection.h:37/43).
- **코어 판정 예외**: FI 복구 시나리오가 켜진 테스트에서 나온 abort/코어는 **고의 주입**이다 —
  크래시 조사 시 fault injection 활성 여부(`fault_injection_test` 등)를 먼저 확인하고, 해당 코어는
  제품 버그 판정에서 예외로 취급할 것.

### restrack_assert (resource_tracker.hpp) — 릴리스 벤치마크 결과는 자원 수명 변경의 증거가 될 수 없다 (PR#7658)

- `restrack_assert`는 resource_tracker.hpp:446에 정의되어 있고 본문 전체가 `#if !defined (NDEBUG)` ~
  `#endif`(같은 파일 448~457행)로 감싸여 있어 릴리스 빌드에서는 호출부가 통째로 no-op이 된다.
  (원 메모의 `:455` 참조는 부정확했고, 95b79e7ed에서 재검증 — 정의 :446, 가드 448~457행.
  원 기준: CBRD-27094 @ faf5a3b2a.)
- 귀결: 릴리스 빌드에서 돌린 벤치마크는 페이지 fix 누락이나 `db_private_alloc` 해제 누락을 원리상
  한 건도 검출하지 못한다. 실제로 PR#7658은 릴리스 TPC-H에서 22/22 질의 결과 바이트가 동일했는데도
  디버그 CI에서 abort가 쏟아졌다. 이 계열 버그의 재현·검증은 반드시 디버그 빌드 + CTP로 해야 하며,
  릴리스 성능·정합성 수치는 반증이 되지 않는다.
- 디버그 빌드의 resource tracker는 `push_track()`/`pop_track()` 쌍으로 페이지 fix/락 불균형을 pop
  시점에 검출한다.
- ✅ **리뷰 체크포인트**: 자원(페이지 fix, private 메모리) 획득/해제 경로를 건드린 변경에 "릴리스에서
  정상 동작하고 성능도 동일하다"만 근거로 달려 있으면 불충분하다고 지적하고 디버그 빌드 CTP 결과를
  요구할 것.

- **debug(SERVER_MODE, `!NDEBUG` — CI 의 optdebug 포함) 서버는 요청마다 `db_private_alloc` 을 추적하고, 요청 끝에 남은 할당을 덤프한 뒤 abort 한다 — release 는 요청의 private heap 을 비워 요청 안의 누수가 요청을 넘지 않는다** (.51, develop `226352283`, 2026-11-03): 요청 끝 `net_server_request ()` → `pop_resource_tracks ()`(thread_entry.cpp:443)가 남은 할당을 서버 에러 로그에 덤프(`tracked res_ptr=… first_caller=<파일:줄>`)한 뒤 `restrack_assert (false)`(resource_tracker.hpp:426·455)로 abort 한다. 억제는 기본 꺼짐. release 는 그 뒤 `db_clear_private_heap ()`(network_sr.c:949)이 요청의 private heap 을 비운다. abort 스택은 서버 `abort_handler` 가 `$CUBRID/log/coredump/cub_server_<시각>.coredump` 에 남긴다(src-executables §2 「abort_handler」). 실측: 분할 부모 2개 표 INSERT 1행 → 덤프 `xasl_stream.cpp:85·244·254`·`heap_file.c:10611`(파티션 캐시 미적중이면 `heap_get_class_partitions` 쪽 할당까지 15건) — CBRD-27845(src-transaction §3). — 정소희(.52) 2026-11-09

### mht_get_hash_number (memory_hash.c) — DB_VALUE 해시의 문자열 처리

> 아래 세 항목의 줄 번호는 `89722cf4e` 기준이다. develop `2d925cb86` 에서 language_support.c·object_primitive.c 는 그대로이고
> memory_hash.c 만 위쪽에 함수 하나가 늘어 27줄 밀렸다(본문 동일). SERVER·SA·CS 공통 코드.

- **`mht_get_hash_number ()` 는 문자열의 뒤 ASCII 공백(0x20)을 떼고 해시하고, 빈 문자열·공백만 있는 값은 0 을 돌려준다** (.50,
  `89722cf4e`, 2026-10-27 단위 실측): memory_hash.c:2468-2477 루프(주석 "only the trailing ASCII space is ignored"), :2479-2481
  `hashcode = 0`(develop :2495-2508). 기본 `ignore_trailing_space=no` 의 VARCHAR 비교는 `'a'`·`'a '` 를 다르게 본다 — `lang_fastcmp_byte ()` 가
  앞부분이 같으면 길이 차를 돌려주고(language_support.c:5574-5577), 인덱스 키 비교 `mr_cmpval_string ()` 도 같은 기준이다
  (object_primitive.c:11416 의 static `ti`, :11472 `QSTR_COMPARE`). CHAR 만 비교도 뒤 공백을 무시한다(object_primitive.c:12401-12404).
  해시 테이블 버킷으로 쓰면 충돌이 늘 뿐 무해하지만(같음은 비교가 다시 판정), **해시 값의 개수로 고유값을 세는 곳(distinct 추정)에 쓰면 뒤
  공백만 다른 VARCHAR 가 접혀 과소**가 된다. — 정소희(.50) 2026-10-28
- **`mht_get_hash_number ()` 의 DOUBLE(·MONETARY) 해시는 32비트 반쪽마다 하위 4비트를 버리고(`& 0xFFFFFFF0`) FLOAT 도 같은 마스크다 — 1 ulp 차이는 대개 같은 해시지만 16-ulp 묶음 경계를 넘으면 갈린다; -0.0 과 +0.0 은 비트가 달라 다른 해시** (.52, develop `d6ca98121`·PR#8213 head memory_hash.c ~2400-2416, 2026-10-28): CONNECT BY 사이클 해시(`qexec_connect_by_hash_column`)는 0 을 먼저 접는다(query_executor.c, PR#8213 head 20571 — #8213 은 `52193efa9` 로 머지). 해시 키에 DOUBLE 을 쓰는 곳은 이 두 가지를 같이 본다. — 정소희(.50) 2026-11-03

### lang_mht2str_byte / mht_2str_pseudo_key — 콜레이션 문자열 해시 (language_support.c:5753, memory_hash.c:183)

- **콜레이션 문자열 해시는 PJW/ELF 계열이라 상위 니블이 늘 0(사실상 28비트)이고, 자릿수가 같은 정형 문자열이 구조적으로 충돌한다** (.50,
  `89722cf4e`, 2026-10-27 단위 실측): `lang_mht2str_byte ()`(language_support.c:5753) 의 `ADD_TO_HASH`(:3240-3250)가 4비트 이동 + 상위 니블
  접기, iso88591_bin 은 `mht_2str_pseudo_key ()`(memory_hash.c:183, 같은 hashpjw). `'2015-01-20'` = `'2025-01-10'`, 날짜 문자열 4,096일 →
  해시 3,809개; 같은 집합을 바이트 FNV 로 해시하면 충돌 0. 해시 테이블엔 성능 문제일 뿐이지만, 표본 해시의 고유 개수로 추정하는 Duj1
  식에서는 표본 4,096개 안 충돌 4쌍만으로 고유값 100만 열이 677,357 로 내려간다. — 정소희(.50) 2026-10-28

### lang_fastcmp_byte / lang_fastcmp_ko — 이진 콜레이션의 문자열 비교 (language_support.c:5535, :6138)

- **이진 콜레이션의 비교는 공백을 NUL 과 같은 0 가중치로 본다** (.50, `89722cf4e`, 정적 + 2026-10-27 단위 실측): `lang_fastcmp_byte ()`
  (language_support.c:5535)가 `ASCII_SPACE` 를 `ZERO` 로 바꿔 비교한다(:5547-5549·:5557-5559) — utf8_bin·iso88591_bin 에서 `'a b'` =
  `'a\0b'`. euckr_bin 의 `lang_fastcmp_ko ()`(:6138)는 ASCII 공백과 EUC 공백 쌍 `0xA1A1` 을 0 단위로 본다(:6155·:6159). binary 콜레이션
  `lang_fastcmp_binary ()` 는 뒤 NUL 만 무시한다(단위 실측). 그래서 "비교의 같음과 맞는 해시" 를 이진 콜레이션에 만들려면 바이트가 아니라
  이 0 단위로 섞어야 한다(그렇게 섞은 해시는 반례 탐색에서 utf8_bin VARCHAR 6/18·CHAR 13/9 → 0/0). — 정소희(.50) 2026-10-28

### or_mvcc_get_repid_and_flags / or_mvcc_get_header — 힙 레코드 첫 접근의 DRAM 미스 (object_representation.c)

- **힙 스캔의 레코드 첫 접근은 `or_mvcc_get_repid_and_flags ()` 의 첫 load 에서 DRAM 미스로 드러난다** (.51, PR#8196 헤드 `46fd2be49` release 프로파일 — 측정 조건은 src-query §2 「페이지 배치 실행(expr_batch) 프로파일」, 2026-10-31): F01(`count(*), sum(l_extendedprice) … where l_quantity < 24`, 직렬 6.0초)에서 자기 시간 20.0%, 그 함수 샘플의 98.3% 가 `mov (%rdx),%eax`(레코드 첫 4바이트) 한 명령이다. 함수 본체는 load 하나라 명령 비용이 아니라 대기다. 같은 질의의 `or_mvcc_get_header ()` 7.0%(레코드마다 `or_init` + 다른 번역 단위 함수 chn·insid·delid·prev_lsa 호출). 배치(`heap_page_collect_visible ()`)와 행 경로 둘 다 레코드마다 이 파서를 부른다. 하드웨어 프리페처는 4KB 경계를 넘지 않아 16KB 페이지 안에서도 네 번 새로 시작한다(일반 사실). 이 측정 뒤 PR#8196 은 배치가 페이지의 첫 묶음을 모을 때(`*slot == 0`) 페이지 전체를 64바이트 줄마다 prefetch 한다 — `heap_page_prefetch ()`(develop `1802aa581` heap_file.c:8203, 호출 :8335, 2026-11-03 확인; .51 실측 LLC 미스 36.0M → 6.8M). 행 경로 prefetch·배치 전용 얕은 헤더 파서는 미측정. — 정소희(.50) 2026-11-03

## 3. 예비 이슈 사항

> 미수정 버그·의심·문서 정정 후보·구조적 한계. 해소되면 삭제가 아니라 "해소됨(커밋/PR)"로 갱신.

- **euckr_bin 의 같음은 뒤 NUL 에서 추이적이지 않다 — `'a'` = `'a\0'`, `'a\0'` = `'a '`, 그런데 `'a'` ≠ `'a '`(ti off VARCHAR)** —
  **미수정**, 이슈 없음(영향 미조사) (develop `2d925cb86` 재확인 2026-10-28 — 정적: language_support.c 는 `89722cf4e` 이후 변경 없음) (.50,
  `89722cf4e`, 2026-10-27 단위 실측, 공백·NUL·EUC 공백 19~26개 문자열 전 쌍 탐색): `lang_fastcmp_ko ()` 의 길이가 다른 꼬리 처리
  (language_support.c:6188 이후) 중 어느 줄이 갈리는지는 정적으로 따라가지 않았다(단위 결과만). 같음이 추이적이지 않으므로 이 콜레이션에서는
  어떤 해시도 비교와 완전히 맞출 수 없다(뒤 NUL 5쌍이 남는다) — 해시를 비교에 맞추는 작업은 euckr_bin 뒤 NUL 을 예외로 적는다. 정렬·인덱스
  순서에 미치는 영향은 보지 않았다. — 정소희(.50) 2026-10-28

## 4. 진행중인 작업

> 각 컨테이너가 자기 소절을 직접 관리한다. 완료되면 지우지 말고 "완료(PR/커밋)"로 갱신.

### .50
- (해당 없음 또는 미기입)
### .51
- (해당 없음 또는 미기입)
### .52
- (해당 없음 또는 미기입)
