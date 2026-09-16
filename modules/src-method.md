# src/method

> 기준: upstream/develop 95b79e7ed (2026-08-27)

## 1. 소스 목적 및 사용처 (함수별)

쿼리 실행 중 메서드/SP 호출 처리. `method_scan.cpp`(실행기용 메서드 스캔), `query_method.cpp`,
`method_struct_invoke.cpp`(디스패치 구조체), `method_struct_value.cpp`(인자·결과 값),
`method_callback.cpp`, `method_error.cpp`. 흐름: query_executor → scan_manager(METHOD_SCAN)
→ method_scan → query_method → method_struct_invoke → src/sp/ → PL 엔진.

| 함수 | 파일 | 목적 | 주요 사용처(호출자) |
|---|---|---|---|
| `cubscan::method::scanner::init` | `method_scan.cpp:52` | 메서드 스캔 초기화(`PL_SIGNATURE_ARRAY_TYPE` + 입력 list_id) | `src/query/scan_manager.c` `scan_open_method_scan`(:4461) |
| `cubscan::method::scanner::open` / `close` | `method_scan.cpp:151` / `:162` | 스캔 열기/닫기 | `scan_manager.c` 스캔 수명주기 |
| `cubscan::method::scanner::next_scan` | `method_scan.cpp:173` | 다음 행에 대해 메서드 호출·결과 반환 | `scan_manager.c` `scan_next_method_scan`(:7542) |
| `cubscan::method::scanner::clear` | `method_scan.cpp:114` | 스캔 상태 정리(최종/재사용) | `scan_manager.c` 스캔 종료 경로 |
| `method_dispatch` | `query_method.cpp:113` (+오버로드 :164, 내부 :203) | 서버→클라이언트 메서드 요청의 클라이언트 측 디스패치 | `src/communication/network_cl.c`(콜백 수신 경로) |
| `method_error` | `query_method.cpp:146` | 메서드 실행 에러의 클라이언트 측 처리 | `src/communication/network_cl.c:1416/:1833` |
| `method_invoke_builtin` | `query_method.cpp:255` (내부 :343) | 빌트인(C) 메서드 in-process 실행 | `method_dispatch_internal` |
| `method_prepare_arguments` | `query_method.cpp:288` | 메서드 런타임 인자 준비 | `method_dispatch_internal` |
| `method_set_runtime_arguments` / `method_erase_runtime_arguments` | `query_method.cpp:325` / `:307` | 런타임 인자 등록/해제(UINT64 id 키) | 메서드 호출 준비·정리 경로 |
| `method_fixup_set_vobjs` | `query_method.cpp:446` (판별 :413 `method_has_set_vobjs`) | 결과값 내 가상 OID(set) 보정 | 메서드 결과 후처리 |
| `method_callback_final` | `method_callback.cpp:1229` | 콜백 핸들러 전역 정리 | 클라이언트 종료 경로 |

## 2. 분석 내용 (함수별)

> 항목은 함수 단위로 기술한다 — 각 항목의 제목/선두가 함수·파일명이다. 새 분석도 함수명을 앞세워 추가할 것.
> (아래 주의점·리뷰 체크포인트의 원본: src/method/AGENTS.md 증류)

### 모듈 일반

- Java 메서드는 `src/sp/` 경유로 PL 엔진에 라우팅, 빌트인 메서드는 in-process 실행.
- 접두사 `method_`, 스캔 통합은 `SCAN_TYPE_METHOD`.
- Java 메서드 호출은 프로세스 간 통신 — **타임아웃 처리가 결정적으로 중요**.
- ✅ **리뷰 체크포인트**: 크로스 프로세스 호출 경로에 타임아웃/에러 전파가 있는가?

### scanner::next_scan (method_scan.cpp)

- 스캔 중 메서드 호출은 비싸다 — 행마다 호출이 발생.
- ✅ **리뷰 체크포인트**: 행 단위 호출이 불필요하게 늘어나는 변경이 아닌가?

### method_dispatch / method_invoke_builtin (query_method.cpp)

- 메서드 결과는 쿼리 엔진용 `DB_VALUE`로 올바르게 변환돼야 한다.
- ✅ **리뷰 체크포인트**: 메서드 결과의 DB_VALUE 변환·정리가 완전한가?

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
