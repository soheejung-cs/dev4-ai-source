# src/storage

> 기준: upstream/develop 95b79e7ed (2026-08-27)

## 1. 소스 목적 및 사용처 (함수별)

버퍼풀, 힙 파일, B-tree, 디스크/파일 관리, 서버측 통계. 대부분 SERVER/SA 전용이며 소수 파일
(`byte_order.c`, `es.c`, `file_io.c`, `oid.c`, `statistics_cl.c`, `storage_common.c`, `tde.c` 등)만
`cubridcs`에도 컴파일된다. 핵심 파일: `page_buffer.c`(pgbuf_fix/unfix/dirty),
`heap_file.c`(MVCC 버전·스캔), `btree.c`(검색·범위스캔·MVCC 인덱스), `disk_manager.c`/`file_manager.c`,
`slotted_page.c`, `statistics_sr.c`/`statistics_ndv.c`, `system_catalog.c`. 상세는 `docs/` 하위 참조 문서 7종.

| 함수 | 파일 | 목적 | 주요 사용처(호출자) |
|---|---|---|---|
| `pgbuf_fix` / `pgbuf_unfix` / `pgbuf_set_dirty` | page_buffer.c:2162,2969,4823 (매크로: page_buffer.h) | 페이지 fix(래치+핀)·unfix·dirty 마크 — 버퍼풀 기본 프로토콜 | 스토리지·쿼리 전 모듈 (btree.c, heap_file.c, scan_manager.c 등) |
| `pgbuf_ordered_fix` | page_buffer.c:12141,12146 | 힙/오버플로 페이지의 데드락 회피 순서 fix (PGBUF_WATCHER 운반) | heap_file.c, scan_manager.c, histogram_sampler_sr.cpp, px_scan_input_handler_heap.cpp |
| `pgbuf_search_hash_chain` | page_buffer.c:7496 | VPID→BCB 해시 체인 탐색 (fix 경로의 조회 코어) | page_buffer.c 내부(fix 경로) |
| `pgbuf_hash_func_mirror` | page_buffer.c:1500 | VPID 해시 함수(버킷 인덱스 계산) | page_buffer.c 내부 |
| `pgbuf_copy_page_for_scan` | page_buffer.c:892 | 래치 없이 스캔하기 위한 페이지 사본 생성 | heap_file.c |
| `pgbuf_copy_buffer_alloc` / `_free` | page_buffer.c:855,880 | 스캔용 복사 버퍼 할당/해제 | page_buffer.c (힙 스캔 경로) |
| `xbtree_find_unique` | btree.c:25406 | 유니크 인덱스 단건 키 조회 진입점 | network_interface_sr.cpp, query_executor.c |
| `btree_search_key_and_apply_functions` | btree.c:23781 | 키 탐색 공통 진입점(루트→리프 하강 + 노드/리프 함수 적용) | btree.c 내부 (조회·삽입·삭제 경로의 공통 코어) |
| `btree_range_scan` | btree.c:26520 | 범위 스캔 드라이버(리프 순회 + key_func 적용) | scan_manager.c, locator_sr.c |
| `btree_range_scan_resume` | btree.c:25750 | 중단된 범위 스캔의 리프 재개(LSA 비교→재사용/재탐색) | btree.c (btree_range_scan) |
| `btree_search_nonleaf_page` | btree.c:5235 | 논리프 노드 내 이진탐색으로 자식 VPID 결정 | btree.c 내부 4곳 (btree.h:910에 extern 선언) |
| `btree_compare_key` | btree.c:20048 | 인덱스 키 비교(도메인·collation 처리) | btree.c, btree_load.c, external_sort.c, px_scan_index_leaf_slot_walker.cpp |
| `btree_prepare_bts` | btree.c:16341 | BTREE_SCAN 구조 준비(범위·필터 세팅) | scan_manager.c, locator_sr.c, btree_load.c |
| `heap_next` | heap_file.c:19252 | 힙 순차 스캔에서 다음 가시 행 반환 | scan_manager.c, histogram_sampler_sr.cpp, load_server_loader.cpp |
| `heap_prepare_get_context` | heap_file.c:7069 | 행 조회 컨텍스트 준비(페이지 fix·슬롯 타입 확인·포워딩 추적) | heap_file.c, locator_sr.c |
| `heap_get_mvcc_header` | heap_file.c:7304 | 준비된 컨텍스트에서 MVCC 레코드 헤더 추출 | heap_file.c, locator_sr.c |
| `heap_get_record_data_when_all_ready` | heap_file.c:7391 | 가시성 판정 후 레코드 데이터 확보(COPY/PEEK) | heap_file.c, locator_sr.c |
| `heap_get_class_oid_from_page` | heap_file.c:19455 | 힙 페이지 헤더에서 클래스 OID 유도 | heap_file.c, vacuum.c, page_buffer.c |
| `heap_scancache_start_internal` | heap_file.c:6359 | 스캔캐시 시작(is_queryscan이면 클래스 IS_LOCK 획득) | heap_file.c 내부 (heap_scancache_start* 래퍼 경유) |
| `spage_get_record` | slotted_page.c:3815 | 슬로티드 페이지에서 슬롯 레코드 조회(PEEK/COPY) | btree.c, heap_file.c, vacuum.c, px_scan 계열 |
| `fileio_write` | file_io.c:4145 | 볼륨에 페이지 물리 쓰기(저수준 I/O) | page_buffer.c(플러시), double_write_buffer.cpp, log_page_buffer.c |
| `disk_reserve_sectors` | disk_manager.c:4290 | 볼륨 섹터 예약 | file_manager.c |
| `file_alloc` | file_manager.c:5420 | 파일에 페이지 할당 | btree.c, btree_load.c, query_manager.c, vacuum.c |
| `xstats_update_statistics` | statistics_sr.c:91 | 클래스 통계 갱신 서버 진입점 | network_interface_sr.cpp |
| `stats_analyze_mcv_list` | statistics_ndv.c:205 | MCV 후보 중 채택 개수 결정(통계 검정) | histogram_sampler_sr.cpp:312 |

## 2. 분석 내용 (함수별)

> 항목은 함수 단위로 기술한다 — 각 항목의 제목/선두가 함수·파일명이다. 새 분석도 함수명을 앞세워 추가할 것.

### 모듈 일반

