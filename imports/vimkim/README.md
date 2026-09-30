# imports/vimkim — 김대현(vimkim) 의 CUBRID 소스 분석 문서·개인 스킬에서 들여온 것

출처: https://github.com/vimkim/my-cubrid-docs (public) @ `307bcb718` (2026-09-30, 486 커밋, 2026-04-17~) ·
https://github.com/vimkim/my-cubrid-skills (public) @ `6eacc4c` (106 커밋). 들여온 날 2026-09-30 (정소희 세션, .51). **원 작성자 vimkim(및 그 세션의 Claude/Codex), 원문 무수정.**

방침(`imports/xmilex-git` 선례 = 사용자 지시 2026-09-16): **재사용 가능한 소스 사실 조사·설계 근거만** 남긴다. 제외한 것 —
CI 실패 분석 보고서(`ci_analysis_report_*`)·코드 리뷰 보고서·리뷰 대응 보고서·머지 충돌 결정 로그·PR 본문 상세판·`.scratch/` 티켓·
`evidence/`·pedagogy/quiz 패킷·발표 자료·`feat/oos` 전용 문서(OOS 는 2026-09-30 현재 develop 에 없다 — `src/storage` 에 oos 파일 0개) ·
OLAP/HTAP 로드맵·JIT 입문서. 원 리포에서 본다.

모듈 노트(`modules/src-*.md` §2·§3)로 옮길 때는 항목 끝에 `— vimkim(원문 imports/vimkim/<파일>) YYYY-MM-DD` 로 출처를 남기고 원문은 여기 둔다.
**타 DBMS 비교 절이 있는 문서**(`reference-dbms/`, `storage/survey-*`, `pgbuf/CBRD-27196-*`)를 우리 노트에 인용할 때는
`claude-workspace/memory/rules/참조DB-표기.md` 대로 제품명 대신 "database-reference 참고" 로 쓴다.

원문 파일명의 `_<7자리 SHA>_<agent>` 접미사는 **분석 기준 CUBRID 커밋과 작성 에이전트**다(vimkim 규약). 여기서는 SHA 만 남기고 agent 접미사는
대부분 뗐다(같은 주제의 claude/codex 두 판이 있는 `transaction/cdc-*` 만 유지).

## 1. 들여온 파일 (54개, 약 29.8K 줄)

### pgbuf/ — `src/storage/page_buffer.c` 전역 분석 (기준 develop `e6ed61e87`, 2026-08)
| 파일 | 내용 |
|---|---|
| `00-overview.md` | 총론: 5계약(fix/latch/unfix/set_dirty/flush), 4 문제의식, 시나리오 5개, 뮤텍스 계층·락 랭킹, "놓았다 다시 잡으면 재검증" 패턴, 결함 후보 20건 표 |
| `01-structures.md` | 자료구조 16종, BCB 플래그 비트 인코딩, 메모리 레이아웃 실측, 초기화/종료, 시스템 파라미터 |
| `02-fix-unfix-latch.md` | `pgbuf_fix` 전체 경로, atomic latch, holder, **lock-free RO 경로**, promote, 락 랭킹, CAS 결정표 |
| `03-lru-victim-quota.md` | 3-zone LRU, private/shared, quota 수식, victim 선정 의사코드, direct victim, AOUT |
| `04-flush-wal-daemons.md` | dirty 생애주기, WAL rule, `pgbuf_bcb_flush_with_wal`, victim/checkpoint flush, 데몬 4종, DWB |
| `05-ordered-fix-dealloc.md` | ordered fix/watcher, dealloc/invalidate, recovery, VPID 페이지 락 |
| `06-misc-observability.md` | TDE, copy buffer, temp 페이지 규칙, 통계/SHOW 19컬럼, 디버그 안전장치 23종, 외부 모듈 계약 |
| `09-issue-proposals.md` | JIRA 이슈 제안 P1~P9 (등록 전 초안) — **§2 "소스 사실" 표에서 develop 대조 결과 참조** |
| `10-CBRD-27263-repro-proof-and-solutions.md` | lock-free fix 와 dealloc 보호 카운터 비대칭 — 라이브 재현(40회 해제, 7회 타인 보호 탈취) + 해법 후보 비교 |
| `research/prevent-dealloc-necessity.md` | `OLD_PAGE_PREVENT_DEALLOC` 은 정합성 장치인가 성능 장치인가 → 정합성(제거 불가) |
| `research/lockfree-fix-origin.md` | lock-free fix 경로가 들어온 커밋/PR/동기·성능 수치, 되돌릴 때의 비용 |
| `defects-report_5cd4f860e.md` | 세미나 준비 중 발견한 결함 D1~D8 (재검증 방법 포함) |
| `CBRD-27196-sx-latch-flush-aio-source-trace_f799e05.md` | flush/AIO 에 SX latch 가 필요한가 — "현 flush 는 BCB mutex 하에 frame 을 복사하므로 불필요" 소스 추적 |
| `CBRD-26325-latch-timeout-instrumentation-proposal.md` | 300초 WRITE latch 점유 원인 규명용 계측 4단계 제안 (holder 추적·breadcrumb·강제 스택덤프) |
| `CBRD-26500-PR-7157-hit-ratio-underflow-explanation.md` | page buffer hit ratio uint64 언더플로 — PR#7157 (2026-09-30 OPEN, approved) |

