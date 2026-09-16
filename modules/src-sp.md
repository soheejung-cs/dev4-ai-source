# src/sp

> 기준: upstream/develop 95b79e7ed (2026-08-27)

## 1. 소스 목적 및 사용처 (함수별)

C 서버 ↔ Java PL 엔진 브리지 (JNI/Unix 소켓). `sp_catalog.cpp`(SP 카탈로그), `pl_sr.cpp`(서버 측
PL 서버 수명주기), `pl_sr_jvm.cpp`(JVM 기동), `pl_executor.cpp`(실행 오케스트레이션),
`pl_comm.c`(소켓 통신), `pl_connection.cpp`(연결 풀), `pl_signature.cpp`(시그니처·마샬링),
`pl_file.c`(JAR 관리), `jsp_cl.cpp`(클라이언트 측 API), `method_invoke_group.cpp`(src/method와 공유).

| 함수 | 파일 | 목적 | 주요 사용처(호출자) |
|---|---|---|---|
| `jsp_create_stored_procedure` | `jsp_cl.cpp:1000` | CREATE PROCEDURE/FUNCTION 문 처리(클라이언트) | `src/query/execute_statement.c` |
| `jsp_drop_stored_procedure` | `jsp_cl.cpp:837` | DROP PROCEDURE/FUNCTION 문 처리 | `src/query/execute_statement.c` |
| `jsp_call_stored_procedure` | `jsp_cl.cpp:732` | CALL 문의 클라이언트 측 실행 진입 | `src/query/execute_statement.c` |
| `sp_add_stored_procedure` / `_argument` / `_code` | `sp_catalog.cpp` (`sp_catalog.hpp:159-161`) | SP 시스템 카탈로그 행 삽입 | `jsp_create_stored_procedure` 경로 |
| `pl_server_init` / `pl_server_destroy` | `pl_sr.cpp` (`pl_sr.h:40-41`) | PL 서버(자바 프로세스) 초기화/종료 | `src/transaction/boot_sr.c:2248`(log_initialize보다 먼저 호출) |
| `pl_server_wait_for_ready` | `pl_sr.cpp` (`pl_sr.h:42`) | PL 서버 기동 대기 | 부트/SP 실행 준비 경로 |
| `get_connection_pool` | `pl_sr.cpp` (`pl_sr.h:44`) | 전역 PL 연결 풀 획득 | `pl_executor.cpp`, `pl_session.cpp` |
| `pl_start_jvm_server` | `pl_sr_jvm.cpp` (`pl_sr_jvm.h:30`) | JVM 내장 기동(server_name, path, port) | `pl_server_init` 경로 |
| `pl_connect_server` | `pl_comm.c:79` (UDS :256 / TCP :288) | PL 엔진 소켓 연결(UDS 우선, TCP 폴백) | `pl_connection.cpp` 연결 생성 |
| `cubpl::connection_pool::claim` / `retire` | `pl_connection.cpp` (`pl_connection.hpp:78-79`) | 연결 풀에서 연결 획득/반환 | `pl_executor.cpp` 실행 경로 |
| `cubpl::executor::execute` | `pl_executor.cpp:274` | SP 1회 실행 오케스트레이션(`invoke_java` 패킹 :45~) | `spl_call`(`network_interface_sr.cpp:11209`), method 경로 |
| `cubmethod::method_invoke_group::begin` / `execute` | `method_invoke_group.cpp:198` / `:114` | 스캔 중 메서드 호출 그룹 수명주기/실행 | `src/method/method_scan.cpp`, `query_method.cpp` |

## 2. 분석 내용 (함수별)

> 항목은 함수 단위로 기술한다 — 각 항목의 제목/선두가 함수·파일명이다. 새 분석도 함수명을 앞세워 추가할 것.
> (아래 주의점·리뷰 체크포인트의 원본: src/sp/AGENTS.md 증류)

### 모듈 일반

- PL 엔진은 별도 Java 프로세스 — SP 실행 전에 떠 있어야 한다.
- JNI 호출은 JVM 오버헤드 — SP 호출은 네이티브 SQL 함수보다 훨씬 느림.
- 접두사: `sp_`(카탈로그/실행), `jsp_`(JNI/통신), `pl_`(PL 엔진 프로토콜).
- 에러 전파: Java 예외 → C 측 `er_set()` 에러 코드.
- ✅ **리뷰 체크포인트**: Java 예외가 `er_set()`으로 번역되어 C 측 에러 관습을 따르는가?
- ✅ **리뷰 체크포인트**: PL 엔진 미기동/연결 실패 시의 에러 처리가 있는가?

### pl_signature (pl_signature.cpp)

- SQL↔Java 타입 불일치가 흔한 버그 원인 — `pl_signature.cpp` 매핑 확인
  (DB_INT↔int/Integer, DB_STRING↔String, DB_NUMERIC↔BigDecimal, DB_DATE↔java.sql.Date,
  결과셋↔java.sql.ResultSet).
- ✅ **리뷰 체크포인트**: 타입 매핑 변경/추가가 `pl_signature.cpp`와 `pl_struct_compile.cpp` 양쪽에 일관되게 반영됐는가?

### connection_pool::claim / retire (pl_connection.cpp)

- PL 엔진 연결 풀은 `pl_connection.cpp` 관리 — **연결 누수는 행(hang)을 유발**.
- ✅ **리뷰 체크포인트**: 연결 획득 경로마다 반환(해제)이 보장되는가(누수 시 hang)?

### pl_connect_server (pl_comm.c)

- 통신은 Unix 도메인 소켓(기본) 또는 원격 PL 엔진용 TCP.

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
