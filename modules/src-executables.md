# src/executables

> 기준: upstream/develop 95b79e7ed (2026-08-27)

## 1. 소스 목적 및 사용처 (함수별)

모든 CUBRID 바이너리의 진입점. `server.c`(`cub_server`), `csql.c`/`csql_launcher.c`(csql 셸),
`master.c`(`cub_master` — 호스트의 서버 프로세스 관리)·`master_heartbeat.c`(HA),
`util_service.c`(`cubrid` 서비스 명령), `util_admin.c`(관리 유틸 디스패치), `unloaddb.c`, `compactdb.c`,
`util_common.c`(공용 헬퍼).

| 함수 | 파일 | 목적 | 주요 사용처(호출자) |
|---|---|---|---|
| `main` | `server.c:276` | `cub_server` 진입점 — `net_server_start()` 호출(:325) | OS 프로세스 기동 |
| `main` | `master.c:1244` | `cub_master` 진입점 — HA 시 `hb_master_init()`(:1340) | OS 프로세스 기동 |
| `main` | `util_service.c:534` | `cubrid` 서비스 명령 진입점 | OS; 내부 디스패치 `process_service`(:1263)/`process_server`(:1628) |
| `main` | `util_admin.c:1095` | 관리 유틸리티(`cubrid <util>`) 디스패치 진입점 | `ua_Utility_Map[]`(:968)에서 유틸 검색 후 실행 |
| `ua_Utility_Map[]` | `util_admin.c:968` | 유틸 이름→함수·인자맵 등록 테이블(`UTIL_MAP`) | `util_admin.c` main/디스패치(:1115, :1136, :1223) |
| `main` | `csql_launcher.c:114` | csql 실행 파일 진입점 — CS/SA 라이브러리에서 `csql` 심볼을 동적 로드(`DSO_HANDLE`) 후 호출 | OS 프로세스 기동 |
| `csql` | `csql.c:3230` | csql 본체 진입(인자 구조체 `CSQL_ARGUMENT`) — `start_csql()`(:713) 호출(:3492) | `csql_launcher.c`(동적 로드) |
| `start_csql` | `csql.c:713` | csql 메인 루프(입력 읽기·세션 명령·실행) | `csql()` |
| `csql_execute_statements` | `csql.c:2183` | 입력 스트림의 SQL 문장 배치 실행 | `start_csql` 경로 |
| `csql_do_session_cmd` | `csql.c:1084` | `;`로 시작하는 세션 명령 처리 | `start_csql` 입력 루프 |
| `utility_initialize` | `util_common.c:72` | 유틸리티 공통 초기화(메시지 카탈로그 등) | 각 유틸 진입점 |
| `unloaddb` | `unloaddb.c:116` | `unloaddb` 유틸 본체(`UTIL_FUNCTION_ARG`) | `ua_Utility_Map[]` 경유 디스패치 |
| `compactdb` | `compactdb.c:98`(SA) / `compactdb_cl.c:787`(CS) | `compactdb` 유틸 본체 — SA/CS 두 구현 | `ua_Utility_Map[]` 경유 디스패치 |
| `hb_master_init` | `master_heartbeat.c:5250` | 마스터 프로세스 HA 하트비트 초기화 | `master.c:1340` |
| `hb_reload_config` | `master_heartbeat.c:5576` | HA 설정 리로드 | `cubrid heartbeat reconfig` 경로 |

## 2. 분석 내용 (함수별)

> 항목은 함수 단위로 기술한다 — 각 항목의 제목/선두가 함수·파일명이다. 새 분석도 함수명을 앞세워 추가할 것.
> (아래 주의점·리뷰 체크포인트의 원본: src/executables/AGENTS.md 증류)

### 모듈 일반

- 링크 대상 구분: 독립형 유틸(`loaddb`/`unloaddb`/`compactdb`)은 `cubridsa`(SA_MODE),
  클라-서버 유틸은 `cubridcs`(CS_MODE).
- 새 유틸리티 추가는 진입점 생성 + CMakeLists.txt 등록 + `util_common.c` 서브커맨드 등록.
- ✅ **리뷰 체크포인트**: 새/변경 유틸리티가 올바른 라이브러리(SA vs CS)에 링크되는가?
- ✅ **리뷰 체크포인트**: 서브커맨드 등록(`util_common.c`)과 CMake 타깃이 함께 갱신됐는가?

### loaddb 진입 (util_admin.c → src/loaddb/load_db.c)

- `loaddb`는 standalone/client-server 두 모드 — 코드 경로가 다르다.
  (실제 본체 `loaddb_dba`/`loaddb_user`는 `src/loaddb/load_db.c:953/:966`에 있고,
  `util_admin.c:989`의 `ua_Utility_Map[]`에 `loaddb_user`로 등록된다.)
- ✅ **리뷰 체크포인트**: loaddb 관련 수정이 두 실행 모드 모두에서 검토됐는가?

### main (master.c)

