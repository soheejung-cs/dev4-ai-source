# src/communication

> 기준: upstream/develop 95b79e7ed (2026-08-27)

## 1. 소스 목적 및 사용처 (함수별)

네트워크 인터페이스 층: 요청 패킹/언패킹, 서버 디스패치 테이블, method/xs 콜백 글루, 클라이언트
히스토그램. `network.h`(`NET_SERVER_REQUEST_LIST`·요청 상수), `network_sr.c`(`net_server_init()`,
`net_Requests[]` 디스패치 테이블), `network_interface_sr.cpp`(서버 핸들러; develop 기준 .cpp),
`network_interface_cl.c`(클라이언트 인터페이스), `network_callback_cl.cpp`/`network_callback_sr.cpp`.

| 함수 | 파일 | 목적 | 주요 사용처(호출자) |
|---|---|---|---|
| `net_server_init` | `network_sr.c:75` | `net_Requests[]` 디스패치 테이블 구성(핸들러+`action_attribute`) | `net_server_start` 초기화 경로 |
| `net_server_request` | `network_sr.c:796` | 서버 요청 메인 디스패처(권한/트랜잭션 속성 검사 후 핸들러 호출) | `css_initialize_server_interfaces(net_server_request)`(:1143)로 등록 → css 워커 스레드 |
| `net_server_start` | `network_sr.c:1064` | 서버 기동 총괄(er/스레드/파라미터 init → `css_init`(:1154)) | `src/executables/server.c:325` |
| `net_server_conn_down` | `network_sr.c:1046` | 연결 다운 시 트랜잭션 정리 훅 | css 연결 종료 경로 |
| `net_client_request` | `network_cl.c:579` | 클라이언트 요청 송신+응답 수신의 공통 본체 | `network_interface_cl.c`(약 180회 사용) |
| `net_client_init` | `network_cl.c:3619` | 클라이언트 네트워크 초기화(`css_client_init` 경유 :3625) | `boot_cl.c` 접속 경로 |
| `get_net_request_name` | `network_common.cpp:42` | 요청 인덱스→이름 문자열(로깅/히스토그램) | `net_server_request` 디버그 로그, 히스토그램 |
| `xs_callback_send` / `xs_callback_receive` | `network_callback_sr.cpp:35/:60`(서버) · `:90/:96`(비서버 변형) | 서버→클라이언트 method/xs 콜백 송수신 | `xs_receive_data_from_client`(`network_interface_sr.cpp:7191`) 등 |
| `xs_queue_send` | `network_callback_cl.cpp:68` | 클라이언트 측 콜백 응답 큐잉 | method 콜백 처리(`src/method/query_method.cpp` 경로) |
| `net_histo_ctx` | `network_histogram.hpp:46` | 클라이언트 요청별 히스토그램 수집(`NET_SERVER_REQUEST_END` 크기 배열) | CS/SA 클라이언트 perf 덤프 |
| `spl_call` | `network_interface_sr.cpp` (grep `spl_call`) | SP 호출 서버 핸들러 — `cubpl::executor` 생성·실행(:11209 부근) | `net_Requests[]` 디스패치 |
| `sloaddb_*` 핸들러 | `network_interface_sr.cpp:10842~11089` | loaddb CS 모드 요청 핸들러 묶음 | `net_Requests[]` 디스패치 |

## 2. 분석 내용 (함수별)

> 항목은 함수 단위로 기술한다 — 각 항목의 제목/선두가 함수·파일명이다. 새 분석도 함수명을 앞세워 추가할 것.
> (아래 주의점·리뷰 체크포인트의 원본: src/communication/AGENTS.md 증류)

### 모듈 일반

- `_cl` = CS/SA, `_sr` = SERVER/SA. `network_request_def.hpp`는 `#error`로 SERVER_MODE를 강제.
- 빌드 타깃별 파일 포함이 다르다(예: `network_common.cpp`는 서버·CS만, `network_callback_sr.cpp`는
  서버·SA, `network_histogram.cpp`는 CS·SA만) — 표 확인 필요.
- `memory_wrapper.hpp` 마지막 include 규칙 준수.
- 접두사: `net_`, `net_client_*`, `net_server_*`, `css_*`, `sboot_*`(부트 핸들러),
  `stran_*`(트랜잭션 핸들러), `xs_*`(method/xs 콜백).
- ✅ **리뷰 체크포인트**: 파일이 올바른 빌드 타깃(cubrid/cs/sa CMakeLists)에 들어가는가?

### net_server_init / net_Requests[] (network_sr.c)

- 새 서버 요청 추가는 3곳 세트: `network.h`(요청 리스트) + `network_sr.c`(`net_Requests[]` 등록)
  + `network_interface_sr.c`(핸들러 구현).
- ✅ **리뷰 체크포인트**: 새 요청이 network.h·net_Requests[]·핸들러 3곳에 모두 등록됐는가? `action_attribute` 플래그가
  적절한가?

### net_client_request (network_cl.c) ↔ 서버 핸들러 (network_interface_sr.cpp)

- ✅ **리뷰 체크포인트**: 클라이언트 호출(`network_interface_cl.c`)과 서버 핸들러의 패킹/언패킹이 대칭인가?

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