- 영구 페이지 접근은 전부 버퍼풀 경유. `file_io.c`는 저수준 볼륨 I/O이지 힙/B-tree/카탈로그 페이지
  수정의 지름길이 아니다.
- 페이지 래치는 물리적 일관성, 트랜잭션 락은 논리적 일관성 — 서로 대체 금지.
- 온디스크 디스크립터/페이지 레이아웃 변경 시 디스크 호환성, 리커버리 레코드, TDE 플래그,
  check/dump 코드를 같은 서브시스템에서 함께 점검.
- `LOG_LSA`는 transaction/WAL 소유지만 storage 페이지가 page LSA 필드를 갖는다 — 플러시 코드는
  WAL 규칙을 보존해야 한다.
- 헤더에 `#error Belongs to server module`이 있으면 그 경계를 유지할 것.
- `statistics_cl.c`는 클라이언트, `statistics_sr.c`는 서버, SA는 둘 다 빌드.
- `es.c`는 모드를 가로지름: 클라이언트/SA는 `network_interface_cl.h` 경유 가능, 서버는 백엔드 직접 호출.
- ✅ **리뷰 체크포인트**: `file_io.c` 직접 호출로 버퍼풀을 우회하지 않는가?
- ✅ **리뷰 체크포인트**: 래치로 락을, 락으로 래치를 대신하려 하지 않는가?
- ✅ **리뷰 체크포인트**: 페이지 레이아웃/디스크 포맷 변경 시 리커버리(redo/undo), TDE, check/dump,
  디스크 호환성까지 짝으로 수정됐는가? 플러시 경로가 page LSA(WAL 규칙)를 보존하는가?
- ✅ **리뷰 체크포인트**: CS 빌드에 들어가는 파일인지(클라이언트 서브셋) 확인하고 서버 전용 API를
  호출하지 않는가?