### storage/ — 힙·디스크·파일 관리자·래치 계약
| 파일 | 내용 |
|---|---|
| `CBRD-26176-bestspace-01-asis-legacy.md` | **PR#7353 이전** `heap_Bestspace`(HEAP_HDR_STATS·인메모리 캐시·sync 경로·고동시성 INSERT 병목) 전수 분석 (`e84a7f6dc^`) |
| `CBRD-26176-bestspace-02-tobe-architecture.md` | **PR#7353 이후** `bestspace.cpp`(shard·L1/L2/L3·registry·온디스크·동기화·복구·파라미터) 구조 레퍼런스 (`e84a7f6dc`) — develop 현행 |
| `CBRD-26176-bestspace-03-callflows.md` | gdb·printf 계측으로 실측한 INSERT→bestspace 콜플로우, 8-커넥션 인터리빙, 30초 sync, 재시작 rebuild, 미해결 이슈 |
| `CBRD-26788-prefetch-survey.md` | heap/btree 스캔 prefetch 도입 검토 — 사용자 질의 경로 prefetch 부재, `posix_fadvise` hook, parallel scan 임계(2048p) |
| `CBRD-27151-bulk-destroy-recovery-metadata_93f11fb3f.md` | 섹터 단위 bulk `file_destroy` 와 복구 시 재실행의 정합성 구멍 — PR#7785 (2026-09-30 OPEN) |
| `cubrid-volume-read-only-parser_e6ed61e.md` | 데이터 볼륨 온디스크 포맷(페이지 프레이밍·볼륨 헤더·섹터 테이블·file 소유 재구성·TDE·LSA) 과 읽기 전용 파서 설계 |
| `survey-unconditional-page-latch-assumptions_d9ceb53.md` | `PGBUF_UNCONDITIONAL_LATCH` 실패를 `assert_release` 로 취급하는 호출부 표(file_manager·disk_manager·recovery) vs busy 를 정상으로 쓰는 곳(bestspace `L1_fix`, `btree_set_error`) |
| `survey-backupdb-level-0_cd593bc.md` | `backupdb -l 0` 이 실제로 하는 일 — 볼륨 파일 페이지 전수 `pread`, 체크포인트/flush/DWB sync 선행, 멀티스레드는 압축 병렬이지 I/O 병렬이 아님 |
| `CBRD-27198-lock-vs-latch-timeout-survey_d9ceb53.md` | `lock_timeout`(트랜잭션) 과 `page_latch_timeout_in_msecs`(300s, 숨은 파라미터)의 분리 — `pgbuf_fix_internal` 이 zero-wait 트랜잭션의 UNCONDITIONAL 을 CONDITIONAL 로 강등하는 설계 누수 |
| `CBRD-27198-PR-7630-preserve-lk-force-zero-wait_d9ceb53.md` / `-blocking-refutation_1185f16.md` | PR#7630(머지됨 `b203b6c9d`) 의 설계 근거: `LK_FORCE_ZERO_WAIT` 의 no-wait 의미 보존, 대안 설계 |

