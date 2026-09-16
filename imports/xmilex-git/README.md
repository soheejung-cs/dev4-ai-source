# imports/xmilex-git — 송일한(xmilex-git) 의 소스 연구 노트·ADR

출처: https://github.com/xmilex-git/workspace (public) @ `676531645` (2026-09-16) · 들여온 날 2026-09-16 (정소희 세션). **원 작성자 xmilex-git, 원문 무수정.**
모듈 노트(`modules/src-*.md` §2·§3)로 옮길 때는 항목 끝에 `— xmilex-git(원문 imports/xmilex-git/research/<파일>) YYYY-MM-DD` 로 출처를 남기고, 원문은 여기 둔다.

주제: CBRD-27365 튜플 포맷(레이아웃 디스크립터·접근자 API·역방향 리스트·in-place 덮어쓰기·성능/검증/리뷰 기록), CAS 병합(공유 prepared statement·XASL no-stream·워크스페이스→카탈로그 latch·PL in-process), 호스트 변수 도메인 추론, PG 세션 풀링 대조, Debezium/CDC(Oracle·PG DDL 처리), ADR 15건(parallel iscan 게이트, buildvalue 누산기 힙 소유권 등).

| 파일 | 첫 줄 |
|---|---|
| `research/cas-merge-ci-test-shell-7837.md` | cas-merge upstream CI test_shell 전수 실패 분석 (CUBRID/cubrid#7837, CircleCI 151311) |
| `research/cas-merge-final-gate-and-defect-log-1.md` | cas-merge 최종 게이트 진행 기록 + CTP 결함 추적 1기 요약 (2026-08-30 ~ 09-02) |
| `research/cas-merge-opt-pl-inprocess-call.md` | PL/CSQL·JavaSP의 wire 우회 — 서버 세션 컨텍스트에서 직접 재호출 가능성 (사실 조사) |
| `research/cas-merge-opt-shared-prepared-statement.md` | prepared statement / 실행계획의 세션 간 공유 가능성 — 사실 인벤토리 |
| `research/cas-merge-opt-workspace-to-catalog-latch.md` | client workspace → 서버 카탈로그 read-latch 대체 가능성 — 사실 조사 (#213) |
| `research/cas-merge-opt-xasl-no-stream.md` | XASL stream 직렬화/역직렬화 제거 가능성 — 사실 조사 (#214) |
| `research/cas-merge-productization-gaps-2026-09.md` | cas-merge 제품화 잔여 과제 — 코드/아키텍처 감사 (2026-09-12) |
| `research/cas-merge-shell-followup-map.md` | CAS 통합 셸 CI 후속 배정표 |
| `research/cas-merge-shell-followup-map.tsv` | case_path	baseline_category	baseline_reason_unverified	owner_title	owner_url	local_status |
| `research/cbrd27365-accessor-api.md` | CBRD-27365 접근자 API·deform 캐시·튜플 조립기·in-place·정렬 레코드 설계 (티켓 #182, 지도 #179) |
| `research/cbrd27365-alignment.md` | CBRD-27365 연구: 자연 정렬(INT 4B 등)이 pr_type / OR_* (역)직렬화에 안전한가 |
| `research/cbrd27365-backward-lists.md` | CBRD-27365 — 역방향 스캔이 필요한 리스트 전수 분류 (`backward_capable` 근거표) |
| `research/cbrd27365-baseline.md` | CBRD-27365 성능 기준선·검증 인프라 캡처 (티켓 #187) |
| `research/cbrd27365-ci-204.md` | #204 — upstream #7866 CircleCI test_sql 실패: `disk_size(null)` 의 `qfile_value_body_size` as |
| `research/cbrd27365-ci-205.md` | #205 — CUBRID/cubrid#7866 gha-ci test_shell 23건 실패: 원인·수정·검증 |
| `research/cbrd27365-inplace-overwrite.md` | CBRD-27365 연구: 리스트 파일 in-place 덮어쓰기 5지점 증명표 |
| `research/cbrd27365-jira-design.md` | CBRD-27365 Design |
| `research/cbrd27365-layout-descriptor.md` | CBRD-27365 레이아웃 디스크립터 설계 (티켓 #181, 지도 #179) |
| `research/cbrd27365-perf-193.md` | CBRD-27365 성능 확인 (티켓 #193) |
| `research/cbrd27365-perf-239.md` | CBRD-27365 warm TPC-H 회귀 재검증 (티켓 #239) |
| `research/cbrd27365-pr1b-accessor-rollout.md` | CBRD-27365 PR-1b: 접근자 치환 롤아웃 기록 (티켓 #196, 지도 #179) |
| `research/cbrd27365-pr2a-writer-convergence.md` | CBRD-27365 PR-2a: 튜플 조립기 도입·라이터 수렴·정렬 레코드 리더 (티켓 #190, 지도 #179) |
| `research/cbrd27365-pr2b-format-swap.md` | CBRD-27365 PR-2b: 튜플 포맷 교체 — ADR 0016 §1.1 포맷으로 접근자·조립기 내부 교체 + 구 포맷 삭제 (티켓 #199, 지도 #179) |
| `research/cbrd27365-pr2b-review.md` | CBRD-27365 PR-2b 리드 직접 리뷰 (fork PR xmilex-git/cubrid#259, 베이스 `286b6ab8a`) — 티켓 #191 세션, 지 |
| `research/cbrd27365-qfile_tuple_layout.h` | /* |
| `research/cbrd27365-review-203.md` | CBRD-27365 #7866 리뷰 반영 (#203) — SCRATCH 본문 4B 정렬·제자리 디코드 + 후속 2건 |
| `research/cbrd27365-review-243.md` | CBRD-27365 #7866 리뷰 반영 (#243) — 최상위 UNION ALL fast path 의 BACKWARD 유실(P1) + `qfile_scan_pr |
| `research/cbrd27365-sortrec-and-late-domain.md` | CBRD-27365 연구: 정렬 레코드(P/A_sort_key) 경로와 늦은 도메인 확정 정밀 조사 |
| `research/cbrd27365-tc-201.md` | CBRD-27365 TC PR (tc/pr-7866) — #201 기록 |
| `research/cbrd27365-tuple-format-spec.md` | CBRD-27365 임시 리스트 튜플 포맷 명세 v0 (prototype) |
| `research/cbrd27365-verification-192.md` | CBRD-27365 #192 정합성 검증 기록 (PR-2b `a2456c390` → 수정 커밋) |
| `research/cdc-ha-supplemental-precedents.md` | CDC × HA — supplemental 설정 위치·failover offset 연속성 선례 조사 (CUBRID·PostgreSQL·Oracle) |
| `research/debezium-oracle-txn-buffer.md` | Debezium Oracle 커넥터(LogMiner)의 transaction buffering 구현 조사 |
| `research/debezium-pg-oracle-ddl-handling.md` | Debezium Postgres·Oracle 커넥터의 DDL/schema evolution 처리 — 선례 조사 |
| `research/hv-domain-compile-inference.md` | 컴파일 측 호스트 변수 도메인 추론 인벤토리 + 진짜 추론 불가 케이스 분류 |
| `research/hv-domain-late-binding-exec-sites.md` | CUBRID 호스트 변수(`?`) 도메인의 결정·전파·실행 비용 — 전 계층 조사 |
| `research/postgres-session-pooling-cubrid.md` | PostgreSQL의 접속·세션 수명과 CUBRID AUTO 호환 적용안 |
| `research/pr753-harvest.md` | PR #753 수확: [CBRD-26722] Expand parallel heap scan to parallel scan (index, heap, list) |
| `research/wf220-ha-recipe-validation.md` | D5 AREA 수명 검증과 HA 레시피 복구 |
| `adr/0001-parallel-iscan-double-gate-units.md` | Parallel index scan 이중 게이트의 단위·threshold 분리 |
| `adr/0002-debezium-connector-jna-first.md` | CUBRID Debezium 커넥터의 CDC 접근은 JNA-first |
| `adr/0003-full-row-via-all-in-cond-merge.md` | full row 복원은 all_in_cond=1 병합 — 엔진 무변경 (§7.5 선택지 2) |
| `adr/0004-counter-position-and-txn-boundaries.md` | 이벤트 position은 결정적 아이템 카운터로 합성 — offset 4키·_version UInt64 (§7.4 개정) |
| `adr/0005-jdbc-snapshot-write-stop-barrier.md` | 초기 적재는 Debezium JDBC 스냅샷 재사용 — 쓰기 정지 barrier와 snapshot `_version`=0 (§8.1) |
| `adr/0006-e2e-deployment-and-impl-decisions.md` | E2E 수직 슬라이스의 배포·구현 결정 — 컨테이너 마운트, 토픽 reset, SMT 체인, 커넥터 내부 구조 (#40) |
| `adr/0007-txn-buffer-oracle-parity.md` | 트랜잭션 버퍼 정책은 Debezium Oracle parity — opt-in count threshold·retention, 초과 시 abandon |
| `adr/0008-ddl-halt-1.0-support-matrix.md` | 1.0 DDL 지원 = DDL halt — captured 테이블 DDL 감지 시 fail-fast, 복구는 resnapshot 단일 절차 |
| `adr/0009-online-snapshot-connector-only.md` | Online snapshot 1.0 — 엔진 확장 없는 커넥터-only 방식 + blocking snapshot, incremental은 post-1.0 |
| `adr/0010-ha-halt-master-only-1.0.md` | 1.0 HA 지원 = HA halt — master-only 캡처, 노드 전환 감지 시 fail-fast, 복구는 resnapshot |
| `adr/0011-cdc-privilege-and-relation-dictionary.md` | 1.0 CDC 권한 = per-table SELECT + 서버 relation 사전 — DBA 의존 제거, owner 전면 채택 |
| `adr/0012-pure-java-log-client-standalone-repo.md` | cubrid_log 순수 Java 포팅 + 커넥터 standalone 저장소 전환 |
| `adr/0013-logical-execution-chain-crosses-session-boundary.md` | 논리 실행 체인은 물리 세션 경계를 넘어 전파된다 |
| `adr/0014-snapshot-import-does-not-pin-vacuum.md` | 스냅샷 import는 vacuum을 막지 않는다 — pin은 독립된 선행 단계다 |
| `adr/0015-parallel-buildvalue-accumulator-heap-ownership.md` | 병렬 BUILDVALUE 누산기의 힙 소유권은 패스 시작에서 빌리고 패스 안에서 반납한다 |
| `adr/0016-qfile-tuple-format-pg-style.md` | status: accepted |
| `adr/0017-ctp-runner-on-cubridci-image.md` | status: accepted |
| `adr/0018-qfile-interface-preserve-paths.md` | status: accepted |
