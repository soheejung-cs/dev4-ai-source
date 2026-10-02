# 모듈 경계(cross) 지식 — .50, 8건

### 통계 객체 dangling은 CBRD-27039(동시 fetch 견고성)와 동일 결함군
히스토그램 borrow 포인터 dangling 결함은 CBRD-27039(통계 동시 fetch 견고성)와 같은 결함군으로 분류된다. 공통 패턴은 "통계 객체를 여러 주체가 동시에 fetch/무효화하는데 참조자가 소유권을 갖지 않는다"이며, reservoir 브랜치의 histogram gaps(eqjoinsel/IN/correlation/mergejoinscansel/LIKE-prefix/min-max 미비) 전반과 함께 봐야 한다. 개별 크래시로 취급하면 같은 패턴이 다른 경로에서 재발한다.
- ✅ **리뷰 체크포인트**: 통계 fetch/무효화 관련 수정 리뷰 시 CBRD-27039 계열의 동시성·소유권 패턴을 함께 점검할 것.

### 해시조인 크래시 노출 조건 — 자동 선택 + probe 측 페이지 초과 튜플 + 병렬 실행
이 크래시는 세 조건이 겹칠 때만 노출된다: (1) 해시조인이 선택됨 — PR#6782 이후 USE_HASH 힌트 없이도 해시조인 플랜이 생성된다, (2) probe 스트림에 페이지를 넘는 큰 튜플이 존재(JOB 7c의 `person_info.info` 전기문), (3) 병렬 해시조인으로 실행. 옵티마이저 로직과 무관한 실행기(executor) 버그이며 develop에서 USE_HASH 힌트로 재현 가능할 것으로 판단된다(2026-07-03 코어 덤프). 옵티마이저 변경으로 해시조인 채택률이 오르면 이 실행기 결함의 노출면이 그대로 넓어진다.
- ✅ **리뷰 체크포인트**: 해시조인 회귀 테스트에 큰 LOB/긴 문자열 컬럼이 probe 측에 오는 케이스를 반드시 포함할 것.

### BUILDLIST(GROUP BY) 집계 operand는 전부 TYPE_CONSTANT — 식은 xasl_generation이 스캔으로 옮긴다
GROUP BY가 있는 BUILDLIST 플랜에서는 집계 함수 operand가 전부 `TYPE_CONSTANT`다. 식이 `xasl_generation`(파서 단계)에서 스캔 쪽으로 이동하기 때문이며, 실제 산술 노드(INARITH)는 BUILDVALUE 플랜에서만 나타난다. 이를 몰라서 커밋1의 Q1 측정(-2.6%)은 실제로는 프로그램이 비활성인 no-op 측정이었고, 대응으로 `expr_prog_compile_roots`(feature/expression-compile 기준 `src/query/expr_compile.c:2052`)에 `allow_wired_only` 인자를 추가해 집계 훅만 wired-only를 허용한다(`src/query/query_aggregate.cpp:1006`). 커널 0개·스텝 0개면 `expr_compile.c:2132`의 `if (n_roots == 0 || (!compiled_something && !allow_wired_only))`에서 프로그램을 폐기한다. 설계문서 9.1절 참조. (심볼은 feature/expression-compile 브랜치에만 존재 — develop/CBRD-27094에는 없음)
- ✅ **리뷰 체크포인트**: 집계/식 최적화 성능 측정 전에 플랜이 BUILDLIST인지 BUILDVALUE인지 확인하고, `;trace`의 EXPR_COMPILE 덤프로 프로그램 발화 여부부터 검증할 것.

### leaf deforming — 디코딩 플랜 캐시 + 레코드 레이아웃 1회 유도 + 타입 고정 readval 커널
스캔 리프의 값 디코딩도 컴파일 대상이며 세 커밋으로 나뉜다: `3c451fedd`(디코딩 플랜 캐시 — 타입 핸들러·고정폭 디스크 크기·해제 필요 여부를 표현(representation)당 1회 해석), `bed97db8f`(오브젝트 헤더 크기·가변 오프셋 폭·고정영역 시작·bound-bit를 레코드당 1회 유도), `eeab664c2`(타입 고정 readval 커널 INT/BIGINT/SHORT/FLOAT/DOUBLE/DATE/NUMERIC을 `heap_attrvalue_resolve_plan()`의 함수 포인터 `value->rd_readval`에 저장 — `src/storage/heap_file.c:10613`). lazy 경로는 arm 시 `heap_rec_layout_init (&attr_info->lazy_layout, …)`(`heap_file.c:10995`)로 1회 유도한 레이아웃을 `heap_attrvalue_peek_lazy()`(`heap_file.c:11325`)와 공유한다. q1 17.78→16.25s, 17.97→16.45s 등의 효과.
- ✅ **리뷰 체크포인트**: 캐시 무효화가 "디스크립터(표현) 불일치 시 재구축" 하나에만 의존하므로, 스키마 변경·가변 오프셋·NULL 비트맵 변화가 이 조건으로 전부 잡히는지와 arm 이후 `lazy_recdes` 수명 동안 레이아웃이 변할 여지가 없는지 확인할 것.

