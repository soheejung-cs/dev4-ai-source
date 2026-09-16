# src/connection

> 기준: upstream/develop 95b79e7ed (2026-08-27)

## 1. 소스 목적 및 사용처 (함수별)

TCP 네트워킹, CSS(CUBRID Server/client Support) 프로토콜, HA 하트비트.
`connection_sr.c`(서버 측)/`connection_cl.cpp`(클라이언트 측), `tcp.c`(소켓 연산),
`heartbeat.c`(HA), `server_support.c`(서버 요청 디스패치)/`client_support.cpp`,
`connection_support.cpp`(공용 송수신), `connection_defs.h`(`CSS_CONN_ENTRY`).
develop 기준 클라이언트 측 다수 파일이 .cpp/클래스화(`connection_cl::`, `client_support::`)돼 있다.

| 함수 | 파일 | 목적 | 주요 사용처(호출자) |
|---|---|---|---|
| `css_send_data` | `connection_support.cpp:1619` | 응답 데이터 송신(CSS 헤더 포함) | 서버 핸들러(`network_interface_sr.cpp`), 클라 지원층 |
| `css_net_send` / `css_net_recv` | `connection_support.cpp:1150` / `:603` | 저수준 송신/수신(부분 전송 루프 포함) | `css_send_*`/`css_receive_*` 계열 내부 |
| `css_receive_data` | `connection_sr.c:1487` | 서버 측 요청 데이터 수신(타임아웃 지원) | 서버 요청 처리 경로(`xs_receive_data_from_client` 등) |
| `css_connect_to_master_server` | `connection_sr.c:1066` | 서버가 마스터에 자신을 등록·연결 | 서버 부트(`css_init` 경로) |
| `css_init` | `server_support.c:553` | 서버 연결 서브시스템 초기화·요청 루프 진입 | `src/communication/network_sr.c:1154`(`net_server_start`) |
| `connection_cl::css_connect_to_cubrid_server` | `connection_cl.cpp:1093` (`connection_cl.h:80`) | 클라이언트→서버 연결 수립 | `client_support.cpp:170/:201` |
| `client_support::css_client_init` | `client_support.cpp:158` (`client_support.h:55`) | 클라이언트 연결 초기화(마스터 경유 서버 접속) | `src/communication/network_cl.c:3625`(`net_client_init`) |
| `css_tcp_client_open` | `tcp.c:166` | TCP 클라이언트 소켓 열기 | 마스터/서버 접속 경로 |
| `css_tcp_master_open` | `tcp.c:651` | 마스터 리슨 소켓 열기 | `cub_master` 기동 |
| `hb_process_init` | `heartbeat.c:691` | HA 프로세스(서버/copylogdb 등)의 하트비트 등록 | HA 구성 프로세스 기동 경로 |

## 2. 분석 내용 (함수별)

> 항목은 함수 단위로 기술한다 — 각 항목의 제목/선두가 함수·파일명이다. 새 분석도 함수명을 앞세워 추가할 것.
> (아래 주의점·리뷰 체크포인트의 원본: src/connection/AGENTS.md 증류)

### 모듈 일반

- SA_MODE에서도 `connection_cl.c`, `connection_less.c`, `connection_globals.c`,
  `connection_list_cl.c`, `connection_support.c`가 컴파일·링크된다 — TCP 연결은 없지만 파일은 빌드됨.
  (develop 기준 실제 확장자는 `connection_cl.cpp`/`connection_less.cpp`/`connection_list_cl.cpp`/
  `connection_support.cpp`.)
- 접두사 `css_`(CSS 프로토콜), `net_`(네트워크 층). 서버 파일은 SERVER_MODE, 클라 파일은 CS_MODE.
- 서버 연결은 고정 크기 배열 `css_Conn_array`로 추적.
- ✅ **리뷰 체크포인트**: SA 빌드에서도 컴파일되는 파일에 CS 전용 가정을 넣지 않았는가?
- ✅ **리뷰 체크포인트**: 고정 크기 `css_Conn_array` 한도를 넘는 시나리오를 고려했는가?
- ✅ **리뷰 체크포인트**: 요청-응답 프로토콜 변경이 클라·서버 양쪽에 대칭 반영됐는가?

### css_send_data / css_receive_data (connection_support.cpp, connection_sr.c)

- `css_send_data()` / `css_receive_data()`는 부분 송수신 가능 — **short read/write 처리 필수**.
- ✅ **리뷰 체크포인트**: 송수신 코드가 부분 전송/수신을 루프로 처리하는가?

### css_connect_to_cubrid_server (connection_cl.cpp)

- 클라이언트 연결 순서: `css_connect_to_master()` → `css_connect_to_cubrid_server()`.

### hb_process_init (heartbeat.c)

- `heartbeat.c`는 HA 전용 — 복제 구성에서만 활성.

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