- **index skip scan 리뷰 논점** (PR #7463): 선두 컬럼 NULL 케이스만이 아니라 **복합키 중간 NULL**에서도
  알고리즘이 성립하는지, 샘플링을 1회가 아니라 구간을 끊어 여러 번 해야 하는지 확인.
- **섹터 read 실패 경로에서 미초기화 ftab 포인터를 free하지 말 것** (CBRD-27285) — 에러 경로의 정리
  코드는 "그 시점까지 초기화된 것"만 해제해야 한다. 에러 경로 리뷰 시 각 자원의 초기화 시점 대조.
- **랜덤 프로브가 많은 플랜만 페이지 버퍼 크기에 비선형으로 민감하다**: TPC-H q19의 나쁜 플랜
  (part 구동, FK 인덱스 2M회 프로브)은 버퍼 8G에서 16G 대비 약 2배 악화된다(25s → 48s). 반면
  lineitem 구동 플랜은 버퍼 크기와 무관하게 ~5s로 일정하다(측정 기준 b572177a1, FK 인덱스 16개).
  즉 버퍼 크기 민감도는 플랜 모양의 함수이며, 비용 모델은 이 민감도를 전혀 반영하지 않는다.
  - ✅ **리뷰 체크포인트**: 성능 회귀를 버퍼 크기 탓으로 돌리기 전에 플랜 모양부터 확인하라 —
    버퍼 민감도가 크다는 것 자체가 프로브 폭주 플랜을 골랐다는 신호다.

### pgbuf_fix / pgbuf_unfix / pgbuf_set_dirty (page_buffer.c)

- 버퍼풀 프로토콜: 성공한 모든 `pgbuf_fix*()`는 `pgbuf_unfix*()` 또는 `pgbuf_set_dirty(..., FREE)`로
  짝을 맞춰야 한다. 수정 페이지는 unfix 전에 dirty 마크. 포인터를 널리파이하려면 `pgbuf_unfix_and_init()`.
- 래치 순서 준수: 부모/조상 페이지를 자식보다 먼저 fix.
- 락프리 RO 경로: fix는 `fcnt==0`, unfix는 `fcnt==1`에서 bail(측정 시점 L7636/L7708) → 단독 스캐너는
  항상 뮤텍스 경로로 떨어져 페이지당 BCB 뮤텍스 2왕복.
- **PGBUF_BCB(144B)는 mutex·read-mostly(VPID/iopage 포인터)·per-fix 쓰기 필드(fix count/
  latch/LRU 링크)를 한 캐시라인 세트에 섞고, `malloc` 테이블이라 16B 어긋나 BCB가 라인을 걸친다.**
  CBRD-27284가 이를 false sharing으로 보고 3라인 분리(144→192B, `alignas(64)`+`aligned_alloc`)를
  시도했으나 **perf c2c 재측정으로 반증돼 종결**(PR#7844 close, 2026-09-02). [출처 .52, 기준 04620b2ce vs addd1e955]
  - **실측 사실 (TPC-H SF10 Q21, 8192M/par6, 16 워커)**: 전체 Load-HITM의 32%가 **BCB 한 개**에
    몰린다 — `lineitem.fk_lineitem_l_orderkey` **루트 페이지**(Btid 19|16064|16065)의 BCB. 상관
    서브쿼리 프로브마다 모든 워커가 같은 루트를 fix/unfix하며 같은 `atomic_latch`를 RMW한다 →
    **true sharing**이지 무관한 BCB 간 false sharing이 아니다. 필드 배치로는 이 왕복을 없앨 수 없다.
  - **64B 분할의 역효과**: 분리된 read-mostly 라인(vpid·hash_next·iopage_buffer·LRU 링크)은
    스토어 샘플 0인데 HITM 21,863(latch 라인 21,695와 동수). 두 라인이 **128B 정렬 형제**라
    인접 라인 프리페치로 함께 끌려온다(규칙집 COH-03). 결과 전체 HITM 98,563 → 155,956(+58%),
    fix 경로 전송 1회→2회. 원자료 `.52:~/dev/tests/tpch/results/c2c_27284/`.
  - 벽시계: JOB 16G/par6 9/9 무변화 / TPC-H 8192M 블록 순차 A→B −6.2%는 **goto 전환 직후 첫
    rep +13% 페널티**(팔 무관)가 만든 수치, B→A 반전에서 +4.5%로 뒤집힘 → 차이 없음.
  - 구 측정치(TPC-H 8G −4.7%)는 2026-08-28 계약 경계(24094 포맷 + 샘플링 통계 결함)로 무효.
  - 열린 방향(미착수·미발번): 루트 페이지 fix당 latch RMW 빈도 자체를 줄이는 것([G] Tier-0 설계).
- ✅ **리뷰 체크포인트**: 모든 fix 경로(에러 경로 포함)에서 unfix가 보장되는가? 수정 후 dirty 마크가
  unfix보다 앞서는가?
- ✅ **리뷰 체크포인트**: 래치 종류(READ/WRITE)가 실제 작업과 일치하는가? 래치 순서(부모→자식)를
  어기지 않는가?

### pgbuf_ordered_fix (page_buffer.c:12141/12146)

- 힙/오버플로 순서 fix는 `PGBUF_WATCHER`가 group/rank 상태를 운반 — watcher를 쓰는 코드에서 우회 금지.
- `pgbuf_ordered_fix_release`의 패스트패스가 35,624B 스택 프레임(`sub $0x8b28,%rsp`, 측정 시점 L12155).
  64×64 워스트케이스 배열 때문인데 패스트패스는 그 배열을 쓰지 않는다.
- ✅ **리뷰 체크포인트**: `PGBUF_WATCHER`를 쓰던 경로에서 watcher 없이 페이지를 fix하지 않는가?

### pgbuf_search_hash_chain (page_buffer.c:7496)

- buf_hash_table(측정 시점 L554/L5581): 버킷 56B×2^20=56MB인데 히트 경로는 8B(hash_next)만 읽음 —
  mutex는 미스/insert 전용. SoA 분리 시 8MB. 해시가 pageid 순서를 보존하므로 분리 후 프리페치 가능.
- trylock→lock 패턴(측정 시점 L7513): 형식상 중복이나 trylock 대체로 성공 — 접어도 무익(비검토 대상 판정).

### pgbuf_hash_func_mirror (page_buffer.c:1500)

- bitrev8이 언롤 안 된 8회 루프로 버킷 로드 직전에 실행됨(-O2는 -funroll-loops 미포함).
  256엔트리 rodata 테이블로 대체 가능.

### pgbuf_copy_page_for_scan / pgbuf_copy_buffer_alloc (page_buffer.c:892/:855)

- memmove 프로파일 2.23%의 정체: `pgbuf_copy_page_for_scan`의 페이지당 16KB 복사(page_buffer.c:892).
  CBRD-27041의 의도적 설계 — 래치 없이 스캔하기 위한 사본.
- 복사 버퍼 크기는 sizeof가 아니라 offsetof + PGBUF_IOPAGE_BUFFER_SIZE로 계산해야 한다:
  `FILEIO_PAGE.page`가 `char[1]` 유연 배열이라 `sizeof (struct pgbuf_copy_buffer)`로 잡으면 페이지
  페이로드만큼 과소 할당된다. 현재 소스는 `PGBUF_COPY_BUFFER_ALLOC_SIZE = offsetof (struct
  pgbuf_copy_buffer, iopage_buf) + PGBUF_IOPAGE_BUFFER_SIZE` 관용구를 쓰고(page_buffer.c:849-852,
  "CRITICAL: sizeof ... under-allocates" 주석 포함), `PGBUF_IOPAGE_BUFFER_SIZE` 자체도
  page_buffer.c:118에서 동일한 offsetof 방식으로 정의된다. `pgbuf_copy_buffer_alloc ()`(:855)이 이
  매크로로 malloc하고, 해제는 `pgbuf_copy_buffer_free ()`(:880)와 짝을 이룬다.
  (기준: CBRD-27094 @ faf5a3b2a, 행번호 재검증됨)
- ✅ **리뷰 체크포인트**: pgbuf 계열 구조체를 memcpy/할당하며 `sizeof`를 그대로 쓰는 코드가 보이면
  유연 배열 페이로드 누락을 의심하고 offsetof 관용구로 바꾸도록 지적한다.

### btree_search_nonleaf_page (btree.c:5235)

- **UB: start_col 미초기화** — 선언 btree.c:5242(develop 95b79e7ed에서 미초기화 잔존 재확인).
  MIDXKEY 분기에서만 대입되는데 이진탐색 루프의 `right_start_col = start_col` /
  `left_start_col = start_col`(측정 시점 L5349/L5354)에서 무조건 읽는다. 단일컬럼 인덱스 전부 해당.
  리프 쌍둥이 `btree_search_leaf_page`(:5583)는 정상. 수정 c44ccf767은 join-perf-analysis 브랜치에만
  있고 develop에 아직 없음.
- 외부 호출자 0인데 exported(btree.h:910) → 자기 호출이 PLT 경유. btree.c:1260 주석은 "parallel
  index scan needs it"이라 하나 git grep상 btree.c 밖 호출자 없음. static이면 끝.
  `btree_reset_common_prefix_page_info`(btree.c:1769)도 non-static(헤더 선언 없음)인데 호출자는
  btree.c 내부뿐 — 같은 문제.

### btree_compare_key (btree.c:20048)

- 스캔 불변(키 타입·collation)을 비교마다 재검증 — 20여 비교 캐스케이드를 통과한 뒤에야 cmpval
  간접호출에 도달.

### btree_range_scan_resume (btree.c:25750)

- 리프 재사용 기계: 저장한 리프 LSA가 같으면(LSA_EQ) 페이지 재사용 → 아니면 min/max 키 범위 확인 →
  재탐색 → 최후에 루트부터 하강. 이 기계를 확장할 때의 함정 2개:
  - `btree_leaf_is_key_between_min_max`(:5415)는 비MIDXKEY에서 무조건 BETWEEN을 반환한다
    (containment 판정이 아님).
  - `BTREE_IS_PAGE_VALID_LEAF`(:290)는 페이지가 해당 BTID 소속인지 검증하지 않는다.

### btree_prepare_bts (btree.c:16341)

- ~80B `FILTER_INFO`를 프로브마다 복사(내용 동일, 측정 시점 L16596 — develop 정의는 :16341로 이동).

### heap_scancache_start_internal (heap_file.c:6359)

- **힙 스캔의 IS_LOCK과 compactdb의 X_LOCK 상호 배제가 스캔 중 페이지 재-fix의 안전 근거다**:
  힙 스캔은 `heap_scancache_start_internal`(heap_file.c:6359)에서 `is_queryscan`일 때
  `lock_scan (thread_p, class_oid, LK_UNCOND_LOCK, IS_LOCK)`을 획득한다(heap_file.c:6387). 반면
  compactdb 경로는 `xheap_reclaim_addresses`(heap_file.c:5731)에 들어가기 전에 클래스에 X_LOCK을
  잡으므로(src/storage/compactdb_sr.c:625) 두 경로는 상호 배제되고, 스캔 도중 페이지 dealloc이
  끼어들 수 없다. S_END 시점에 페이지를 다시 fix하는 코드가 안전한 근거가 바로 이 락 불변식이지
  페이지 래치가 아니다. (기준: CBRD-27094 @ faf5a3b2a. 원 메모의 `heap_file.c:6806 부근
  heap_scancache_start` 참조는 행 번호 확인 필요 — 당시 소스와 불일치, 실제 위치는 6359/6387이며
  심볼도 `heap_scancache_start_internal`이다.)
- ✅ **리뷰 체크포인트**: 힙 스캔 경로에서 락을 조기 해제하거나 락 없이 페이지를 재-fix하는 변경은
  이 IS_LOCK↔X_LOCK 배제 불변식을 깨므로 거부 대상이다.

### heap_prepare_get_context / heap_get_mvcc_header / heap_get_record_data_when_all_ready (heap_file.c:7069/:7304/:7391)

- 힙 프로브 1행당 같은 슬롯을 3~4회 재탐색: prepare_get_context(측정 시점 L7098 slot0 + L7106) →
  get_mvcc_header(L7330) → get_record_data(L7430). PEEK이면 3·4번째 탐색은 비트 단위로 동일한 작업.
  spage 계열 합계 프로파일 7.6%.
- `or_header_size`(src/object/object_representation.c:5771): 6명령어 함수가 PLT 경유로 호출되며
  가변길이 속성당 4회 호출(같은 값 반환).
- `or_mvcc_get_repid_and_flags`(src/object/object_representation.c:399): 형제 3개는 same-TU
  ALWAYS_INLINE인데 이것만 타 TU+PLT → OR_BUF 스택 실체화. 피호출자 1.35% > 호출자 0.64%.

### heap_get_class_oid_from_page (heap_file.c:19455)

- class OID를 행마다 페이지에서 재유도(측정 시점 L25451: class_oid에 NULL 전달 시 매행
  `heap_get_class_oid_from_page` 호출) — 유일 소비처는 scan_cache에 이미 같은 값을 갖고 있음.

### xstats_update_statistics (statistics_sr.c:91)

- **파티션 테이블 부모 NDV를 자식 합산으로 만들면 과대추정** — 자식 간 값 중복이 무시된다.
  (CBRD-26936 계열에서 실측)
- **저장된 btree NDV는 불신 대상** — 실측에서 저장값 587K vs 실제 11 수준의 괴리 사례. (동일 계열)
- varchar 통계의 정밀도 캡 제거는 플랜을 바꾼다 — 통계 표현 변경은 반드시 플랜 diff 회귀 확인. (동일 계열)
- **통계/MCV 코드 변경은 저장된 히스토그램에 소급되지 않아 재생성이 필수다**: 통계 산출 코드를
  고쳐도 이미 카탈로그에 저장된 히스토그램에는 반영되지 않으므로, 수정 후 히스토그램을 재생성해야
  비로소 새 로직이 관측된다. 실제 검증은 재생성 후 movie_info.info의 MCV 개수를 확인하는 절차로
  했고(Horror 포함 ~300개 기대), 당시 쓰던 `SHOW HISTOGRAM movie_info ON info` 구문은 커밋
  61ce121e0([CBRD-26959] Retire ANALYZE TABLE and SHOW HISTOGRAM)에서 폐지되어 현재는 csql
  `;info histogram`으로 확인해야 한다.
- ✅ **리뷰 체크포인트**: 통계 산출 코드 변경 PR의 성능/정확도 수치가 히스토그램 재생성 후 값인지
  확인할 것 — 재생성 없이 낸 수치는 이전 통계로 측정된 무효 수치다.

### stats_analyze_mcv_list (statistics_ndv.c:205)

- **PG analyze_mcv_list의 통계 검정 이식본이며 "1% 고정 규칙"으로 퇴행한 전례가 있다**:
  `stats_analyze_mcv_list`(statistics_ndv.c:205 — 원 메모의 `:202`는 행 번호 확인 필요, 당시 소스와
  불일치)는 초기하분포 기반 연속성 보정 Wald 신뢰구간 하한
  (`mcv_counts[num_mcv-1] > selec * samplerows + 2 * stddev + 0.5`)으로 MCV 채택 개수를 정한다.
  과거 df937b482가 이를 "샘플 비null 행의 1% 이상"이라는 고정 임계값으로 바꾸고
  stadistinct/stanullfrac/totalrows 인자를 `(void)` 캐스팅으로 버렸는데, 그 결과 movie_info.info가
  MCV 300캡 중 12개만 채택되어 'Horror' 1,466배·6개 장르 IN 1,477배·cast_info.note
  '(voice: English version)' 839배 과소추정이 났고 이것이 JOB 30건 divergence의 1순위 원인이었다
  (격차 약 106초; 직접 원인 18b 18c 31a 31c 25a 25c 30a 30c 28b 8a, 잠재 9d/12/13). 리버트 커밋
  bb9b53e46으로 PG 기준이 복원되며 mi.info MCV 12→300개, Horror 추정 오차 1,466배→7%가 되었다
  (퇴행 기준 바이너리 ba0d955ee). 호출부는 src/optimizer/histogram/histogram_sampler_sr.cpp:312
  (원 메모의 `:290`은 행 번호 확인 필요 — 당시 소스와 불일치)이며, 전수 reservoir 스캔에서
  stadistinct=모집단 비null NDV, stanullfrac=0.0, samplerows=reservoir 비null 크기, totalrows=정확한
  모집단 비null 행수로 매핑해 넘긴다. (기준: CBRD-27094 @ faf5a3b2a, 행번호 재검증됨)
- ✅ **리뷰 체크포인트**: MCV 채택 로직 변경이면 PG analyze_mcv_list와의 수식 동치성, 시그니처의
  stadistinct/stanullfrac/samplerows/totalrows가 실제 계산에 쓰이는지(다시 `(void)` 처리되지
  않았는지), 전수 스캔의 비null 공간 매핑 규약(stanullfrac=0, totalrows=비null 모집단) 유지를 모두
  확인할 것.

### `catcls_update_class_stats()` — 카탈로그 통계 칸 갱신 (catalog_class.c)

`UPDATE STATISTICS` 의 마지막 단계다. `stats_update_statistics_internal()`(statistics_sr.c:443)이
`catalog_add_representation()`·`catalog_add_class_info()` 로 **내부 카탈로그**(옵티마이저가 읽는 곳)에
통계를 기록한 뒤 이 함수를 불러, 그 사실을 **사용자에게 보이는 `_db_class` 행**에 반영한다.
고치는 칸은 둘뿐이다 — `catcls_update_or_value_class_stats_fields()` 가
`checked_time`(수집 시각, timestamp→datetime)과 `statistics_strategy`(전수스캔 여부, int)만 바꾼다.

`_db_class` 행이 직렬화된 OR 형식이라 "컬럼 하나만 UPDATE" 가 없고, 전체를 풀었다 다시 싼다:

```
①  catcls_find_oid_by_class_name              대상 클래스의 _db_class 행 OID
②  ct_Class.cc_classoid / catalog_get_class_info   _db_class 자신의 클래스 OID·HFID
③  heap_scancache_start_modify                수정용 스캔캐시
④  heap_get_visible_version (..., COPY, ...)   현재 행 읽기  ← record.data = 스캔캐시 소유 버퍼
⑤  catcls_get_or_value_from_record            직렬화 레코드 → OR_VALUE 트리
⑥  catcls_update_or_value_class_stats_fields  두 칸만 수정
⑦  record.data = malloc (record.length)       ← 이 시점부터 record.data 가 이 함수 소유
⑧  catcls_put_or_value_into_record (old_chn+1) 재직렬화 (chn 증가 = 클라이언트 캐시 무효화)
⑨  locator_update_index / ⑩ heap_update_logical
```

**소유권 경계가 ⑦ 이다.** 형제 함수 `catcls_update_instance()`(:4155)는 처음부터 읽기 `old_record` /
쓰기 `record` 를 나눠 이 경계를 코드로 표현하는데, 이 함수만 RECDES 하나를 겸했다(→ §3).
④ 가 실패했을 때는 안전하다 — `heap_get_visible_version_internal()` 은 복사 영역을 먼저 잡고
(`heap_scan_cache_allocate_area (thread_p, scan_cache, DB_PAGESIZE * 2)`) 실패 시 `recdes` 를 건드리기
전에 `S_ERROR` 로 빠진다. (기준: develop 1ea077d85)

### 페이지 래치 실패의 에러 계약 — `pgbuf_fix()` ~ `pgbuf_timed_sleep()` (page_buffer.c)

**래치는 락이 아니다.** 버퍼 관리자가 BCB 단위로 관리하는 짧은 배타 제어이고, 모드는
`PGBUF_LATCH_READ`/`PGBUF_LATCH_WRITE` 둘뿐이며, 대기는 BCB 의 `next_wait_thrd` 큐에 매달린다.
결정적 차이는 **데드락을 탐지하지 않는다**는 것이다. 코드가 그 판단을 명시한다(page_buffer.c:7045):

> We do not guarantee that there is no deadlock between page latches. So, we made a decision that
> when read/write buffer fix request is not granted immediately, block the request with timed sleep
> method. ... When the request is waken up, the request is treated as a victim.

즉 **래치 타임아웃은 비정상 사건이 아니라 정상 동작의 일부**다(락 쪽은 `wait_for_graph.c` 로 탐지해
희생 트랜잭션을 abort 시킨다). 호출자는 타임아웃을 받아 재시도하거나 물러나도록 짜여 있고,
`bestspace.cpp` 가 그 전형이다 — `error_code == ER_LK_PAGE_TIMEOUT` 이면 `er_clear()` 후
`status::CONTENDED` 로 재시도한다.

대기 시간 결정 방식이 헷갈리기 쉽다. `pgbuf_timed_sleep()` 은 트랜잭션의 `tdes->wait_msecs` 를
읽지만(`pgbuf_find_current_wait_msecs()`), 그 값을 대기 길이로 쓰지 않는다:

```c
old_wait_msecs = wait_msecs = pgbuf_find_current_wait_msecs (thread_p);
if (wait_msecs == LK_ZERO_WAIT || wait_msecs == LK_FORCE_ZERO_WAIT) wait_msecs = 0;
else wait_msecs = pgbuf_latch_timeout_msecs;   /* PRM_ID_PAGE_LATCH_TIMEOUT_IN_MSECS, 기본 300초 */
```

**트랜잭션 설정은 "기다릴지 말지"와 "타임아웃 때 어떤 에러를 보고할지"만 고르고**, 실제 대기 길이는
래치 전용 파라미터가 정한다. `old_wait_msecs` 를 따로 보관하는 이유가 후자다.

에러 계약: `pgbuf_fix()` 가 NULL 을 반환하면 **반드시 에러가 설정돼 있어야 한다.** 호출자들이
`ASSERT_ERROR_AND_SET (error_code)`(= `assert (er_errid () != NO_ERROR); error_code = er_errid ()`)
로 이를 강제하기 때문이다(예: btree.c:30574, `btree_split_node_and_advance` 의 자식 페이지 fix 직후).
전파 경로 어디에서도 에러를 메우지 않으므로, 계약을 지켜야 하는 쪽은 최하단이다:

```
pgbuf_timed_sleep → pgbuf_block_bcb (:7054) → pgbuf_latch_bcb_upon_fix (:6499) → pgbuf_fix (:2411) → NULL
   (세 단계 모두 ER_FAILED 를 그대로 올릴 뿐 er_set 하지 않는다)
```

`er_set_return` 블록이 세 갈래이고 **`er_errid()` 의 최종값은 `ER_LK_PAGE_TIMEOUT`** 이다 —
`LK_INFINITE_WAIT` 분기는 `ER_PAGE_LATCH_TIMEDOUT` 뒤 `ER_LK_UNILATERALLY_ABORTED`,
`> 0` 분기는 `ER_PAGE_LATCH_TIMEDOUT` 뒤 `ER_LK_PAGE_TIMEOUT` 을 설정한다. 이름이 `ER_LK_`(lock)
계열이지만 래치 타임아웃에 쓰인다. (기준: develop 1ea077d85)

- ✅ **리뷰 체크포인트**: `pgbuf_fix()` 가 NULL 을 반환하는 경로나 `pgbuf_latch_bcb_upon_fix()` /
  `pgbuf_block_bcb()` 가 에러를 반환하는 경로를 새로 만들면 **그 지점에서 er_set 을 하는지** 본다.
  래치 경쟁을 양성으로 처리하는 호출자가 `ER_LK_PAGE_TIMEOUT` 을 특정해 검사하므로(bestspace),
  타임아웃에 다른 코드를 쓰면 재시도 가능한 경쟁이 하드 실패로 바뀐다.


### 스레드 스코프 wait override 와 "연산 스코프 무한대기 강제"의 중첩 (page_buffer.c · disk_manager.c 등, PR#7843 실측)

`tdes->wait_msecs` 를 임시로 바꾸는 코드는 두 부류다 — ① no-wait 프로브(bestspace `L1_fix`, `btree_set_error`,
`xlock_dump`: `LK_FORCE_ZERO_WAIT`), ② "여기서는 절대 타임아웃 금지" 강제(`disk_is_page_sector_reserved_with_debug_crash`,
`heap_does_exist`, `log_rollback`, `btree_load` 온라인 인덱스 락 복구: `LK_INFINITE_WAIT`). 둘이 **같은 변수(TDES)** 를 쓰는
동안은 가까운 스코프가 이겼다(LIFO). CBRD-27183 이 ①만 THREAD_ENTRY override 로 옮기자, 조회(`logtb_find_current_wait_msecs`)가
override 를 우선하므로 **①창 안에 중첩된 ②가 가려져 스코프가 뒤집혔다.**

발화 경로(debug 빌드): `page_validation_level` 기본값이 `!NDEBUG` 에서 `PGBUF_DEBUG_PAGE_VALIDATION_FETCH` 라
`pgbuf_fix` 마다 `pgbuf_is_valid_page → disk_is_page_sector_reserved_with_debug_crash` 가 돌고, 그 안의 볼륨헤더 fix 가
bestspace 프로브 창(override −2) 안에서 조건부로 강등 → 볼륨헤더 경쟁(동시 삽입의 파일 확장) 시 에러 없는 NULL →
`disk_manager.c:3235 ASSERT_ERROR_AND_SET` abort. 8세션 동시 삽입으로 2/2 재현, ②를 전부 override 로 옮긴 뒤 2/2 생존.
**release 는 페이지 검증이 꺼져 있어 이 경로를 밟지 않는다** — debug 전용 노출.

- ✅ **리뷰 체크포인트**: wait/timeout 류를 스레드 스코프로 옮기는 변경은 **그 값을 임시로 바꾸는 모든 지점**을 같은
  변수로 옮겨야 한다(`grep xlogtb_reset_wait_msecs`). 하나라도 TDES 에 남으면 중첩 시 뒤집힌다. 회귀 검증은 반드시
  **debug 빌드**로 — `page_validation_level` 기본값이 갈려 debug 에만 있는 경로가 있다.

### `pgbuf_fix` 의 조용한 강등과 거부 경로의 에러 규약 (page_buffer.c:2231, :6467)

무조건 요청(`PGBUF_UNCONDITIONAL_LATCH`)이라도 현재 wait 가 zero-wait(`LK_ZERO_WAIT`/`LK_FORCE_ZERO_WAIT`)면
`pgbuf_fix` 입구(:2231)가 **호출자 모르게 조건부로 바꾼다.** 강등된 요청의 거부 경로(:6467)는 `wait == LK_ZERO_WAIT`(0)
일 때만 `ER_LK_PAGE_TIMEOUT` 을 설정하고 `LK_FORCE_ZERO_WAIT`(−2)는 **에러 없이** 거부한다 — FORCE 프로브 호출자가
스스로 처리한다는 전제다(bestspace 는 `er_errid()==NO_ERROR` 이면 `ER_FAILED` 를 직접 세팅하는 방어까지 갖고 있다).
그래서 "에러 없는 NULL" 은 ①이 강등→거부 else(−2), ②`pgbuf_timed_sleep` zero-wait else 두 경로에서 나온다.
CBRD-27355 의 CI abort 는 ①이 유력했고(선행 케이스 에러 폭풍 → `btree_set_error` 프로브 엇갈림 → −2 고착 →
**`logtb_clear_tdes()` 가 `wait_msecs` 를 리셋하지 않아 트랜잭션 경계를 넘어 유지**), 27183 이 원인을, 27355 가 ②를 닫는다.

### 통계 카운트의 표현 폭과 카탈로그 BTREE_STATS/CLS_INFO 레코드 레이아웃 (statistics.h · system_catalog.c · statistics_sr.c · btree.c)

[출처 .50, 기준 develop 5f3a30d09 → PR#7856(`4d3edfef5`), CBRD-27140]

- develop 5f3a30d09 까지 행수(`CLS_INFO.ci_tot_objects`, `CLASS_STATS.heap_num_objects`)와 인덱스 키수/부분키수
  (`BTREE_STATS.keys`, `int *pkeys`, 옵티마이저 `QO_ATTR_CUM_STATS`)는 **수집→카탈로그→와이어→클라이언트→플래너 전 구간 32비트**.
  컬럼 NDV(`ATTR_STATS.ndv`)만 CBRD-26667 에서 INT64 로 먼저 승격돼 있었다(디스크 `CATALOG_DISK_ATTR_NDV_OFF 80`, 와이어 `OR_INT64`).
- 키 카운터는 `btree.c` 의 `stat_info->keys += key_cnt` / `pkeys[k]++` 누산이라 2^31 에서 **signed wrap** 한다. 실측(gdb 주입):
  debug 는 `btree_get_stats()` 끝의 `assert (keys >= pkeys[i])`(btree.c:8128)로 abort, release 는 `assert_release (keys >= 0)`
  (statistics_sr.c:399,721)이 **NOTIFICATION 만 남기고 음수를 카탈로그에 그대로 영속**한다(`Cardinality: -2147456649`).
  클라이언트 `stats_client_unpack_statistics()` 의 `MIN (keys, heap_num_objects)`/`MIN (pkeys[k], keys)` 는 음수를 걸러내지 못하고,
  플래너 `query_graph.c:5210` 의 "더 큰 keys 선택" 에서 음수가 탈락해 **인덱스 NDV 통계가 통째로 사라진다**(컬럼 NDV 가 있으면 등호
  선택도는 그것으로 대체돼 플랜이 안 바뀔 수 있다).
- 행수는 `statistics_sr.c` 가 `(int) MIN (rs_total_rows, INT_MAX)` 로 **포화**시켜 음수는 안 나오지만, 폴백 `heap_get_num_objects (int *nobjs)`
  는 `HEAP_HDR_STATS.num_recs`(uint64)를 int 로 절단한다. 덤으로 이 함수는 **행수를 반환값으로** 주는데(`return *nobjs`) 유일한 호출부가
  `== NO_ERROR` 로 검사해 행이 있으면 폴백이 0 행으로 끝나는 잠복 버그가 있었다.
- 파티션 부모 통계는 `PARTITION_STATS_ACUMULATOR`(double) 합산 후 int 대입 — 범위 밖 double→int 는 UB.
- **카탈로그 온디스크 레이아웃** (system_catalog.c 상단 `CATALOG_*_OFF`): DISK_REPR 56B(offset 16 은 "reserved", writer 가 0 기록) →
  속성마다 DISK_ATTR 88B(+가변 default value) → 인덱스마다 BTREE_STATS. **V0** = 80B (`btid@0 leafs@12 pages@16 height@20 keys@24
  func@28 pkeys[8]@32 reserved[4]@64`). CLS_INFO 는 별도 56B 레코드(`hfid@0 tot_pages@12 tot_objs@16 time_stamp@20 rep_dir@24`,
  32..55 는 writer 가 `memset 0`). 레코드 크기 산식은 `catalog_sum_disk_attribute_size()`.
- **PR#7856 이후**: 위 필드 전부 INT64. DISK_REPR 의 offset-16 예약 슬롯이 `stats_layout`(0=V0, 1=V1)이 되고 BTREE_STATS 는
  **V1 = 120B** (`V0 프리픽스 0..31 유지, keys INT64@32, pkeys[8] INT64@40, reserved@104`; V0 의 keys@24 칸에는 포화 복사).
  reader 는 `disk_repr_p->stats_layout` 으로 stride/파서를 고르고(`catalog_fetch_btree_statistics(…, stats_layout, …)`),
  writer 는 항상 V1 → 구 DB 는 그대로 열리고 `UPDATE STATISTICS`/스키마 변경 때 자연 갱신. CLS_INFO 는 tail(offset 32)에 INT64
  행수를 두고 0 이면 32비트 칸을 읽는다. `disk_compatibility_level`(11.5f)은 올리지 않았다.
  **주의(.51 실측 정정 2026-09-08)**: V1 레코드가 있는 DB(새 빌드로 createdb 또는 UPDATE STATISTICS)를 PR 이전 바이너리(머지베이스
  `899f07dda` release)로 열면 오독이 아니라 **부팅 거부** — `Missing or invalid catalog class/vclass is found`(시스템 클래스 표현의
  BTREE_STATS 스트라이드 80→120 어긋남이 부팅 시 카탈로그 검증에 걸림). 반대 방향(V0 DB → 새 빌드)은 정상, 재기록 후도 정상.
  → 사용자 결정(2026-09-08)으로 **`disk_compatibility_level` 11.5→11.6 상향**(`20f5b0e9d`). `rel_get_disk_compatible()`(release_string.c)은
  정확 일치만 `REL_FULLY_COMPATIBLE` 이고 `disk_compatibility_rules[]` 는 비어 있어 `log_xinit`(log_manager.c ~1297)·restore(log_page_buffer.c ~2470)
  가 양방향으로 `ER_LOG_INCOMPATIBLE_DATABASE` 를 낸다 → **머지 후 11.5 DB 전부 재생성**(CBRD-26049 11.4→11.5 와 동일). 세 컨테이너 공유 벤치 볼륨 포함.
  리뷰 반영 `90594d976`: AR 샘플링 확장 포화 `INT_MAX`→`DB_BIGINT_MAX`, `orc_diskrep_from_record` `stats_layout` 초기화.
- 와이어: `xstats_get_statistics_from_server()` pack ↔ `stats_client_unpack_statistics()` 가 tot_objects/keys/pkeys 를 INT64 로;
  단건 `NET_SERVER_BTREE_GET_STATISTICS` 회신도 keys INT64(버퍼 `OR_INT_SIZE*4 + OR_INT64_SIZE`). 클라/서버 동일 빌드 전제.
- int 를 유지하는 경계와 포화 지점: `db_get_btree_statistics()`, `db_get_class_num_objs_and_pages()`(→`xheap_get_class_num_objects_pages`),
  `catalog_get_cardinality()`(`index_cardinality()` SQL 함수·`SHOW INDEX` cardinality 컬럼), `heap_estimate_num_objects()`.
  `#objects`/`#keys` 의사컬럼(execute_statement.c `cst_item_tbl`)은 BIGINT 로 바뀜.
- ✅ **리뷰 체크포인트**: 카탈로그 레코드에 필드를 넣을 때 reserved 슬롯이 "항상 0 으로 쓰였는지"(DISK_REPR offset 16, CLS_INFO tail,
  BTREE_STATS reserved) 를 먼저 확인하면 버전 마커 없이도 구 레코드 판별이 가능하다. 통계 관련 카운트를 새로 추가하면 위 7단계 중
  어느 하나만 int 로 두어도 다시 잘린다.

## 3. 예비 이슈 사항

> 미수정 버그·의심·문서 정정 후보·구조적 한계. 해소되면 삭제가 아니라 "해소됨(커밋/PR)"로 갱신.

- **[develop 미반영 UB 수정]** `btree_search_nonleaf_page` start_col 미초기화(btree.c:5242) —
  develop 95b79e7ed에서 잔존 재확인. 수정 c44ccf767은 .52의 join-perf-analysis 브랜치에만 있음.
- **[구조적 한계 — 핫 인덱스 루트 BCB의 latch true sharing]** 상관 서브쿼리·NLJ 인덱스 프로브가 많은 질의에서
  루트 페이지 BCB 하나의 `atomic_latch` RMW가 전체 HITM의 30%+ (Q21 실측, §2 pgbuf 항목). BCB 레이아웃
  변경(CBRD-27284)으로는 해소 불가 — **64B 3분할은 128B 형제 결합으로 HITM +58% 역효과**(반증됨, PR#7844 close).
  fix당 RMW 빈도를 줄이는 설계(스캔 단위 루트 fix 유지 등)가 필요하나 미발번. [.52, 2026-09-02]
- `pgbuf_ordered_fix_release` 패스트패스 35,624B 스택 프레임 — 패스트패스가 쓰지 않는 64×64
  워스트케이스 배열 때문.
- buf_hash_table 56MB(56B×2^20) 중 히트 경로는 8B(hash_next)만 사용 — SoA 분리 시 8MB + 프리페치 여지.
- 힙 프로브 1행당 같은 슬롯 3~4회 재탐색(spage 합계 7.6%), class OID 행마다 재유도.
- **[래치 타임아웃이 서버 abort]** `pgbuf_timed_sleep()` 의 `er_set_return` 이 zero-wait 분기
  (`LK_ZERO_WAIT`·`LK_FORCE_ZERO_WAIT`, 그리고 tdes 가 없어 `pgbuf_find_current_wait_msecs()` 가 0 을
  반환한 경우)에서만 **에러를 설정하지 않아** `pgbuf_fix()` 가 에러 없는 NULL 을 반환하고, 호출자의
  `ASSERT_ERROR_AND_SET` 이 깨져 서버가 죽는다. zero-wait 는 예외 상황이 아니다 —
  `xlogtb_reset_wait_msecs (thread_p, LK_FORCE_ZERO_WAIT)` 로 트랜잭션 전역에 no-wait 를 걸었다 푸는
  구간이 있다(btree.c:21729, bestspace.cpp:680, lock_manager.c:9029). → **CBRD-27355 / PR#7843 제출됨** (`.51`, 2026-09-01). **2026-09-02 이관** — PR#7843(27183+27355) 후속은 다른 세션/담당이 맡는다. 같은 부류를 CBRD-27293(f8f5b4401)이 `pgbuf_block_bcb()` 인터럽트 경로에서 먼저
  고쳤고 "callers assert one is set" 주석이 그 흔적이다.
- **[에러 경로에서 남의 버퍼 free]** `catcls_update_class_stats()` 가 읽기·쓰기에 RECDES 하나를 겸해,
  `heap_get_visible_version(COPY)` 성공 후 `malloc` 전에 실패하면(`catcls_get_or_value_from_record()` 가
  `ER_INTERRUPTED` 로 NULL) error 레이블이 **스캔캐시 소유 버퍼**를 free 해 glibc
  `munmap_chunk(): invalid pointer` 로 abort. 코어의 `record = {area_size = 32688, length = 560}` 이
  증거다 — 이 함수가 잡은 버퍼면 ⑦ 에서 둘을 같게 설정하므로 값이 같아야 한다.
  → **CBRD-27354 / PR#7842 제출됨** (`.51`, 2026-09-01).
- **[디버그 빌드 지뢰]** `pgbuf_timed_sleep()` 의 `LK_INFINITE_WAIT` 타임아웃 분기에
  `assert (0);` 이 "FIXME: remove it. temporarily added for debugging" 주석과 함께 남아 있다.
  무한대기 트랜잭션이 래치 타임아웃을 맞으면 **디버그/optdebug 빌드가 설계상 abort** 한다.
  미수정 — 제거 여부는 판단 필요.
- **[통계 32비트 절단]** 인덱스 키수/부분키수·행수가 전 구간 int 라 2^31 키 초과 인덱스에서 카운터가 랩되어 음수 카디널리티가 카탈로그에
  영속(release)·debug abort(§2 항목 참조). → **CBRD-27140 / PR#7856 제출됨** (`.50`, 2026-09-02). 부수 발견: `heap_get_num_objects()` 반환값
  오검사, 파티션 합산 double→int UB, `statistics_cl.c:233` `assert (keys >= 0)` 가 debug SA 에서 음수에도 발화하지 않은 현상(원인 미추적).
- **[테스트 하네스 결함]** FI 테스트 `exclude_core()` 스윕이 foreground 직후에만 돌아 비동기 vacuum
  워커 발화 FI 코어를 놓침 — CI 산발 NOK. TC 이슈화는 사용자 판단 대기.

**CBRD-24094(10a1df3e6, OID-ordered overflow chains + separator directory)는 온디스크
포맷 비호환** — 구 포맷 볼륨을 새 빌드로 열면 **읽기는 되지만 뷰 생성 등 카탈로그 쓰기에서
깨진다**(사용자 실측 2026-08-28, 3컨테이너 전체 재적재로 대응). 역방향(구 빌드 ↔ 새 포맷
볼륨)은 `.50`이 demodb DDL까지 양방향 안전을 실측. **이 커밋을 걸치는 브랜치 전환·TC
재실행 시 DB 재적재 여부를 먼저 판단할 것.** [출처 .52/.50 교차, 기준 develop 04620b2ce]

## 4. 진행중인 작업

> 각 컨테이너가 자기 소절을 직접 관리한다. 완료되면 지우지 말고 "완료(PR/커밋)"로 갱신.

### .50
- exclude_core 하네스 결함 발견(FI 코어 판정 예외 규칙화 완료), TC 이슈화 여부 사용자 판단 대기.
- CBRD-27140 통계 INT64 승격 + 카탈로그 BTREE_STATS V1 레이아웃 — PR#7856 리뷰 대기, CTP sql/medium 진행 중 (2026-09-02).

### .51
- CBRD-27354 / PR#7842 — `catcls_update_class_stats()` RECDES 분리. test_shell 벤더 3건 외 실패 0, 리뷰 대기 (2026-09-02).
- CBRD-27183 + CBRD-27355 / PR#7843 — **2026-09-02 이관(세션 종료)**. head `3c58abb63`(27183 `b0f2f3c78` + 27355).
  1차 CI 회귀(위 §2 스코프 뒤집힘) 수정 후 CI 재실행 중이었다. 인수인계는 보드 #87·#51 코멘트.

### .52
- join-perf-analysis 브랜치에 btree start_col UB 수정(c44ccf767) 보유 — develop 반영 경로 미정
  (PR#7622 머지 후 별도 PR 또는 편승 판단 대기).
- CBRD-27284(BCB 캐시라인 분리): **종결 — 유효성 없음** (2026-09-02, PR#7844 close, 보드 #76 close).
  perf c2c로 반증(§2 pgbuf 항목·§3). 후속 방향은 별건 발번 필요. [설계문서
  claude-workspace/projects/CBRD-27284/설계문서.md]
- CBRD-27285/PR#7762(섹터 read 실패 시 미초기화 ftab free — mspace_free abort): PR OPEN
  (2026-08-20), 리뷰 대기. 이 모듈 §3의 "에러 경로 자원 초기화 시점" 항목의 실제 수정 PR.
  [보드 #80]