### q21/q1 "회귀"의 진짜 원인 — 행당 연산 감소가 px 워커의 pgbuf 래치·futex 경합을 앞당긴다
q21 +3.3%(병렬도 6 한정, 교차 A/B에서 실재: dev 50.26~50.80 vs feat 51.10~53.22)와 리베이스 후 q1 +1.5s는 코드 결함이 아니다. 직렬 웜 전체쿼리는 피처가 우세하고(226.57 vs 229.50s, 명령어 −2.5%, 사이클 −1.4%, LLC 미스 −42%), q1은 명령어·사이클 ±1% 동일에 L1i 미스는 오히려 −21%다. 원인은 행당 연산이 줄어 px 워커가 페이지 래치/큐에 더 빨리 도달해 futex 수면/기상이 늘어난 것으로, 병렬 프로파일에서 `native_queued_spin_lock` 0.49→3.39%, futex_wake/try_to_wake_up 증가에 유저 심볼은 전부 감소했다(HEAD `bed97db8f` / `dbc84e2d2` 교차 A/B). 즉 진짜 병목은 엔진 쪽 pgbuf 래치 경합이며, 식 평가를 빠르게 할수록 이 경합이 드러난다.
- ✅ **리뷰 체크포인트**: 식/스캔 최적화 후 병렬 쿼리가 느려지면 유저 심볼 프로파일부터 보고(전부 감소면 코드 회귀 아님) 래치·futex로 옮겨간 것인지 판정하되, 병렬 단일런 수치로 회귀를 판정하지 말 것.

### 조인 순서를 PG와 완전히 맞춰도 남는 ~3.2배 엔진 상수 갭
JOB 17c/17d는 플랜이 PG와 동등한데도 15.4초 vs 4.8초로 약 3.2배 차이가 났다. 즉 조인 순서를 전부 맞춰도 PG 시간에 도달하지 못하며, 남는 갭은 옵티마이저 밖(실행 엔진 상수, 스캔·프로브 실제 처리 비용) 문제다. 옵티마이저 변경의 목표치를 잡을 때 이 상수항을 빼고 계산해야 한다.
- ✅ **리뷰 체크포인트**: "플랜이 같은데 여전히 3배 느림"을 옵티마이저 실패로 오판하지 말고, 플랜 동등성부터 확인한 뒤 동등하면 실행 엔진 쪽으로 원인을 넘길 것.