### transaction/ — WAL·sysop·락·MVCC·CDC
| 파일 | 내용 |
|---|---|
| `log-manager-overview_4cfc837.md` | 로그 매니저 16장: LSA, 온디스크 구조, 레코드 종류, **prior list → LOG_CS → 로그 페이지 버퍼 → flush 데몬/그룹 커밋**, WAL 강제, sysop, 체크포인트, 아카이브, 복구 3단계, Vacuum/HA/CDC 소비자, 파라미터, 파일 지도 |
| `log-manager-append-flush-dynamic-analysis_4cfc837.md` | 위 정적 분석을 printf 트레이스 8곳으로 실측 확인 + **정적 문서 정정 사항(§6)** |
| `log-manager-dynamic-analysis-plan_4cfc837.md` · `log-manager-CONTEXT.md` | 계측 계획, 용어집 |
| `sysop-explained_977cf18a4.md` | `log_sysop_start/commit/abort` 내부(TDES topops 스택), 부분 실패가 문제 안 되는 이유, crash 안전성, 비용 (§6·§11·§12 는 feat/oos 예시) |
| `CBRD-27093-dwb-off-checkpoint-fsync-missing.md` · `-QnA-dwb-off-fsync.md` · `-checkpoint-fsync-fallback_85b6b57.md` | DWB 비활성 시 체크포인트가 데이터 볼륨을 fsync 하지 않던 문제 — **develop `60f3b5a96`(#7521) 로 해소**, 11.0/11.3/11.4 백포트 |
| `CBRD-27400-append-lsa-torn-read_a590292.md` | `append_lsa` 를 락 없이 두 번 load / 두 번 store 하여 찢어진 값을 읽는 경합 해설 — PR#7904 는 close, **CBRD-27320(#7875, `b319ce1ab`) 의 whole-word atomic LSA 로 해소** |
| `lock-manager-source-trace-packet_f30f1c2.md` · `-source-audit-revision_f30f1c2.md` · `lock-manager-scope_f30f1c2.md` | lock manager end-to-end 추적 4건(자원·모드·계층·변환·에스컬레이션 / 대기·데드락·타임아웃·기상·해제 / MVCC SELECT·FOR UPDATE·DML 클래스-행 정책 / **MVCCID X self-lock 과 unique/FK S wait·recheck**), claim 후보, negative search |
| `mvcc-version-read-path-improvement-proposal_f30f1c2.md` | 구버전 읽기 경로(`heap_get_visible_version_from_log`) 개선 제안 — **초안, 계측 선행 필요** 라고 원문이 명시 |
| `cdc-ha-failover-analysis_4cfc8370e-claude.md` · `cdc-ha-role-transition-analysis_4cfc8370-codex.md` | master→standby→master 전환 후 CDC 가 멈추는 원인 정적 분석 두 판 |

### loaddb/ · build-perf/ · arch/
| 파일 | 내용 |
|---|---|
| `loaddb/CBRD-27157-server-loaddb-locking-source-trace_f11fc42.md` | 서버측 loaddb 의 락(`BU_LOCK`) 과 트랜잭션 MVCCID self-lock 은 자원·소유자가 다른 두 락 — 수정 PR#7588 은 **feat/oos 에만 머지** |
| `loaddb/CBRD-27441-validate-partition-range-server-loaddb_109f16a.md` | 서버측 loaddb 파티션 범위 검증 — PR#7982 (2026-09-30 OPEN) |
| `build-perf/CBRD-26382-*.md` (5) | `std::function`→lambda 리팩터링(PR#6636)이 COUNT(*) 를 느리게 한 인과: cold code 7B 감소 → 링크 정렬 도미노로 hot 함수 16B 이동 → 실행 코어 bound 변화. `noexcept` 바이너리 배치 6종 실험, hot function alignment 선택지, GCC 8 전체 서버 후속, **PGO 실험** |
| `build-perf/debug-gcc-vs-clang-clean-build-analysis_2026-08-13.md` | 클린 빌드 78.8s(gcc) vs 50.9s(clang) 차이는 링커가 아니라 GCC 컴파일 단계; 플래그·PCH 실험 |
| `build-perf/cubrid-third-party-ci-cache-design_2026-09-22.md` | k8s CI 용 third-party 캐시 설계 |
| `arch/SA_MODE-libcubridsa-removal-roadmap.md` | SA_MODE 컴파일 모드·libcubridsa 제거 로드맵 제안(파일럿 loaddb, 성능 게이트, 단계) |
| `arch/CBRD-27074-csql-sa-pl-startup-delay.md` | csql SA 모드 PL 시작의 고정 지연 |

### reference-dbms/
`innodb-bufpool.md`(2072줄) · `postgres-bufmgr.md`(762줄) — 페이지 버퍼 대조 팩트시트. 인용 시 표기 규칙 위 참조.

## 2. 소스 사실 — develop `0d0809963`(2026-09-30) 대조 결과와 모듈 반영

| 원문 주장 | .51 대조 (0d0809963) | 반영 |
|---|---|---|
| **D1/P2** `pgbuf_bcb_flush_with_wal` 의 TDE 암호화 실패·`dwb_set_data_on_next_slot` 실패 조기 반환이 `FLUSHING_TO_DISK` 를 원복하지 않음 | **잔존.** `mark_is_flushing` :10714, 조기 `return error` :10728·:10740, `mark_was_not_flushed` 는 :10823 (정규 write 실패 경로) 에만 | `src-storage.md` §3 미수정 |
| **D3/P3** `pgbuf_direct_victims_maintenance` 두 루프가 `index = prv_index` 로 시작해 `index != prv_index` 가 첫 평가부터 거짓 | **잔존.** 루프 조건 동일(`nassigns > 0` 항이 추가됐을 뿐) | `src-storage.md` §3 미수정 |
| **P1/CBRD-27263** lock-free RO fast path 가 `register_avoid_deallocation` 을 건너뛴 채 공통 꼬리의 `unregister` 를 실행 | **구조 잔존.** `pgbuf_lockfree_fix_ro` :2267 → `goto fast_path` :2279 → 라벨 :2447; register 는 :2376(라벨 앞), unregister 는 :2465(라벨 뒤). PR 없음 | `src-storage.md` §3 미수정 |
| **D7** AOUT 은 conf 와 무관하게 강제 비활성 | **잔존.** `system_parameter.c:10159-10160` "disable AOUT list until we fix CBRD-20741" | `src-storage.md` §2 |
| **P5** `PSTAT_PB_NUM_IOWRITES` 가 non-DWB 분기에서만 증가 | **잔존.** :10804 (`else` = DWB 미사용 분기) | `src-storage.md` §2 |
| CBRD-27400 `append_lsa` torn read | **해소.** CBRD-27320(#7875) 로 `log_Gl.hdr.append_lsa` 가 atomic LSA (`.load()/.store()`, log_page_buffer.c) | `src-transaction.md` §2 |
| CBRD-27093 DWB off 체크포인트 fsync 누락 | **해소.** `60f3b5a96` (#7521) | `src-transaction.md` §2 |
| CBRD-26176 bestspace 재설계 | 머지됨(`e84a7f6dc`, #7353). `src/storage/bestspace.{cpp,hpp}` 현존 | `src-storage.md` §2 포인터 |
| CBRD-27151 bulk destroy vs 복구 재실행 | PR#7785 OPEN | `src-storage.md` §3 |
| CBRD-26500 hit ratio 언더플로 | PR#7157 OPEN(approved, 2026-08-14 이후 정지) | `src-storage.md` §3 |
| D2·D4·D5·D6·P4·P6·P7·P8·P9, lock manager claim 후보, sysop 세부, CDC 원인 후보 | **미대조** | `staging/정소희-vimkim-imports.md` 에 미확인 표기로 대기 |

## 3. 방식에서 배울 점 (my-cubrid-skills + 문서 규약) — 채택은 사용자 판단

우리 규약(`skills/source-learning`, `dev4-review-workspace/skills/*`, `claude-workspace/memory/rules/*`)과 비교해 **없거나 약한 것만** 적는다.

1. **파일명에 기준 커밋·에이전트 접미사** `<slug>_<7자리SHA>_<claude|codex>.md`. 우리는 본문 머리에 리비전을 적는데, 파일명에 있으면 디렉터리 목록만으로 낡은 문서를 가려낼 수 있다. 같은 주제를 두 에이전트가 쓴 판을 나란히 두는 것도 이 규약 덕이다.
2. **조사 문서 골격 `Verdict → Shared Scenario → Trace(file:line 표) → Runtime Probe → Unknowns → Source Revisions`** (`storage/survey-*`). 우리 §2 "주장→근거→체크포인트" 에 **"확인 못 한 것(Unknowns)"과 "찾아봤는데 없던 것(Negative searches)"** 절이 없다 — 다음 사람이 같은 grep 을 반복하지 않게 해 준다. `source-learning` §4 에 추가 검토.
3. **결함 보고서 → 이슈 제안 목록(P1~P9, "등록 전 초안", 심각도·준비 상태·검증 방법·근거 챕터 링크)** 형식(`pgbuf/09-issue-proposals.md`). 우리 §3 예비 이슈의 한 항목이 이 정도 구조를 가지면 발번이 바로 된다.
4. **정적 분석 뒤 동적 실증 + "정적 문서 대비 정정/보강" 절**(`transaction/log-manager-append-flush-dynamic-analysis` §6, `storage/CBRD-26176-*-03-callflows`). 우리 "검증된" 기준(§2: 가능하면 실행으로 확인)의 좋은 실례 — 정정 사항을 별도 절로 모아 정적 문서를 고친다.
5. **CI 증거 규율**(`cubrid-ci-analyze`, `cubrid-common/references/ci-evidence.md`): run ID 와 attempt 를 구분, 엔진 커밋과 테스트케이스 리비전을 따로 기록, 러너 exit 0 은 판정이 아니다, 인과 주장마다 `PR relation(direct/plausible/unlikely/unknown) + confidence + falsifier + next action`. `dev4-review-workspace/skills/gha-ci` 와 대조해 빠진 항목(특히 falsifier) 채택 검토.
6. **PR 본문 계약**(`cubrid-pr-create`): `## Purpose / Implementation / Remarks` 고정, **AS-IS/TO-BE 한 줄씩**, 25~35줄 한 화면, 상세는 별도 문서 링크, **로컬 전용 명령(`just`·alias·절대경로) 금지 + 게시 전 스캔** (`rg -nP '\bjust\s+\w'`). 우리 `goto`·`~/bin/*` 도 PR·JIRA 본문에 쓰면 안 되는 로컬 도구다 — `PR브랜치-규칙` 에 스캔 한 줄 추가 검토.
7. **JIRA 본문 Layer Ownership**(`cubrid-jira-issue-write`): Triage(목적/이유/방안) = 결론, Description = 메커니즘, Summary = 범위·영향 — **같은 사실을 두 층에 쓰지 않는다**, 작성 후 중복 grep. 이유에는 임계값을 코드 이름으로(`DB_PAGESIZE/8`), 영향은 5범주 중 하나만 구체 사례로. 우리 `jira-task` 스킬과 상보.
8. **리뷰 코멘트는 REST 3 endpoint 합집합**(`gh-pr-comments-all`): `/pulls/N/comments`(인라인) + `/pulls/N/reviews`(리뷰 요약, `COMMENTED`+빈 본문은 래퍼라 버림) + `/issues/N/comments`(대화 탭). 하나만 보면 리뷰 요약·대화 탭이 조용히 빠진다. `review-response` 스킬의 수집 단계와 대조.
9. **용어집 `CONTEXT.md` 에 `_Avoid_` 동의어 목록** — "test bucket 말고 test suite". 우리 CONTRIBUTING 7항(원문 용어 유지)과 상보적: 유지할 원문뿐 아니라 **쓰지 말 표현**을 적는다.
10. **테스트 실행은 attempt 디렉터리에 `$CUBRID`·CTP 를 복사해 격리**하고, 판정은 프로세스 종료 코드가 아니라 결과 산출물(summary·XML·`.result`)로 (`cubrid-common/references/testkit-focused.md`). 우리 `harness/templates/repro.sh`·`session.py` 의 격리 원칙과 같은 방향; "exit 0 ≠ pass" 는 명문화 가치.
11. **자동 발행 계약을 좁게 명시**: fork·대상 리포·draft 세 조건이 전부 맞을 때만 확인 없이 진행, 하나라도 다르면 묻는다(`cubrid-pr-create` "Automatic Draft Publication Contract"). 우리 "타인 PR 게시 전 사용자 검토" 규칙의 반대편 — 내 PR 은 조건부 자동화하는 선례.

원 리포에는 이 밖에 `cubrid-manual-search`(RST 매뉴얼을 `rg -F` 로 찾고 `:ref:`/`include` 를 풀어 file:line 인용), `cubrid-qa-fetch`(qahome 인증 페치·`showFuntionRes` 철자 함정), `track-work`(30분 이상 작업 원장), `markdown-write`(copyparty 뷰어용 Mermaid·MathJax 검증) 가 있다 — 도구 의존이라 들여오지 않았다.