- `master.c`는 데이터베이스 서버가 아니라 서버 프로세스들의 관리자.
- **`auto_restart_server` 는 master 가 기동할 때 한 번, DB 섹션 없이 읽는다** (.51, `959314906`, 2026-10-21~23 · develop `2d925cb86` 재확인): `main` 이
  `master_util_config_startup ((argc > 1) ? argv[1] : NULL, …)` → `sysprm_load_and_init (db_name, …)`(master_util.c:42-44)로 파라미터를 읽고
  `auto_Restart_server = prm_get_bool_value (PRM_ID_AUTO_RESTART_SERVER)`(master.c:1521)를 그때 한 번 정한다. master 는 보통 인자 없이 뜨므로 `[common]` 값만 보이고
  DB 섹션(`[@db]`) 값은 무시된다. 관찰(.51 1회): 되살린 서버가 master 에 등록되기 전에 `cubrid server start` 를 겹쳐 부르면 되살린 서버가 등록하지 못해 −677 이
  2분쯤 이어졌다. — 정소희(.50) 2026-10-28

### csql / start_csql (csql.c)

- csql은 자체 미니 프레임워크(session, result display, input handling) — 함수 접두사 `csql_`.

### optimizedb / optimizedb_update_class_statistics (util_sa.c:1534/:1493) — `-n` 과 히스토그램

- **`optimizedb -n <class>` 는 develop `bcd6c5936` 까지 히스토그램을 만들지 않았다 — `dce40879e`(CBRD-27249 PR#8166, 2026-10-19)부터 SQL 단일 클래스 경로와 같은
  순서다** (.51, 2026-10-14 · develop `2d925cb86` 재확인): 예전 `optimizedb ()` 는 `sm_update_statistics (class_mop, STATS_WITH_SAMPLING)` 만 불렀고 이 함수엔
  히스토그램 경로가 없었다(히스토그램은 전체 경로 `sm_update_all_statistics` → `update_histogram_for_all_classes` 만 만들었다). 지금은
  `optimizedb_update_class_statistics ()`(:1493)가 `do_update_stats` 의 단일 클래스 분기를 따라 히스토그램 헬퍼(`update_or_drop_histogram_helper
  (DO_HISTOGRAM_CREATE)`, 클래스 통계도 자기 스캔으로 갱신)를 먼저 부르고 `ER_OBJ_INVALID_ARGUMENTS` 면 `sm_update_statistics` 로 폴백한다. `--no-histogram` 이면
  `sm_update_statistics` 만, 인자 없는 전체 실행은 `sm_update_all_statistics (STATS_WITH_SAMPLING, 0, no_histogram, …)`(:1701)에 `--no-histogram-classes` 제외 목록을
  넘긴다. 전체 경로의 클래스당 이중 수집은 src-storage §3. — 정소희(.50) 2026-10-28
  - ✅ **리뷰 체크포인트**: `do_update_stats` 의 단일 클래스 분기를 고치면 `optimizedb_update_class_statistics` 도 같이 고친다 — 함수 주석이 둘을 "keep the two in
    step" 으로 묶어 둔다.

### abort_handler (server.c:226, debug 전용) — SIGABRT 의 전파

- **debug 서버의 SIGABRT 핸들러는 붙은 로컬 클라이언트(CAS 등)에 SIGABRT 를 보낸 뒤 자신도 abort 한다** (.51, `959314906`, 2026-10-21~23 · develop `2d925cb86`
  재확인): `!NDEBUG` 에서만 `register_abort_signal_handler (SIGABRT)`(:287)로 걸리고(release 는 `register_fatal_signal_handler`), 재기동이 끝난 서버면
  `logtb_collect_local_clients` 로 모은 pid 마다 `kill (client_pid, SIGABRT)`(:254) 뒤 콜스택을 찍고 `abort ()` 한다. 장애 주입의 기본 동작
  `fault_injection_action_prefer_abort_to_exit`(숨은 파라미터, 기본 yes — system_parameter.c:4035~)와 겹치면 주입마다 CAS 코어가 `$CUBRID/log/coredump` 에 쌓인다 —
  주입 테스트는 `no` 로. — 정소희(.50) 2026-10-28

## 3. 예비 이슈 사항

> 미수정 버그·의심·문서 정정 후보·구조적 한계. 해소되면 삭제가 아니라 "해소됨(커밋/PR)"로 갱신.

- (현재 등록된 예비 이슈 없음)

## 4. 진행중인 작업

> 각 컨테이너가 자기 소절을 직접 관리한다. 완료되면 지우지 말고 "완료(PR/커밋)"로 갱신.

### .50
- (해당 없음 또는 미기입)

### .51
- PR#7561 (CBRD-27126): `cubrid calibratedb` 신설(util_sa.c, SA 전용) — O_DIRECT 마이크로벤치 +
  스크래치 테이블 캘리브레이션으로 비용 파라미터 권장값 보고. 구현 완료, 사용자 검토 대기.

### .52
- (해당 없음 또는 미기입)