### 무관한 커밋이 핫 경로를 느리게 만든다 — 코드 배치가 바꾸는 DSB↔MITE 전환 (정소희 발견, 2026-10-02)
**건드리지도 않은 함수의 실행 속도가 링크 배치 때문에 ±1~3% 움직인다.** CBRD-27140(통계 체인 INT64, PR#7856) 머지 뒤 TRACE 성능 TC `cbrd_25454`가 간헐 FAIL 했고, bisect가 그 커밋을 지목했다. 재현은 됐지만(교대 5회 42.663s↔43.367s, +1.65%, 차이>2×MAD) **원인은 그 커밋의 내용이 아니었다.**
근거 셋. ① 정적 — `.text` 크기가 `0x871864`로 **양쪽 완전 동일**하고, 크기가 바뀐 함수는 20,086개 중 **15개, 전부 카탈로그·통계**(합계 +323B = `.text`의 0.0036%)다. 핫 함수는 역어셈블 니모닉 열이 **완전 동일**하고 **주소만 +48B** 밀렸다(`eval_pred` 1206, `scan_next_scan_local` 2442, `qexec_intprt_fnc` 559, `qexec_eval_instnum_pred` 89 — before=after). ② `perf stat` — **instructions +0.01%**, cycles +0.89%, IPC 2.75→2.71. 추가 작업이 없다. ③ 프런트엔드 — `idq.dsb_uops` **−10.56%**, `idq.mite_uops` **+14.62%**, `dsb2mite_switches.penalty_cycles` **+40.42%**. rep 짝 비교에서 **패널티 증가분 1.22G가 사이클 증가분 1.05G를 그대로 설명**한다(104~116%). 분기 예측은 아니다 — branch-misses는 오히려 −20%.
기전은 **Cascade Lake JCC erratum**이다. DSB(디코드된 uop 캐시)에 담길 자격은 **명령의 내용이 아니라 절대 주소**로 결정되고, 조건분기가 32B 경계를 걸치거나 경계에서 끝나면 그 32B 블록 전체가 DSB에서 빠져 느린 MITE로 재디코드된다. 48은 32의 배수가 아니라 함수 안 모든 분기가 격자에 16B씩 어긋난다. 실제로 `qexec_intprt_fnc` 14→21, `scan_next_scan_local` 54→56, `qexec_eval_instnum_pred` 0→1로 늘었고 **`eval_pred`는 42→34로 줄어 좋아졌다 — 부호가 무작위라는 증거다.** 반대로 나왔으면 "1.6% 개선"으로 집계되고 아무도 보지 않았을 것이다.
**완화 플래그는 이 툴체인에 없다.** `-mbranches-within-32B-boundaries`는 GCC 9+ / binutils 2.33+인데 우리는 GCC 8.5.0 / binutils 2.30이다(실측 `unrecognized option`). 구조체 packing으로도 해결되지 않는다 — 커진 구조체 4개(`btree_stats` 64→72B, `cls_info`·`disk_representation` 32→40B, `class_stats` 24→32B)는 **행당 경로에서 읽히지 않으므로** 줄여도 핫 코드의 주소 이동은 그대로다.
장비 확정: CPUID family 6 / model 85 / **stepping 7** = Cascade Lake-SP B1, 마이크로코드 `0x5003303`(JCC 완화 MCU 적용 후). 다른 마이크로아키텍처면 폭과 부호가 달라진다.
- ✅ **리뷰 체크포인트**: 벤치마크가 몇 % 움직였는데 bisect가 어떤 커밋을 지목하면, **받아들이기 전에 `perf stat`으로 instructions와 cycles를 같이** 본다. 명령 수가 늘었으면 그 변경이 일을 더 시킨 것이고, **명령 수는 같은데 사이클만 늘었으면 코드 배치**이지 코드 결함이 아니다. 확인에 10분이면 된다. 이런 축은 통제·귀속·유지가 모두 불가능하므로(다음 커밋이 배치를 또 민다) 개발자에게 넘기지 말고 **TC 판정 설계가 잡음보다 큰 마진을 갖도록** 흡수해야 한다.

### 행 단위 실행 경로는 명령 발자국이 커서 uop의 40%가 느린 디코더를 탄다 — 벡터화가 이 축을 없앤다 (정소희 발견, 2026-10-02)
위 조사의 부수 관측. **CBRD-27140과 무관하게 기준선에서 이미** `db_class` 5중 조인 2.5억 행 질의의 uop 공급이 **DSB 59.6% / MITE 40.4%**였다(2566 기준, 교대 3회 중앙값, 총 311.8G uop). 타이트한 루프라면 DSB가 80% 이상 나온다. 40%가 MITE라는 것은 **행 하나를 처리하는 데 훑는 명령 발자국이 디코드 캐시에 들어갈 수 없을 만큼 크다**는 뜻이다. 실제 크기는 `scan_next_scan_local` 12,056B, `eval_pred` 5,133B, `qdata_evaluate_aggregate_list` 3,865B, `qexec_intprt_fnc` 2,556B로 네 함수만 23KB인데 **L1i는 32KB이고 하이퍼스레딩으로 코어당 두 스레드가 나눠 쓴다.**
**배치(벡터) 실행으로 바꾸면 이 축이 통째로 사라진다.** 배치 N행에 연산 하나를 타이트한 루프로 돌리면 내부 루프가 수십 바이트라 ① L1i에 상주하고 ② DSB에 통째로 들어가며(더 작으면 LSD까지) ③ **32B 경계에 걸릴 수 있는 분기 자체가 수십 개에서 한두 개로 줄어 위 항목의 배치 민감도까지 같이 없어진다.** ④ DB_VALUE 대신 원시 타입 배열이면 L1d 밀도와 프리페치도 좋아진다. 즉 JCC 완화 플래그가 증상을 덮는 쪽이라면 **벡터화는 증상이 생길 자리를 없애는 쪽**이다.
- ✅ **리뷰 체크포인트**: **CBRD-27361**(페이지 단위 배치 스캔·집계 파이프라인, 원시 타입 배열, DB_VALUE는 경계로 강등)의 근거에 이 실측을 추가한다 — 지금까지 논거는 행당 함수 호출 수와 DB_VALUE 복사뿐이었는데 **프런트엔드 축**이 하나 더 있다. 재현: `perf stat -e instructions,cycles,idq.dsb_uops,idq.mite_uops,dsb2mite_switches.penalty_cycles -p <cub_server pid>`(이 컨테이너는 `perf_event_paranoid=2`라 사용자 공간만 샌다. perf는 `~/tools/bin/perf` + `LD_LIBRARY_PATH=~/tools/lib`). 원자료·스크립트 `claude-workspace/projects/CBRD-27140/repro/`.
