# src/broker

> 기준: upstream/develop 95b79e7ed (2026-08-27)

## 1. 소스 목적 및 사용처 (함수별)

별도 프로세스 아키텍처: 브로커가 CAS(Common Application Server) 워커 프로세스를 생성·관리.
`broker.c`(포트 리슨·디스패치), `cas.c`(클라이언트 세션당 1 프로세스), `cas_execute.c`(CAS 내 SQL 실행),
`cas_function.c`(프로토콜 함수 디스패치), `broker_shm.c`(브로커↔CAS 공유 메모리 IPC:
`T_SHM_BROKER`, `T_SHM_APPL_SERVER`), `broker_config.c`(`cubrid_broker.conf`),
`shard_metadata.c`/`shard_proxy.c`(샤딩).

| 함수 | 파일 | 목적 | 주요 사용처(호출자) |
|---|---|---|---|
| `main` | `broker.c:461` | 브로커 프로세스 진입점 — `broker_init_shm()`(:482) 후 리슨/디스패치 | OS 프로세스 기동(`cub_broker`) |
| `broker_init_shm` | `broker.c:2909` | 브로커 공유 메모리 부착·초기화 | `broker.c` main(:482) |
| `main` / `cas_main` | `cas.c:209` / `:262` | CAS 워커 프로세스 진입점(샤드 모드는 `shard_cas_main` :251 분기) | 브로커가 fork/exec |
| `process_request` | `cas.c:836` | CAS의 클라이언트 요청 1건 처리 루프 본체 | `cas_main` 루프 (게이트웨이 변형: `cas_cgw.c:476`) |
| `fn_prepare` / `fn_execute` | `cas_function.c:216` / `:330` | 프로토콜 함수 테이블의 prepare/execute 핸들러 | `process_request` 디스패치 |
| `ux_prepare` | `cas_execute.c:621` | SQL prepare 실제 구현(스키마 정보 응답 구성) | `fn_prepare` |
| `ux_execute` | `cas_execute.c:995` | SQL execute 실제 구현 | `fn_execute` |
| `uw_shm_open` / `uw_shm_create` | `broker_shm.c:98/:208`(win: :142/:337) | 공유 메모리 열기/생성 | 브로커·CAS·모니터링 유틸 전반 |
| `broker_config_read` | `broker_config.c:1476` | `cubrid_broker.conf` 파싱 → `T_BROKER_INFO[]` | `broker.c`, `broker_admin.c`, `broker_monitor.c` |
| `cas_error_log_write` | `cas_error_log.c:167` | CAS 전용 에러 로그 기록 | CAS 실행 경로 전반(`er_set()` 대신) |
| `main` | `broker_admin.c:77` | `cubrid broker` 관리 명령 진입점 | OS(서비스 유틸 경유) |
| `main` | `broker_monitor.c:485` | `broker_monitor` 유틸 진입점 | OS |
| `main` | `shard_proxy.c:165` | 샤드 프록시 프로세스 진입점 | 브로커(샤드 구성 시) |
| `shard_metadata_initialize` | `shard_metadata.c:434` | 샤드 라우팅 메타데이터 초기화 | `shard_shm.c:304` |

## 2. 분석 내용 (함수별)

> 항목은 함수 단위로 기술한다 — 각 항목의 제목/선두가 함수·파일명이다. 새 분석도 함수명을 앞세워 추가할 것.
> (아래 주의점·리뷰 체크포인트의 원본: src/broker/AGENTS.md 증류)

### 모듈 일반

- 브로커와 CAS는 별도 프로세스 — **공유 메모리로만 통신**. CAS는 브로커에서 fork — 공유 메모리
  동기화에 신중해야 한다.
- 최상위 `broker/`는 CMake 타깃일 뿐, 실제 코드는 `src/broker/`.
- 샤드 코드(`shard_*.c`)는 이 모듈 내 상당한 서브시스템.
- 접두사: `cas_`, `broker_`, `shm_`.
- ✅ **리뷰 체크포인트**: fork 이후 공유 상태 접근에 동기화가 있는가?

### uw_shm_open / uw_shm_create (broker_shm.c)

- `T_BROKER_INFO`, `T_APPL_SERVER_INFO`는 공유 메모리의 packed struct — **정렬(alignment)이 중요**.
- ✅ **리뷰 체크포인트**: 공유 메모리 구조체 변경이 packed 레이아웃/정렬을 깨지 않는가? 브로커·CAS 양쪽이 같은 레이아웃을
  보는가?

### cas_error_log_write (cas_error_log.c)

- CAS는 자체 에러 처리 사용: `cas_error_log_write()` — `er_set()` 아님.
- ✅ **리뷰 체크포인트**: CAS 코드에서 `er_set()` 대신 `cas_error_log_write()`를 쓰는가?

### broker_config_read (broker_config.c)

- ✅ **리뷰 체크포인트**: 설정 항목 추가 시 `broker_config.c` 파싱이 갱신됐는가?

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
