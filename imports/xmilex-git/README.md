# imports/xmilex-git — 송일한(xmilex-git) 의 소스 연구 노트·ADR

출처: https://github.com/xmilex-git/workspace (public) @ `676531645` (2026-09-16) · 들여온 날 2026-09-16 (정소희 세션). **원 작성자 xmilex-git, 원문 무수정.**
방침(사용자 지시 2026-09-16): **재사용 가능한 소스 사실 조사·설계 근거만** 남긴다. 티켓 진행 기록·CI 실패 로그·성능 측정 회차·PR 롤아웃 기록·CDC 제품/배포 결정은 제외(원 리포에서 본다).
모듈 노트(`modules/src-*.md` §2·§3)로 옮길 때는 항목 끝에 `— xmilex-git(원문 imports/xmilex-git/research/<파일>) YYYY-MM-DD` 로 출처를 남기고, 원문은 여기 둔다.

주제: CBRD-27365 튜플 포맷(레이아웃 디스크립터·접근자 API·역방향 리스트·in-place 덮어쓰기·성능/검증/리뷰 기록), CAS 병합(공유 prepared statement·XASL no-stream·워크스페이스→카탈로그 latch·PL in-process), 호스트 변수 도메인 추론, PG 세션 풀링 대조, Debezium/CDC(Oracle·PG DDL 처리), ADR 15건(parallel iscan 게이트, buildvalue 누산기 힙 소유권 등).

| 파일 | 첫 줄 |
|---|---|
| `research/cas-merge-opt-pl-inprocess-call.md` | PL/CSQL·JavaSP의 wire 우회 — 서버 세션 컨텍스트에서 직접 재호출 가능성 (사실 조사) |
| `research/cas-merge-opt-shared-prepared-statement.md` | prepared statement / 실행계획의 세션 간 공유 가능성 — 사실 인벤토리 |
| `research/cas-merge-opt-workspace-to-catalog-latch.md` | client workspace → 서버 카탈로그 read-latch 대체 가능성 — 사실 조사 (#213) |
| `research/cas-merge-opt-xasl-no-stream.md` | XASL stream 직렬화/역직렬화 제거 가능성 — 사실 조사 (#214) |
| `research/cbrd27365-accessor-api.md` | CBRD-27365 접근자 API·deform 캐시·튜플 조립기·in-place·정렬 레코드 설계 (티켓 #182, 지도 #179) |
| `research/cbrd27365-alignment.md` | CBRD-27365 연구: 자연 정렬(INT 4B 등)이 pr_type / OR_* (역)직렬화에 안전한가 |
| `research/cbrd27365-backward-lists.md` | CBRD-27365 — 역방향 스캔이 필요한 리스트 전수 분류 (`backward_capable` 근거표) |
| `research/cbrd27365-inplace-overwrite.md` | CBRD-27365 연구: 리스트 파일 in-place 덮어쓰기 5지점 증명표 |
| `research/cbrd27365-layout-descriptor.md` | CBRD-27365 레이아웃 디스크립터 설계 (티켓 #181, 지도 #179) |
| `research/cbrd27365-qfile_tuple_layout.h` | /* |
| `research/cbrd27365-sortrec-and-late-domain.md` | CBRD-27365 연구: 정렬 레코드(P/A_sort_key) 경로와 늦은 도메인 확정 정밀 조사 |
| `research/cbrd27365-tuple-format-spec.md` | CBRD-27365 임시 리스트 튜플 포맷 명세 v0 (prototype) |
| `research/debezium-pg-oracle-ddl-handling.md` | Debezium Postgres·Oracle 커넥터의 DDL/schema evolution 처리 — 선례 조사 |
| `research/hv-domain-compile-inference.md` | 컴파일 측 호스트 변수 도메인 추론 인벤토리 + 진짜 추론 불가 케이스 분류 |
| `research/hv-domain-late-binding-exec-sites.md` | CUBRID 호스트 변수(`?`) 도메인의 결정·전파·실행 비용 — 전 계층 조사 |
| `research/postgres-session-pooling-cubrid.md` | PostgreSQL의 접속·세션 수명과 CUBRID AUTO 호환 적용안 |
| `adr/0001-parallel-iscan-double-gate-units.md` | Parallel index scan 이중 게이트의 단위·threshold 분리 |
| `adr/0003-full-row-via-all-in-cond-merge.md` | full row 복원은 all_in_cond=1 병합 — 엔진 무변경 (§7.5 선택지 2) |
| `adr/0004-counter-position-and-txn-boundaries.md` | 이벤트 position은 결정적 아이템 카운터로 합성 — offset 4키·_version UInt64 (§7.4 개정) |
| `adr/0013-logical-execution-chain-crosses-session-boundary.md` | 논리 실행 체인은 물리 세션 경계를 넘어 전파된다 |
| `adr/0014-snapshot-import-does-not-pin-vacuum.md` | 스냅샷 import는 vacuum을 막지 않는다 — pin은 독립된 선행 단계다 |
| `adr/0015-parallel-buildvalue-accumulator-heap-ownership.md` | 병렬 BUILDVALUE 누산기의 힙 소유권은 패스 시작에서 빌리고 패스 안에서 반납한다 |
| `adr/0016-qfile-tuple-format-pg-style.md` | --- |
| `adr/0018-qfile-interface-preserve-paths.md` | --- |
| `RESOURCES-tuple-format.md` | Tuple Format Resources |
