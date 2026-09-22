# PostgreSQL — semi/anti join 의 1행 조기 종료

> 기준: PG 16.10 (레퍼런스 서버 192.168.6.11) + 소스 `~/dev/sources/postgres-16`. 조사 2026-09-22, 정소희 세션.
> 용도: CUBRID 의 같은 기능을 리뷰할 때 "표준 동작의 이식인가, 아키텍처가 달라 옮길 수 없는가" 판정 근거(설계-리뷰-규칙 §6).
> PG 는 제품명을 써도 되는 참조다(`memory/howto/PG레퍼런스-접속.md`, JOB 옵티마이저 규칙). 제품명 금지는 `database-reference` 쪽 규약이다.

## 한 줄

**PG 는 조인 층 게이트 하나로 끝난다 — 튜플 단위 pull 이라 "안 부르면 안 읽는다".** 인덱스에 별도 상한을 심지 않는다.

## 소스 사실

- `js.single_match = (inner_unique || jointype == JOIN_SEMI)` — NL `nodeNestloop.c:322-323`, 해시 `nodeHashjoin.c:776-777`.
- 매치 후 NL: `nl_NeedNewOuter = true` (`nodeNestloop.c:230-231`). **ANTI 는 매치 즉시 반환 없이 outer 를 버린다** (`:219-222`).
  그 뒤 inner 에 `ExecProcNode` 를 더 부르지 않는다(`:106`, `:152`).
- 해시 프로브: `hj_JoinState = HJ_NEED_NEW_OUTER` (`nodeHashjoin.c:573-574`, ANTI `:562-565`) — **같은 버킷의 나머지를 안 본다**.
- 머지도 같은 구조: `nodeMergejoin.c:1547`, `:813`.
- **inner 에 LIMIT 1 을 밀어 넣지 않는다.** 튜플 바운드 하달 기구는 `ExecSetTupleBound()`(`execProcnode.c:849`) 하나뿐이고
  **조인 노드는 그것을 부르지 않는다**(호출자는 `nodeLimit`·`execParallel.c:1449` 계열). pull 모델이라 필요가 없다.
- 옵티마이저는 이 실행 동작을 **비용으로 할인**한다 — `compute_semi_anti_join_factors()` 주석
  "the executor will stop scanning inner rows as soon as it finds a match"(`costsize.c:4714`),
  `initial_cost_nestloop` `:2998-3003`, 해시 `:4075`, 머지 `:3539`.
- 완전한 1행 단위는 아니다: btree 는 `_bt_readpage()` 가 현재 인덱스 페이지의 매칭 아이템을 한 번에 긁는다
  (`nbtsearch.c:1544`, `:1448`) — **초과 읽기 상한이 인덱스 페이지 1장**.
- 대안 경로: SEMI 에 한해 RHS 를 유일화해 평범한 inner join 으로 푸는 길을 같이 만들어 비용으로 고른다
  (`JOIN_UNIQUE_INNER/OUTER`, `joinrels.c:1005-1020`). ANTI 엔 없다.

## 실측 (JOB/IMDB, `EXPLAIN (ANALYZE, BUFFERS)`)

| 경로 | inner 읽은 양 | 판정 |
|---|---|---|
| NL + 인덱스 SEMI | `Index Only Scan rows=1 loops=7075`, 버퍼 **25,658** | 끊는다 |
| 〃 대조군 inner join | `rows=20 loops=7075`, 버퍼 **56,375** | — |
| NL + 순차 SEMI (outer 1행) | 버퍼 **1**, 0.082 ms | **끊는다. 술어(Filter)가 있어도 끊는다** |
| 〃 대조군 inner join | `Rows Removed by Filter: 2,609,126`, 버퍼 **18,824**, 167 ms | — |
| 해시 SEMI 빌드 측 | `cast_info` **36,244,344행 전수**, 9,414 ms | **못 끊는다** |
| 해시 SEMI 프로브 측 | 200만행 버킷 체인에 20만 프로브가 ~0.5 µs/건 | 끊는다 |
| NL + 인덱스 ANTI | SEMI 와 동일(버퍼 25,658) | 끊는다 |
| NL + 순차 ANTI, 매치 없음 | 전수 18,824 | **부재 증명이라 못 끊는 것이 정상** |

기본 설정에서 planner 가 해시를 안 고르고 NL Semi 를 골랐다(강제해야 해시가 나온다).
`enable_hashagg` 를 열어두면 inner 를 HashAggregate 로 dedup 한 뒤 평범한 Hash Join 으로 푸는 경로를 고른다.

## CUBRID 와의 차이 (요지)

CUBRID 는 **조인 층 게이트(`QPROC_SINGLE_INNER`)와 스캔 층 절단이 분리**돼 있다 — 게이트는 배치를 다 읽은 뒤
재진입만 막으므로 인덱스 접근(OID 배치)에서는 btree upper key limit 을 **따로 심어야 한다**(PR#7991).
PG 에는 그 분리가 없다. **따라서 이 차이는 "빠뜨린 기능" 이 아니라 실행 모델 차이다.**
단 정도는 별개다 — PG 의 초과도 0 이 아니라 인덱스 페이지 1장이고, CUBRID 의 3.8억 readkeys 는
배치 존재만이 아니라 **배치 크기와 재무장 정책**의 문제다.
